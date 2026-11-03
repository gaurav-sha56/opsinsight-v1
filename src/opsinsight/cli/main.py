import time
import sys
import os

from opsinsight.core.detector import detect_file_type
from opsinsight.core.compilers import get_run_command
from opsinsight.core.runner import run_program
from opsinsight.cli.commands import handle_start, handle_init, handle_config_command
from opsinsight.config.manager import load_merged_config
from opsinsight.ai.brain import start_chat_session
from opsinsight.ai.prompts import get_prompt


def analyze_error(error_message: str) -> None:
    """Generates the debugging prompt and starts the interactive AI chat session."""
    prompts = get_prompt(error_message)
    messages = [{"role": "user", "content": prompts}]
    start_chat_session(messages)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: ops <file> OR ops start OR ops init OR ops config")
        return

    arg = sys.argv[1].lower()

    if arg == "start":
        handle_start()
        return
    elif arg == "init":
        handle_init()
        return
    elif arg == "config":
        handle_config_command(sys.argv[2:])
        return

    file_name = sys.argv[1]

    if not os.path.exists(file_name):
        print(f"❌ Error: File '{file_name}' not found.")
        return

    # Check configuration
    merged = load_merged_config()
    provider, _ = merged.get("OPS_PROVIDER", (None, "unset"))
    api_key, _ = merged.get("OPS_API_KEY", (None, "unset"))
    api_base, _ = merged.get("OPS_API_BASE", (None, "unset"))
    provider = (provider or "gemini").lower()

    if provider == "ollama":
        # Local Ollama does not require an API key
        pass
    elif provider == "openai-compatible":
        if not api_base:
            print("❌ OpsInsight Error: 'OPS_API_BASE' (OpenAI-compatible base URL) is required!")
            print("👉 Please run `ops config set OPS_API_BASE <URL>` or `ops start` to configure your endpoint.")
            return
    elif provider == "ollama-cloud":
        if not api_key:
            print("❌ OpsInsight Error: API key is required for 'ollama-cloud'!")
            print("👉 Please run `ops config set OPS_API_KEY` or `ops start` to configure your Ollama Cloud API key.")
            return
    elif not api_key:
        print("❌ OpsInsight is not configured with an API key!")
        print("👉 Please run `ops start` or `ops config` to setup your provider and API key.")
        return

    time.sleep(0.5)
    file_type = detect_file_type(file_name)

    try:
        run_program_command = get_run_command(file_name, file_type)
    except ValueError as ve:
        print(f"❌ Error: {ve}")
        return

    program_output = run_program(run_program_command)
    if program_output["success"]:
        pass
    else:
        print("\nError detected!. Analyzing with OpsInsight...")
        time.sleep(0.5)
        analyze_error(program_output["error"])


if __name__ == "__main__":
    main()
