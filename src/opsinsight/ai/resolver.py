from typing import Optional


def resolve_litellm_model(provider: str, model: str) -> str:
    """
    Formats model identifier according to provider conventions.
    For Ollama (local and cloud), strips prefixes and passes clean model name to ollama.Client.
    For LiteLLM providers, prefixes accordingly (e.g. gemini/, anthropic/, groq/, openai/).
    """
    provider = provider.lower().strip()
    model = model.strip()
    

    if provider in ("ollama", "ollama-cloud"):
        if model.startswith("ollama_chat/"):
            return model[len("ollama_chat/"):]
        elif model.startswith("ollama/"):
            return model[len("ollama/"):]
        elif model.startswith("openai/"):
            return model[len("openai/"):]
        return model
    elif provider == "gemini":
        return model if model.startswith("gemini/") else f"gemini/{model}"
    elif provider == "anthropic":
        return model if model.startswith("anthropic/") else f"anthropic/{model}"
    elif provider == "groq":
        return model if model.startswith("groq/") else f"groq/{model}"
    elif provider == "openai-compatible":
        return model if model.startswith("openai/") else f"openai/{model}"
    elif provider == "openai":
        return model
    return model


def validate_credentials(provider: str, api_key: Optional[str], api_base: Optional[str]) -> bool:
    """Validates required keys and base URLs for the selected inference provider."""
    provider = provider.lower().strip()
    api_key = api_key.strip() if api_key else None
    api_base = api_base.strip() if api_base else None
    if provider == "ollama":
        return True

    if provider == "ollama-cloud":
        if not api_key:
            print(f"\n❌ OpsInsight Error: API key is missing for 'ollama-cloud'!")
            print("👉 Run `ops config set OPS_API_KEY` or `ops start` to configure your Ollama Cloud API key.")
            return False
        return True

    if provider == "openai-compatible":
        if not api_base:
            print(f"\n❌ OpsInsight Error: API base URL (OPS_API_BASE) is missing for 'openai-compatible'!")
            print("👉 Run `ops config set OPS_API_BASE <URL>` or `ops start` to configure your endpoint.")
            return False
        return True

    if not api_key:
        print(f"\n❌ OpsInsight Error: API key is missing for provider '{provider}'!")
        print("👉 Run `ops config` or `ops start` to configure your API key.")
        return False

    return True