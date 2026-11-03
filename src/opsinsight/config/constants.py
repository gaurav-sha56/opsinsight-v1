import os

VALID_KEYS = {
    "OPS_PROVIDER",
    "OPS_MODEL",
    "OPS_API_KEY",
    "OPS_API_BASE"
}

VALID_PROVIDERS = {
    "openai",
    "anthropic",
    "groq",
    "ollama",
    "ollama-cloud",
    "gemini",
    "openai-compatible"
}

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
    "groq": "llama-3.3-70b-versatile",
    "ollama": "llama3.2",
    "ollama-cloud": "llama3.2",
    "gemini": "gemini-2.5-flash",
    "openai-compatible": "custom-model"
}

DEFAULT_API_BASES = {
    "ollama": "http://localhost:11434",
    "ollama-cloud": "https://ollama.com",
}

SUGGESTED_MODELS = {
    "openai": ["gpt-4o-mini", "gpt-4o", "o1-mini", "o3-mini"],
    "anthropic": ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"],
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    "ollama": ["llama3.2", "qwen2.5-coder", "deepseek-r1", "mistral"],
    "ollama-cloud": ["llama3.2", "qwen2.5-coder", "deepseek-r1", "mistral"],
    "gemini": ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    "openai-compatible": ["custom-model", "local-model"]
}

GLOBAL_CONFIG_DIR = os.path.expanduser(os.path.join("~", ".opsinsight"))
GLOBAL_CONFIG_FILE = os.path.join(GLOBAL_CONFIG_DIR, ".ops.config")
LEGACY_GLOBAL_CONFIG_FILE = os.path.join(GLOBAL_CONFIG_DIR, "config.json")
LOCAL_CONFIG_NAME = ".ops.config"
