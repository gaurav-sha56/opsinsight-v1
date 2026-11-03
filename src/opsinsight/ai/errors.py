from typing import Optional


def handle_api_error(err: Exception, provider: str, api_base: Optional[str] = None) -> None:
    """Translates provider exceptions into beginner-friendly explanations in English."""
    err_msg = str(err)
    err_lower = err_msg.lower()
    err_type = type(err).__name__
    err_type_lower = err_type.lower()

    status_code = getattr(err, "status_code", None)

    if (
        status_code == 401
        or "401" in err_lower
        or "unauthorized" in err_lower
        or "authenticationerror" in err_type_lower
        or "invalid_api_key" in err_lower
    ):
        print(f"\n❌ OpsInsight Authentication Error: Invalid or missing API key for {provider.capitalize()}.")
        print("👉 Run `ops config set OPS_API_KEY <key>` or `ops start` to configure your API key.")
        if provider == "ollama-cloud":
            print("👉 Get or manage your Ollama Cloud API key from: https://ollama.com/settings/keys")
    elif (
        status_code == 429
        or "429" in err_lower
        or "ratelimiterror" in err_type_lower
        or "resource_exhausted" in err_lower
    ):
        print(f"\n❌ OpsInsight Rate Limit Error: You have exceeded your {provider.capitalize()} API quota or rate limit.")
        print("👉 Please wait a moment for the limit to reset or check your account limits.")
    elif (
        status_code == 404
        or "404" in err_lower
        or "not found" in err_lower
        or "model_not_found" in err_lower
    ):
        print(f"\n❌ OpsInsight Error: Model or endpoint not found on {provider.capitalize()}.")
        if provider == "ollama-cloud":
            print(f"👉 Check the model name against Ollama Cloud catalog (e.g. 'llama3.2', 'qwen2.5-coder', 'deepseek-r1').")
            print("👉 Reference: https://docs.ollama.com/cloud")
        else:
            print(f"👉 Check that your model name and endpoint '{api_base}' are correct.")
    elif (
        "connect" in err_type_lower
        or "connectionerror" in err_type_lower
        or "apiconnectionerror" in err_type_lower
        or "econnrefused" in err_lower
    ):
        print(f"\n❌ OpsInsight Connection Error: Could not connect to {provider.capitalize()} at {api_base or 'default endpoint'}.")
        if provider == "ollama":
            print("👉 If using local Ollama, ensure it is running with: `ollama serve`")
        elif provider == "ollama-cloud":
            print("👉 Ensure you have internet access to reach https://ollama.com.")
            print("👉 Reference: https://docs.ollama.com/cloud")
        elif provider == "openai-compatible":
            print(f"👉 Ensure your OpenAI-compatible server is running and reachable at {api_base}.")
        else:
            print("👉 Please check that your endpoint URL is reachable and currently running.")
    else:
        print(f"\n❌ OpsInsight AI Error ({err_type}): {err_msg}")
