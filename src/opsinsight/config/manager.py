import os
import sys
import json
from pathlib import Path
from typing import Dict, Tuple, Optional, Any

from opsinsight.config.constants import (
    VALID_KEYS,
    VALID_PROVIDERS,
    DEFAULT_MODELS,
    DEFAULT_API_BASES,
    GLOBAL_CONFIG_DIR,
    GLOBAL_CONFIG_FILE,
    LEGACY_GLOBAL_CONFIG_FILE,
    LOCAL_CONFIG_NAME
)


def parse_dotenv_lines(content: str) -> Dict[str, str]:
    """Parses KEY=VALUE pairs while supporting comments and quotes."""
    config: Dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()

            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            else:
                if "#" in val:
                    val = val.split("#", 1)[0].strip()

            if key in VALID_KEYS:
                config[key] = val
    return config


def read_config_file(filepath: str) -> Dict[str, str]:
    """Reads a .ops.config file if it exists, returning parsed dict."""
    if not os.path.isfile(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return parse_dotenv_lines(f.read())
    except Exception:
        return {}


def write_config_file(filepath: str, config_dict: Dict[str, str], is_global: bool = False) -> None:
    """Writes config_dict into filepath in standard dotenv format."""
    parent = os.path.dirname(filepath)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    lines = [
        "# OpsInsight Configuration",
        "# Automatically managed. Do not commit secrets to version control.",
        ""
    ]

    for key in sorted(VALID_KEYS):
        if key in config_dict and config_dict[key] is not None and config_dict[key].strip() != "":
            lines.append(f"{key}={config_dict[key].strip()}")

    content = "\n".join(lines) + "\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    if is_global:
        set_secure_permissions(filepath)


def set_secure_permissions(filepath: str) -> None:
    """Sets 600 file permission (read/write by owner only) on POSIX platforms."""
    try:
        if os.name != "nt":
            os.chmod(filepath, 0o600)
    except Exception:
        pass


def migrate_legacy_config() -> None:
    """Migrates legacy ~/.opsinsight/config.json to ~/.opsinsight/.ops.config if needed."""
    paths = get_config_paths()
    if os.path.isfile(paths["legacy"]) and not os.path.isfile(paths["global"]):
        try:
            with open(paths["legacy"], "r", encoding="utf-8") as f:
                data = json.load(f)
            gemini_key = data.get("GEMINI_API_KEY")
            if gemini_key:
                initial_config = {
                    "OPS_PROVIDER": "gemini",
                    "OPS_MODEL": "gemini-2.5-flash",
                    "OPS_API_KEY": gemini_key
                }
                write_config_file(paths["global"], initial_config, is_global=True)
        except Exception:
            pass


def get_config_paths(cwd: Optional[str] = None) -> Dict[str, str]:
    """Returns local, global, and legacy config file paths."""
    target_cwd = cwd or os.getcwd()
    return {
        "local": os.path.join(target_cwd, LOCAL_CONFIG_NAME),
        "global": GLOBAL_CONFIG_FILE,
        "legacy": LEGACY_GLOBAL_CONFIG_FILE
    }


def load_merged_config(cwd: Optional[str] = None) -> Dict[str, Tuple[Optional[str], str]]:
    """
    Loads merged configuration per key with priority:
    Environment Variable > Local .ops.config > Global .ops.config
    """
    migrate_legacy_config()
    paths = get_config_paths(cwd)

    global_data = read_config_file(paths["global"])
    local_data = read_config_file(paths["local"])

    result: Dict[str, Tuple[Optional[str], str]] = {}

    for key in VALID_KEYS:
        env_val = os.environ.get(key)
        if env_val is not None and env_val.strip() != "":
            result[key] = (env_val.strip(), "env")
        elif key in local_data and local_data[key].strip() != "":
            result[key] = (local_data[key].strip(), "local")
        elif key in global_data and global_data[key].strip() != "":
            result[key] = (global_data[key].strip(), "global")
        else:
            result[key] = (None, "unset")

    return result


def get_config_dict(cwd: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Returns a simple key -> value dictionary of the merged configuration."""
    merged = load_merged_config(cwd)
    return {k: v[0] for k, v in merged.items()}


def get_config_value(key: str, cwd: Optional[str] = None) -> Tuple[Optional[str], str]:
    """Returns (value, source_tag) for a specific configuration key."""
    merged = load_merged_config(cwd)
    return merged.get(key, (None, "unset"))


def validate_config_key(key: str, value: str) -> Tuple[bool, Optional[str]]:
    """Validates a key-value pair."""
    if key not in VALID_KEYS:
        return False, f"Invalid configuration key '{key}'. Valid keys are: {', '.join(sorted(VALID_KEYS))}"

    if key == "OPS_PROVIDER":
        val_lower = value.strip().lower()
        if val_lower not in VALID_PROVIDERS:
            return False, f"Invalid provider '{value}'. Valid providers are: {', '.join(sorted(VALID_PROVIDERS))}"

    return True, None


def set_config_value(key: str, value: str, scope: str = "global", cwd: Optional[str] = None) -> None:
    """Saves a key-value pair to either global or local configuration."""
    is_valid, err = validate_config_key(key, value)
    if not is_valid:
        raise ValueError(err)

    paths = get_config_paths(cwd)
    target_path = paths["local"] if scope == "local" else paths["global"]
    is_global = (scope == "global")

    current_values = read_config_file(target_path)
    current_values[key] = value.strip()
    write_config_file(target_path, current_values, is_global=is_global)


def delete_config_value(key: str, scope: str = "local", cwd: Optional[str] = None) -> bool:
    """Deletes a key from either local or global configuration."""
    paths = get_config_paths(cwd)
    target_path = paths["local"] if scope == "local" else paths["global"]
    is_global = (scope == "global")

    current_values = read_config_file(target_path)
    if key in current_values:
        del current_values[key]
        write_config_file(target_path, current_values, is_global=is_global)
        return True
    return False


def mask_api_key(key: Optional[str]) -> str:
    """Safely masks an API key for console display."""
    if not key:
        return "<not set>"
    key = key.strip()
    length = len(key)
    if length <= 8:
        return "****"
    prefix_len = 4
    suffix_len = 4
    return f"{key[:prefix_len]}****{key[-suffix_len:]}"


def ensure_gitignore_has_ops_config(cwd: Optional[str] = None) -> bool:
    """Ensures .ops.config is present in the project's .gitignore file."""
    target_dir = cwd or os.getcwd()
    gitignore_path = os.path.join(target_dir, ".gitignore")
    entry = ".ops.config"

    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                content = f.read()
            lines = [l.strip() for l in content.splitlines()]
            if entry in lines:
                return True
            with open(gitignore_path, "a", encoding="utf-8") as f:
                if content and not content.endswith("\n"):
                    f.write("\n")
                f.write(f"\n# OpsInsight local configuration\n{entry}\n")
            return True
        except Exception:
            return False
    else:
        try:
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write(f"# OpsInsight local configuration\n{entry}\n")
            return True
        except Exception:
            return False
