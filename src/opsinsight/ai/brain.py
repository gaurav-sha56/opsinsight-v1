import time
import json
from typing import List, Dict, Any, Optional

from opsinsight.tools.schemas import tools
from opsinsight.tools.fs import execute_tool
from opsinsight.config.manager import get_config_dict
from opsinsight.config.constants import DEFAULT_MODELS, DEFAULT_API_BASES
from opsinsight.ai.resolver import resolve_litellm_model, validate_credentials
from opsinsight.ai.errors import handle_api_error


def stream_words(text: str) -> None:
    """Print character by character to preserve newlines and formatting."""
    for char in text:
        print(char, end="", flush=True)
        time.sleep(0.01)


def _prepare_messages_for_ollama(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure message history conforms to Ollama's format (e.g. dict arguments for tool_calls)."""
    prepared = []
    for msg in messages:
        m = dict(msg)
        if m.get("content") is None:
            m["content"] = ""
        if m.get("tool_calls"):
            cleaned_tcs = []
            for tc in m["tool_calls"]:
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                cleaned_tcs.append({
                    "function": {
                        "name": fn.get("name", ""),
                        "arguments": args
                    }
                })
            m["tool_calls"] = cleaned_tcs
        prepared.append(m)
    return prepared


def start_chat_session(messages: List[Dict[str, Any]], config: Optional[Dict[str, Optional[str]]] = None, _depth: int = 0) -> None:
    """
    Direct function-based Brain for OpsInsight:
    - Uses official `ollama.Client` for 'ollama' (local) and 'ollama-cloud' (https://ollama.com).
    - Uses `litellm.completion` for all other providers (gemini, openai, anthropic, groq, openai-compatible).
    - Normalizes tool calling across both engines seamlessly with safety guards.
    """
    # Safety guard against infinite tool recursion loops
    if _depth >= 6:
        print("\n⚠️ OpsInsight Warning: Maximum tool recursion depth reached (6 turns). Stopping loop to prevent deadlock.")
        return

    raw_config = config or get_config_dict()
    provider = (raw_config.get("OPS_PROVIDER") or "gemini").strip().lower()
    model = (raw_config.get("OPS_MODEL") or DEFAULT_MODELS.get(provider, "gemini-2.5-flash")).strip()
    api_key = raw_config.get("OPS_API_KEY")
    api_base = raw_config.get("OPS_API_BASE")

    if api_key:
        api_key = api_key.strip()
    if api_base:
        api_base = api_base.strip()

    # Default endpoints with provider-mismatch protection
    if provider == "ollama":
        if not api_base or ("custom" in api_base.lower() and "11434" not in api_base):
            api_base = DEFAULT_API_BASES["ollama"]
    elif provider == "ollama-cloud":
        if not api_base or ("custom" in api_base.lower() and "ollama" not in api_base.lower()):
            api_base = DEFAULT_API_BASES["ollama-cloud"]

    # OpenAI-compatible requires a non-empty string for client API key
    if provider == "openai-compatible" and not api_key:
        api_key = "none"

    if not validate_credentials(provider, api_key, api_base):
        return

    text_content = ""
    parsed_tool_calls: List[Dict[str, Any]] = []

    if provider in ("ollama", "ollama-cloud"):
        try:
            import ollama
            from ollama import Client
        except ImportError:
            print("❌ Error: Missing required dependency 'ollama'.")
            print("👉 Please install dependencies using: pip install ollama (or pip install -e .)")
            return

        if provider == "ollama-cloud":
            host = api_base or "https://ollama.com"
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            client = Client(host=host, headers=headers)
        else:
            host = api_base or "http://localhost:11434"
            client = Client(host=host)

        ollama_model = resolve_litellm_model(provider, model)
        prepared_messages = _prepare_messages_for_ollama(messages)

        try:
            response = client.chat(
                model=ollama_model,
                messages=prepared_messages,
                tools=tools
            )
        except Exception as e:
            handle_api_error(e, provider, host)
            return

        try:
            resp_message = response.message
            text_content = getattr(resp_message, "content", "") or ""
            raw_tcs = getattr(resp_message, "tool_calls", None) or []
            for idx, tc in enumerate(raw_tcs):
                fn = getattr(tc, "function", None)
                fn_name = getattr(fn, "name", "") if fn else ""
                fn_args = getattr(fn, "arguments", {}) if fn else {}
                if isinstance(fn_args, str):
                    try:
                        fn_args = json.loads(fn_args)
                    except Exception:
                        fn_args = {}
                parsed_tool_calls.append({
                    "id": getattr(tc, "id", None) or f"call_{int(time.time()*1000)}_{idx}",
                    "name": fn_name,
                    "arguments": fn_args
                })
        except Exception as e:
            print(f"\n❌ OpsInsight Error: Failed to parse Ollama response: {e}")
            return

    else:
        try:
            import litellm
        except ImportError:
            print("❌ Error: Missing required dependency 'litellm'.")
            print("👉 Please install dependencies using: pip install litellm (or pip install -e .)")
            return

        litellm.telemetry = False
        litellm_model = resolve_litellm_model(provider, model)

        completion_kwargs: Dict[str, Any] = {
            "model": litellm_model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto"
        }

        if api_key:
            completion_kwargs["api_key"] = api_key
        
        # CRITICAL FIX: Only pass api_base if provider is openai-compatible 
        # to prevent global base pollution for Groq, Gemini, and OpenAI.
        if api_base and provider == "openai-compatible":
            completion_kwargs["api_base"] = api_base

        try:
            response = litellm.completion(**completion_kwargs)
        except Exception as e:
            handle_api_error(e, provider, api_base if provider == "openai-compatible" else None)
            return

        try:
            response_message = response.choices[0].message
            text_content = getattr(response_message, "content", "") or ""
            raw_tcs = getattr(response_message, "tool_calls", None) or []
            for idx, tc in enumerate(raw_tcs):
                call_id = getattr(tc, "id", None) or f"call_{int(time.time()*1000)}_{idx}"
                fn = getattr(tc, "function", None)
                fn_name = getattr(fn, "name", "") if fn else ""
                fn_args = getattr(fn, "arguments", "{}") if fn else "{}"
                if isinstance(fn_args, str):
                    try:
                        fn_args = json.loads(fn_args)
                    except Exception:
                        fn_args = {}
                parsed_tool_calls.append({
                    "id": call_id,
                    "name": fn_name,
                    "arguments": fn_args
                })
        except (AttributeError, IndexError):
            print("\n❌ OpsInsight Error: Received invalid response structure from LLM.")
            return

    # Normalized Tool Execution & Multi-turn Conversation Loop
    if parsed_tool_calls:
        if text_content.strip():
            stream_words(f"\n💡 OpsInsight: {text_content.strip()}\n")

        time.sleep(0.5)

        # Build standardized assistant message with tool_calls
        tool_calls_payload = []
        for tc in parsed_tool_calls:
            tool_calls_payload.append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"] if provider in ("ollama", "ollama-cloud") else json.dumps(tc["arguments"])
                }
            })

        assistant_msg: Dict[str, Any] = {
            "role": "assistant",
            "content": text_content if text_content else None,
            "tool_calls": tool_calls_payload
        }
        messages.append(assistant_msg)

        # Execute each tool and append tool response
        for tc in parsed_tool_calls:
            call_id = tc["id"]
            fn_name = tc["name"]
            fn_args = tc["arguments"]

            result_str = execute_tool(fn_name, fn_args)

            messages.append({
                "tool_call_id": call_id,
                "role": "tool",
                "name": fn_name,
                "content": result_str
            })

        # Recurse with updated message history and incremented depth counter
        return start_chat_session(messages, config=raw_config, _depth=_depth + 1)

    else:
        time.sleep(0.5)
        if text_content:
            stream_words(f"💡 OpsInsight: {text_content}")
        print("\n")

        try:
            user_reply = input("💬 Your Reply (or press Enter to exit): ").strip()
        except (KeyboardInterrupt, EOFError):
            user_reply = ""

        if user_reply:
            messages.append({"role": "assistant", "content": text_content})
            messages.append({"role": "user", "content": user_reply})
            return start_chat_session(messages, config=raw_config, _depth=0)
        else:
            print("Exiting OpsInsight. Happy coding!\n")


def send_to_llm(contents: Any) -> None:
    """Bridge function that accepts messages or strings and starts the session."""
    messages: List[Dict[str, Any]] = []

    if isinstance(contents, str):
        messages.append({"role": "user", "content": contents})
    elif isinstance(contents, list):
        for item in contents:
            if isinstance(item, dict):
                messages.append(item)
            elif hasattr(item, "role") and hasattr(item, "parts"):
                text_parts = [p.text for p in item.parts if hasattr(p, "text") and p.text]
                messages.append({"role": item.role or "user", "content": "\n".join(text_parts)})
            elif hasattr(item, "content"):
                messages.append({"role": getattr(item, "role", "user"), "content": str(item.content)})
            else:
                messages.append({"role": "user", "content": str(item)})
    else:
        messages.append({"role": "user", "content": str(contents)})

    start_chat_session(messages, _depth=0)