import os
import sys
import getpass
from typing import Optional, List

from opsinsight.config.constants import (
    VALID_PROVIDERS,
    VALID_KEYS,
    DEFAULT_MODELS,
    DEFAULT_API_BASES,
    SUGGESTED_MODELS
)
from opsinsight.config.manager import (
    load_merged_config,
    get_config_value,
    set_config_value,
    get_config_paths,
    mask_api_key,
    validate_config_key,
    ensure_gitignore_has_ops_config,
    read_config_file
)


def get_questionary():
    """
    Safely import and return the questionary module.
    If not installed, prints a clear, user-friendly error message.
    """
    try:
        import questionary
        return questionary
    except ImportError:
        print("❌ Error: Missing required dependency 'questionary'.")
        print("👉 Please install dependencies using: pip install questionary (or pip install -e .)")
        return None


def handle_start() -> None:
    """
    First-time interactive setup wizard that configures and writes the GLOBAL config.
    """
    print("🚀 Welcome to OpsInsight Setup Wizard!")
    print("This wizard will configure OpsInsight globally for all your projects.\n")

    if not sys.stdin.isatty():
        print("❌ Error: Interactive setup requires a terminal (TTY).")
        print("👉 Please use: `ops config set <KEY> <VALUE>` to configure non-interactively.")
        return

    questionary = get_questionary()
    if not questionary:
        return

    provider = questionary.select(
        "Choose an LLM provider:",
        choices=[
            "gemini",
            "openai",
            "anthropic",
            "groq",
            "ollama",
            "ollama-cloud",
            "openai-compatible"
        ]
    ).ask()

    if provider is None:
        print("\nSetup cancelled.")
        return

    # Model selection
    suggested = SUGGESTED_MODELS.get(provider, [])
    model_choices = list(suggested) + ["Custom..."]

    selected_model = questionary.select(
        f"Select a model for {provider}:",
        choices=model_choices
    ).ask()

    if selected_model is None:
        print("\nSetup cancelled.")
        return

    if selected_model == "Custom...":
        model = questionary.text(
            "Enter custom model name:",
            default=DEFAULT_MODELS.get(provider, "")
        ).ask()
        if model is None or not model.strip():
            print("\nSetup cancelled.")
            return
        model = model.strip()
    else:
        model = selected_model

    api_base = ""
    api_key = ""

    # Provider-specific endpoint and credentials handling
    if provider == "openai-compatible":
        # Always require API base URL from user; no default fallback
        while True:
            api_base_input = questionary.text(
                "Enter OpenAI-compatible API Base URL (e.g., http://localhost:8000/v1):"
            ).ask()
            if api_base_input is None:
                print("\nSetup cancelled.")
                return
            api_base = api_base_input.strip()
            if api_base:
                break
            print("❌ Error: API Base URL is required for 'openai-compatible'!")

        api_key_input = questionary.password(
            "Enter API Key (press Enter if none required):"
        ).ask()
        if api_key_input is None:
            print("\nSetup cancelled.")
            return
        api_key = api_key_input.strip()

    elif provider == "ollama":
        # Local Ollama inference (runs locally, no API key required by default)
        default_base = DEFAULT_API_BASES.get("ollama", "http://localhost:11434")
        api_base_input = questionary.text(
            "Enter Ollama local host URL:",
            default=default_base
        ).ask()
        if api_base_input is None:
            print("\nSetup cancelled.")
            return
        api_base = api_base_input.strip()

        use_key = questionary.confirm("Does your local Ollama instance require an API key / auth token?", default=False).ask()
        if use_key is None:
            print("\nSetup cancelled.")
            return
        if use_key:
            api_key_input = questionary.password("Enter your Ollama API key / token:").ask()
            if api_key_input is None:
                print("\nSetup cancelled.")
                return
            api_key = api_key_input.strip()

    elif provider == "ollama-cloud":
        # Ollama cloud inference (requires Ollama API key, defaults to https://ollama.com)
        api_base = DEFAULT_API_BASES.get("ollama-cloud", "https://ollama.com")
        api_key_input = questionary.password(
            "Enter your Ollama Cloud API Key:"
        ).ask()
        if api_key_input is None:
            print("\nSetup cancelled.")
            return
        api_key = api_key_input.strip()

    else:
        # Standard cloud providers (gemini, openai, anthropic, groq)
        api_key_input = questionary.password(
            f"Enter your {provider.capitalize()} API Key:"
        ).ask()
        if api_key_input is None:
            print("\nSetup cancelled.")
            return
        api_key = api_key_input.strip()

    # Save to global configuration
    try:
        set_config_value("OPS_PROVIDER", provider, scope="global")
        set_config_value("OPS_MODEL", model, scope="global")
        if api_key:
            set_config_value("OPS_API_KEY", api_key, scope="global")
        if api_base:
            set_config_value("OPS_API_BASE", api_base, scope="global")

        paths = get_config_paths()
        print(f"\n✅ Success! Your global configuration has been saved securely to:")
        print(f"   {paths['global']}")
        print("You can now run `ops <filename>` from ANY folder on your computer!")
    except Exception as e:
        print(f"\n❌ Error saving configuration: {e}")


def handle_init() -> None:
    """
    Interactive setup wizard that initializes the current workspace with a LOCAL .ops.config,
    secures .gitignore, and creates starter files.
    """
    cwd = os.getcwd()

    print(f"🚀 Initializing OpsInsight workspace in:\n   {cwd}\n")

    # Secure .gitignore
    added_to_gitignore = ensure_gitignore_has_ops_config(cwd)
    if added_to_gitignore:
        print("🔒 Protected: Added `.ops.config` to `.gitignore` to prevent secret leaks.")


    if not sys.stdin.isatty():
        print(f"✅ Initialized OpsInsight workspace at {cwd}")
        return

    questionary = get_questionary()
    if not questionary:
        return

    configure_local = questionary.confirm(
        "Would you like to configure project-specific LLM settings in `.ops.config`?",
        default=False
    ).ask()

    if configure_local is True:
        provider = questionary.select(
            "Choose a provider for this project:",
            choices=["(use global)"] + list(VALID_PROVIDERS)
        ).ask()

        if provider is None:
            print("\nInitialization cancelled.")
            return

        if provider and provider != "(use global)":
            set_config_value("OPS_PROVIDER", provider, scope="local", cwd=cwd)

            suggested = SUGGESTED_MODELS.get(provider, [])
            model = questionary.select(
                f"Select model for {provider}:",
                choices=suggested + ["Custom...", "(use global)"]
            ).ask()

            if model is None:
                print("\nInitialization cancelled.")
                return

            if model != "(use global)":
                if model == "Custom...":
                    custom_model = questionary.text("Enter model name:").ask()
                    if custom_model is None:
                        print("\nInitialization cancelled.")
                        return
                    if custom_model.strip():
                        set_config_value("OPS_MODEL", custom_model.strip(), scope="local", cwd=cwd)
                else:
                    set_config_value("OPS_MODEL", model, scope="local", cwd=cwd)

            # Endpoint handling
            if provider == "openai-compatible":
                while True:
                    base_input = questionary.text(
                        "Enter OpenAI-compatible API base URL (e.g. http://localhost:8000/v1):"
                    ).ask()
                    if base_input is None:
                        print("\nInitialization cancelled.")
                        return
                    if base_input.strip():
                        set_config_value("OPS_API_BASE", base_input.strip(), scope="local", cwd=cwd)
                        break
                    print("❌ Error: API Base URL is required for 'openai-compatible'!")
            elif provider == "ollama":
                default_base = DEFAULT_API_BASES.get("ollama", "http://localhost:11434")
                base_input = questionary.text(
                    "Enter Ollama local host URL:",
                    default=default_base
                ).ask()
                if base_input is None:
                    print("\nInitialization cancelled.")
                    return
                if base_input.strip():
                    set_config_value("OPS_API_BASE", base_input.strip(), scope="local", cwd=cwd)
            elif provider == "ollama-cloud":
                set_config_value("OPS_API_BASE", DEFAULT_API_BASES["ollama-cloud"], scope="local", cwd=cwd)

            # API Key handling
            paths = get_config_paths(cwd)
            global_config = read_config_file(paths["global"])
            global_provider = global_config.get("OPS_PROVIDER")
            global_api_key = global_config.get("OPS_API_KEY")

            has_matching_global_key = (
                global_provider == provider and
                global_api_key is not None and
                global_api_key.strip() != ""
            )

            prompt_for_key = False
            if has_matching_global_key:
                masked_key = mask_api_key(global_api_key)
                use_global_key = questionary.confirm(
                    f"A global API key for '{provider}' is already configured ({masked_key}). Use this global API key?",
                    default=True
                ).ask()
                if use_global_key is None:
                    print("\nInitialization cancelled.")
                    return
                if not use_global_key:
                    prompt_for_key = True
            else:
                prompt_for_key = True

            if prompt_for_key:
                if provider in ("ollama", "openai-compatible"):
                    key_input = questionary.password(
                        f"Enter API Key for {provider} (press Enter if none required):"
                    ).ask()
                else:
                    key_input = questionary.password(
                        f"Enter your {provider.capitalize()} API Key:"
                    ).ask()

                if key_input is None:
                    print("\nInitialization cancelled.")
                    return
                if key_input.strip():
                    set_config_value("OPS_API_KEY", key_input.strip(), scope="local", cwd=cwd)

        elif provider == "(use global)":
            paths = get_config_paths(cwd)
            global_config = read_config_file(paths["global"])
            global_api_key = global_config.get("OPS_API_KEY")
            global_provider = global_config.get("OPS_PROVIDER", "gemini")
            if not global_api_key or not global_api_key.strip():
                print(f"\n⚠️ Notice: No global API key is configured for provider '{global_provider}'.")
                if global_provider in ("ollama", "openai-compatible"):
                    key_input = questionary.password(
                        f"Enter API Key for {global_provider} (press Enter if none required):"
                    ).ask()
                else:
                    key_input = questionary.password(
                        f"Enter your {global_provider.capitalize()} API Key (will be saved locally in .ops.config):"
                    ).ask()
                if key_input is None:
                    print("\nInitialization cancelled.")
                    return
                if key_input.strip():
                    set_config_value("OPS_API_KEY", key_input.strip(), scope="local", cwd=cwd)

    print(f"\n✅ Workspace initialized successfully.")
    print("Run `ops main.cpp` or `ops <filename>` to start debugging!")


def handle_config_command(args: List[str]) -> None:
    """
    Handles `ops config` interactive menu and direct subcommands:
    - ops config (interactive)
    - ops config list
    - ops config get <KEY>
    - ops config set <KEY> [VALUE] [--local]
    - ops config path
    """
    if not args:
        run_interactive_config_menu()
        return

    subcmd = args[0].lower()

    if subcmd == "list":
        merged = load_merged_config()
        print("\nOpsInsight Configuration:")
        print("=" * 65)
        for key in sorted(VALID_KEYS):
            val, source = merged.get(key, (None, "unset"))
            display_val = mask_api_key(val) if key == "OPS_API_KEY" else (val or "<not set>")
            tag = f"({source})"
            print(f"  {key:<16} = {display_val:<32} {tag}")
        print("=" * 65 + "\n")

    elif subcmd == "get":
        if len(args) < 2:
            print("❌ Usage: ops config get <KEY>")
            print(f"Valid keys: {', '.join(sorted(VALID_KEYS))}")
            return
        key = args[1].upper()
        if key not in VALID_KEYS:
            print(f"❌ Invalid key '{key}'. Valid keys: {', '.join(sorted(VALID_KEYS))}")
            return
        val, source = get_config_value(key)
        if val is None:
            print(f"{key} is not set.")
        else:
            display_val = mask_api_key(val) if key == "OPS_API_KEY" else val
            print(f"{key} = {display_val} ({source})")

    elif subcmd == "set":
        scope = "local" if "--local" in args else "global"
        clean_args = [a for a in args[1:] if a != "--local"]

        if not clean_args:
            print("❌ Usage: ops config set <KEY> [VALUE] [--local]")
            print(f"Valid keys: {', '.join(sorted(VALID_KEYS))}")
            return

        key = clean_args[0].upper()
        if key not in VALID_KEYS:
            print(f"❌ Invalid key '{key}'. Valid keys: {', '.join(sorted(VALID_KEYS))}")
            return

        if key == "OPS_API_KEY":
            if not sys.stdin.isatty():
                print("❌ Error: API key entry requires an interactive terminal (TTY) for security.")
                return

            questionary = get_questionary()
            if questionary:
                val = questionary.password("Enter API Key (input will be hidden):").ask()
            else:
                val = getpass.getpass("Enter API Key (input will be hidden): ")

            if not val or not val.strip():
                print("❌ API Key cannot be empty.")
                return
            value = val.strip()
        else:
            if len(clean_args) < 2:
                print(f"❌ Usage: ops config set {key} <VALUE> [--local]")
                return
            value = clean_args[1].strip()

        try:
            set_config_value(key, value, scope=scope)
            display_val = mask_api_key(value) if key == "OPS_API_KEY" else value
            print(f"✅ Successfully set {key} = '{display_val}' ({scope})")
        except ValueError as ve:
            print(f"❌ Validation Error: {ve}")

    elif subcmd == "path":
        paths = get_config_paths()
        print("\nOpsInsight Configuration File Locations:")
        print(f"  Local config:  {paths['local']} (exists: {os.path.exists(paths['local'])})")
        print(f"  Global config: {paths['global']} (exists: {os.path.exists(paths['global'])})\n")

    else:
        print(f"❌ Unknown config subcommand: '{subcmd}'")
        print("Usage:")
        print("  ops config                         # Interactive configuration menu")
        print("  ops config list                    # View all configuration settings")
        print("  ops config get <KEY>               # View specific setting")
        print("  ops config set <KEY> <VALUE>       # Set global setting")
        print("  ops config set <KEY> <VAL> --local # Set project-specific setting")
        print("  ops config set OPS_API_KEY [--local] # Securely enter API key")
        print("  ops config path                    # Display configuration file paths")


def run_interactive_config_menu() -> None:
    """Provides a user-friendly terminal menu for viewing and modifying settings."""
    if not sys.stdin.isatty():
        print("❌ Error: Interactive configuration requires an interactive terminal (TTY).")
        print("👉 Use direct subcommands instead:")
        print("   ops config list")
        print("   ops config get <KEY>")
        print("   ops config set <KEY> <VALUE> [--local]")
        print("   ops config set OPS_API_KEY [--local]")
        print("   ops config path")
        return

    questionary = get_questionary()
    if not questionary:
        return

    while True:
        action = questionary.select(
            "What do you want to do?",
            choices=[
                "Change provider",
                "Change model",
                "Change API key",
                "Change API base URL (Ollama / custom endpoints)",
                "View current config",
                "Exit"
            ]
        ).ask()

        if action is None or action == "Exit":
            print("Exiting configuration menu.")
            break

        if action == "View current config":
            handle_config_command(["list"])
            continue

        scope_choice = questionary.select(
            "Where should this be saved?",
            choices=[
                "Global (all projects)",
                "Local (this project only)"
            ]
        ).ask()

        if scope_choice is None:
            continue
        scope = "global" if "Global" in scope_choice else "local"

        if action == "Change provider":
            provider = questionary.select(
                "Choose provider:",
                choices=list(VALID_PROVIDERS)
            ).ask()
            if provider is None:
                continue

            set_config_value("OPS_PROVIDER", provider, scope=scope)
            print(f"✅ Updated OPS_PROVIDER to '{provider}' ({scope})")

            suggested = SUGGESTED_MODELS.get(provider, [])
            update_model = questionary.confirm(f"Update model for {provider} now?", default=True).ask()
            if update_model:
                chosen_model = questionary.select(
                    f"Choose model for {provider}:",
                    choices=suggested + ["Custom..."]
                ).ask()
                if chosen_model == "Custom...":
                    custom_m = questionary.text("Enter model name:").ask()
                    if custom_m and custom_m.strip():
                        set_config_value("OPS_MODEL", custom_m.strip(), scope=scope)
                        print(f"✅ Updated OPS_MODEL to '{custom_m.strip()}' ({scope})")
                elif chosen_model:
                    set_config_value("OPS_MODEL", chosen_model, scope=scope)
                    print(f"✅ Updated OPS_MODEL to '{chosen_model}' ({scope})")

            if provider == "openai-compatible":
                base_input = questionary.text("Enter OpenAI-compatible API base URL (e.g. http://localhost:8000/v1):").ask()
                if base_input and base_input.strip():
                    set_config_value("OPS_API_BASE", base_input.strip(), scope=scope)
                    print(f"✅ Updated OPS_API_BASE to '{base_input.strip()}' ({scope})")
            elif provider == "ollama-cloud":
                set_config_value("OPS_API_BASE", DEFAULT_API_BASES["ollama-cloud"], scope=scope)
                key_input = questionary.password("Enter Ollama Cloud API Key:").ask()
                if key_input and key_input.strip():
                    set_config_value("OPS_API_KEY", key_input.strip(), scope=scope)
                    print(f"✅ Updated OPS_API_KEY ({scope})")
            elif provider == "ollama":
                set_config_value("OPS_API_BASE", DEFAULT_API_BASES["ollama"], scope=scope)

        elif action == "Change model":
            current_provider, _ = get_config_value("OPS_PROVIDER")
            current_provider = current_provider or "gemini"
            suggested = SUGGESTED_MODELS.get(current_provider, [])

            model_choice = questionary.select(
                f"Choose model for provider '{current_provider}':",
                choices=suggested + ["Custom..."]
            ).ask()

            if model_choice is None:
                continue

            if model_choice == "Custom...":
                custom_m = questionary.text("Enter model name:").ask()
                if custom_m and custom_m.strip():
                    set_config_value("OPS_MODEL", custom_m.strip(), scope=scope)
                    print(f"✅ Updated OPS_MODEL to '{custom_m.strip()}' ({scope})")
            else:
                set_config_value("OPS_MODEL", model_choice, scope=scope)
                print(f"✅ Updated OPS_MODEL to '{model_choice}' ({scope})")

        elif action == "Change API key":
            new_key = questionary.password("Enter API Key (input is hidden):").ask()
            if new_key is None or not new_key.strip():
                print("Key was not changed.")
                continue
            set_config_value("OPS_API_KEY", new_key.strip(), scope=scope)
            print(f"✅ Successfully updated OPS_API_KEY ({scope})")

        elif action == "Change API base URL (Ollama / custom endpoints)":
            current_base, _ = get_config_value("OPS_API_BASE")
            default_val = current_base or "http://localhost:11434"
            new_base = questionary.text("Enter API Base URL:", default=default_val).ask()
            if new_base is not None and new_base.strip():
                set_config_value("OPS_API_BASE", new_base.strip(), scope=scope)
                print(f"✅ Successfully updated OPS_API_BASE to '{new_base.strip()}' ({scope})")
