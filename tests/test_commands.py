import io
import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from opsinsight.cli.commands import (
    handle_start,
    handle_init,
    handle_config_command,
    run_interactive_config_menu,
    get_questionary
)
from opsinsight.config import read_config_file, write_config_file, VALID_KEYS, VALID_PROVIDERS


class TestCommands:
    """Comprehensive test cases for utils/commands.py."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Creates an isolated workspace and global config directory."""
        cwd = tmp_path / "workspace"
        cwd.mkdir()
        global_dir = tmp_path / "global"
        global_dir.mkdir()
        global_config = global_dir / ".ops.config"

        with patch("os.getcwd", return_value=str(cwd)), \
             patch("opsinsight.cli.commands.get_config_paths") as mock_paths, \
             patch("opsinsight.config.manager.get_config_paths") as mock_cfg_paths:
            paths = {
                "local": str(cwd / ".ops.config"),
                "global": str(global_config),
                "legacy": str(global_dir / "config.json")
            }
            mock_paths.return_value = paths
            mock_cfg_paths.return_value = paths
            yield {
                "cwd": cwd,
                "global_config": global_config,
                "local_config": cwd / ".ops.config"
            }

    # ==========================
    # handle_init Tests
    # ==========================

    def test_handle_init_non_interactive(self, temp_workspace, monkeypatch):
        """Non-interactive initialization creates .gitignore and does not create starter template."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            handle_init()

        cwd = temp_workspace["cwd"]
        gitignore = cwd / ".gitignore"

        assert gitignore.exists()
        assert ".ops.config" in gitignore.read_text()
        assert not (cwd / "main.cpp").exists()
        assert not (cwd / ".opsinsight").exists()
        assert "Initialized OpsInsight workspace" in stdout_capture.getvalue()

    def test_handle_init_existing_code_files_not_overwritten(self, temp_workspace, monkeypatch):
        """Does not overwrite or alter existing files in the workspace."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        cwd = temp_workspace["cwd"]
        my_file = cwd / "script.py"
        my_file.write_text("print('custom user solution')")

        handle_init()

        assert my_file.read_text() == "print('custom user solution')"


    def test_handle_init_interactive_decline_local_config(self, temp_workspace, monkeypatch):
        """Interactive init where user declines configuring local LLM settings."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        mock_q = MagicMock()
        mock_q.confirm.return_value.ask.return_value = False

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            handle_init()

        assert not temp_workspace["local_config"].exists()

    def test_handle_init_interactive_configure_local(self, temp_workspace, monkeypatch):
        """Interactive init where user configures local provider, model, and enters API key when not in global."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        mock_q = MagicMock()
        mock_q.confirm.return_value.ask.return_value = True
        mock_q.select.side_effect = [
            MagicMock(ask=MagicMock(return_value="groq")),             # provider
            MagicMock(ask=MagicMock(return_value="llama-3.3-70b-versatile")) # model
        ]
        mock_q.password.return_value.ask.return_value = "gsk_local_key_123"

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            handle_init()

        local_cfg = read_config_file(str(temp_workspace["local_config"]))
        assert local_cfg.get("OPS_PROVIDER") == "groq"
        assert local_cfg.get("OPS_MODEL") == "llama-3.3-70b-versatile"
        assert local_cfg.get("OPS_API_KEY") == "gsk_local_key_123"

    def test_handle_init_interactive_custom_model(self, temp_workspace, monkeypatch):
        """Interactive init where user inputs a custom model."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        mock_q = MagicMock()
        mock_q.confirm.return_value.ask.return_value = True
        mock_q.select.side_effect = [
            MagicMock(ask=MagicMock(return_value="openai")),
            MagicMock(ask=MagicMock(return_value="Custom..."))
        ]
        mock_q.text.return_value.ask.return_value = "custom-openai-preview"
        mock_q.password.return_value.ask.return_value = "sk_custom_proj_key"

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            handle_init()

        local_cfg = read_config_file(str(temp_workspace["local_config"]))
        assert local_cfg.get("OPS_PROVIDER") == "openai"
        assert local_cfg.get("OPS_MODEL") == "custom-openai-preview"
        assert local_cfg.get("OPS_API_KEY") == "sk_custom_proj_key"

    def test_handle_init_uses_matching_global_api_key_when_approved(self, temp_workspace, monkeypatch):
        """When global config has matching provider & key, user can choose to reuse global key."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        # Populate global config with matching provider & key
        write_config_file(str(temp_workspace["global_config"]), {
            "OPS_PROVIDER": "openai",
            "OPS_MODEL": "gpt-4o",
            "OPS_API_KEY": "sk-global-key-12345678"
        })

        mock_q = MagicMock()
        mock_q.confirm.side_effect = [
            MagicMock(ask=MagicMock(return_value=True)),  # configure local settings
            MagicMock(ask=MagicMock(return_value=True))   # reuse global API key
        ]
        mock_q.select.side_effect = [
            MagicMock(ask=MagicMock(return_value="openai")),
            MagicMock(ask=MagicMock(return_value="gpt-4o-mini"))
        ]

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            handle_init()

        local_cfg = read_config_file(str(temp_workspace["local_config"]))
        assert local_cfg.get("OPS_PROVIDER") == "openai"
        assert local_cfg.get("OPS_MODEL") == "gpt-4o-mini"
        # Local API key was NOT written since global key was reused
        assert "OPS_API_KEY" not in local_cfg

    def test_handle_init_overrides_matching_global_api_key(self, temp_workspace, monkeypatch):
        """When global key exists, user can choose NOT to reuse it and specify a local key."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        # Global config has matching provider
        write_config_file(str(temp_workspace["global_config"]), {
            "OPS_PROVIDER": "openai",
            "OPS_MODEL": "gpt-4o",
            "OPS_API_KEY": "sk-global-key-12345678"
        })

        mock_q = MagicMock()
        mock_q.confirm.side_effect = [
            MagicMock(ask=MagicMock(return_value=True)),  # configure local settings
            MagicMock(ask=MagicMock(return_value=False))  # decline reusing global key
        ]
        mock_q.select.side_effect = [
            MagicMock(ask=MagicMock(return_value="openai")),
            MagicMock(ask=MagicMock(return_value="gpt-4o-mini"))
        ]
        mock_q.password.return_value.ask.return_value = "sk-local-override-key"

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            handle_init()

        local_cfg = read_config_file(str(temp_workspace["local_config"]))
        assert local_cfg.get("OPS_PROVIDER") == "openai"
        assert local_cfg.get("OPS_MODEL") == "gpt-4o-mini"
        assert local_cfg.get("OPS_API_KEY") == "sk-local-override-key"

    def test_handle_init_prompts_key_when_global_provider_differs(self, temp_workspace, monkeypatch):
        """When global config has key for Gemini, but local chooses OpenAI, it must prompt for OpenAI key."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        # Global config is Gemini
        write_config_file(str(temp_workspace["global_config"]), {
            "OPS_PROVIDER": "gemini",
            "OPS_MODEL": "gemini-2.5-flash",
            "OPS_API_KEY": "AIzaSyGeminiGlobalKey"
        })

        mock_q = MagicMock()
        mock_q.confirm.side_effect = [
            MagicMock(ask=MagicMock(return_value=True))   # configure local settings
        ]
        mock_q.select.side_effect = [
            MagicMock(ask=MagicMock(return_value="openai")),
            MagicMock(ask=MagicMock(return_value="gpt-4o-mini"))
        ]
        mock_q.password.return_value.ask.return_value = "sk-new-openai-key"

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            handle_init()

        local_cfg = read_config_file(str(temp_workspace["local_config"]))
        assert local_cfg.get("OPS_PROVIDER") == "openai"
        assert local_cfg.get("OPS_MODEL") == "gpt-4o-mini"
        assert local_cfg.get("OPS_API_KEY") == "sk-new-openai-key"

    def test_handle_init_openai_compatible_endpoint_and_key(self, temp_workspace, monkeypatch):
        """OpenAI-compatible provider asks for base URL and API key in ops init."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        mock_q = MagicMock()
        mock_q.confirm.side_effect = [
            MagicMock(ask=MagicMock(return_value=True))   # configure local settings
        ]
        mock_q.select.side_effect = [
            MagicMock(ask=MagicMock(return_value="openai-compatible")),
            MagicMock(ask=MagicMock(return_value="custom-model"))
        ]
        mock_q.text.side_effect = [
            MagicMock(ask=MagicMock(return_value="http://127.0.0.1:1234/v1"))  # base URL
        ]
        mock_q.password.return_value.ask.return_value = "optional-endpoint-token"

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            handle_init()

        local_cfg = read_config_file(str(temp_workspace["local_config"]))
        assert local_cfg.get("OPS_PROVIDER") == "openai-compatible"
        assert local_cfg.get("OPS_MODEL") == "custom-model"
        assert local_cfg.get("OPS_API_BASE") == "http://127.0.0.1:1234/v1"
        assert local_cfg.get("OPS_API_KEY") == "optional-endpoint-token"


    # ==========================
    # handle_start Tests
    # ==========================

    def test_handle_start_non_interactive(self, monkeypatch):
        """Non-interactive terminal should abort handle_start with error."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            handle_start()
        output = stdout_capture.getvalue()
        assert "Interactive setup requires a terminal (TTY)" in output

    def test_handle_start_provider_cancelled(self, monkeypatch):
        """If user cancels provider selection (Ctrl+C / Esc), setup aborts cleanly."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        mock_q = MagicMock()
        mock_q.select.return_value.ask.return_value = None

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                handle_start()
            assert "Setup cancelled." in stdout_capture.getvalue()

    def test_handle_start_api_key_cancelled(self, monkeypatch):
        """If user cancels API key entry, setup aborts cleanly."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        mock_q = MagicMock()
        mock_q.select.side_effect = [
            MagicMock(ask=MagicMock(return_value="gemini")),
            MagicMock(ask=MagicMock(return_value="gemini-2.5-flash"))
        ]
        mock_q.password.return_value.ask.return_value = None

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                handle_start()
            assert "Setup cancelled." in stdout_capture.getvalue()

    def test_handle_start_success_cloud_provider(self, temp_workspace, monkeypatch):
        """Successful setup writes global provider, model, and API key."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        mock_q = MagicMock()
        mock_q.select.side_effect = [
            MagicMock(ask=MagicMock(return_value="gemini")),
            MagicMock(ask=MagicMock(return_value="gemini-2.5-flash"))
        ]
        mock_q.password.return_value.ask.return_value = "AIzaSyTestApiKey"

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            handle_start()

        global_cfg = read_config_file(str(temp_workspace["global_config"]))
        assert global_cfg.get("OPS_PROVIDER") == "gemini"
        assert global_cfg.get("OPS_MODEL") == "gemini-2.5-flash"
        assert global_cfg.get("OPS_API_KEY") == "AIzaSyTestApiKey"

    def test_handle_start_ollama_provider(self, temp_workspace, monkeypatch):
        """Ollama local setup skips API key and asks for endpoint URL."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        mock_q = MagicMock()
        mock_q.select.side_effect = [
            MagicMock(ask=MagicMock(return_value="ollama")),
            MagicMock(ask=MagicMock(return_value="llama3.2:latest"))
        ]
        mock_q.text.return_value.ask.return_value = "http://localhost:11434"
        mock_q.confirm.return_value.ask.return_value = False

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            handle_start()

        global_cfg = read_config_file(str(temp_workspace["global_config"]))
        assert global_cfg.get("OPS_PROVIDER") == "ollama"
        assert global_cfg.get("OPS_MODEL") == "llama3.2:latest"
        assert global_cfg.get("OPS_API_BASE") == "http://localhost:11434"

    def test_handle_start_ollama_cloud_provider(self, temp_workspace, monkeypatch):
        """Ollama Cloud setup sets https://ollama.com and prompts for API key."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        mock_q = MagicMock()
        mock_q.select.side_effect = [
            MagicMock(ask=MagicMock(return_value="ollama-cloud")),
            MagicMock(ask=MagicMock(return_value="llama3.2"))
        ]
        mock_q.password.return_value.ask.return_value = "ollama-cloud-secret-key"

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            handle_start()

        global_cfg = read_config_file(str(temp_workspace["global_config"]))
        assert global_cfg.get("OPS_PROVIDER") == "ollama-cloud"
        assert global_cfg.get("OPS_MODEL") == "llama3.2"
        assert global_cfg.get("OPS_API_KEY") == "ollama-cloud-secret-key"
        assert global_cfg.get("OPS_API_BASE") == "https://ollama.com"

    def test_handle_start_openai_compatible_requires_base_url(self, temp_workspace, monkeypatch):
        """OpenAI-compatible requires user to input API base URL (no default fallback)."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        mock_q = MagicMock()
        mock_q.select.side_effect = [
            MagicMock(ask=MagicMock(return_value="openai-compatible")),
            MagicMock(ask=MagicMock(return_value="custom-model"))
        ]
        mock_q.text.return_value.ask.return_value = "https://custom-openai-server.com/v1"
        mock_q.password.return_value.ask.return_value = "sk-custom-key"

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            handle_start()

        global_cfg = read_config_file(str(temp_workspace["global_config"]))
        assert global_cfg.get("OPS_PROVIDER") == "openai-compatible"
        assert global_cfg.get("OPS_MODEL") == "custom-model"
        assert global_cfg.get("OPS_API_BASE") == "https://custom-openai-server.com/v1"
        assert global_cfg.get("OPS_API_KEY") == "sk-custom-key"

    # ==========================
    # handle_config_command Tests
    # ==========================

    def test_config_list(self, temp_workspace):
        """ops config list outputs all config keys with masked values."""
        write_config_file(str(temp_workspace["global_config"]), {
            "OPS_PROVIDER": "openai",
            "OPS_API_KEY": "sk-1234567890abcdef"
        })

        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            handle_config_command(["list"])

        output = stdout_capture.getvalue()
        assert "OpsInsight Configuration:" in output
        assert "OPS_PROVIDER" in output
        assert "openai" in output
        # API key must be masked
        assert "sk-1234567890abcdef" not in output
        assert "sk-1****cdef" in output

    def test_config_get_valid_key(self, temp_workspace):
        """ops config get KEY returns current value and source."""
        write_config_file(str(temp_workspace["global_config"]), {
            "OPS_PROVIDER": "anthropic"
        })

        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            handle_config_command(["get", "OPS_PROVIDER"])

        output = stdout_capture.getvalue()
        assert "OPS_PROVIDER = anthropic (global)" in output

    def test_config_get_missing_arg(self):
        """ops config get without key prints usage."""
        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            handle_config_command(["get"])
        assert "Usage: ops config get <KEY>" in stdout_capture.getvalue()

    def test_config_get_invalid_key(self):
        """ops config get with invalid key prints error."""
        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            handle_config_command(["get", "INVALID_KEY"])
        assert "Invalid key 'INVALID_KEY'" in stdout_capture.getvalue()

    def test_config_set_global(self, temp_workspace):
        """ops config set KEY VALUE sets global config by default."""
        handle_config_command(["set", "OPS_PROVIDER", "groq"])
        global_cfg = read_config_file(str(temp_workspace["global_config"]))
        assert global_cfg.get("OPS_PROVIDER") == "groq"

    def test_config_set_local(self, temp_workspace):
        """ops config set KEY VALUE --local sets local config."""
        handle_config_command(["set", "OPS_MODEL", "gpt-4o", "--local"])
        local_cfg = read_config_file(str(temp_workspace["local_config"]))
        assert local_cfg.get("OPS_MODEL") == "gpt-4o"

    def test_config_set_invalid_provider(self):
        """ops config set OPS_PROVIDER <bad> fails validation."""
        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            handle_config_command(["set", "OPS_PROVIDER", "not-a-provider"])
        assert "Invalid provider" in stdout_capture.getvalue()

    def test_config_set_missing_args(self):
        """ops config set with no args prints usage."""
        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            handle_config_command(["set"])
        assert "Usage: ops config set" in stdout_capture.getvalue()

    def test_config_path(self, temp_workspace):
        """ops config path shows paths for local, global, and legacy configs."""
        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            handle_config_command(["path"])
        output = stdout_capture.getvalue()
        assert "Local config:" in output
        assert "Global config:" in output

    def test_config_unknown_subcommand(self):
        """ops config unknown prints error and options."""
        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            handle_config_command(["unknown_cmd"])
        output = stdout_capture.getvalue()
        assert "Unknown config subcommand: 'unknown_cmd'" in output

    def test_interactive_config_menu_non_tty(self, monkeypatch):
        """run_interactive_config_menu on non-tty prints error."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            run_interactive_config_menu()
        assert "Interactive configuration requires an interactive terminal (TTY)" in stdout_capture.getvalue()

    def test_interactive_config_menu_exit(self, monkeypatch):
        """run_interactive_config_menu exit choice terminates cleanly."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        mock_q = MagicMock()
        mock_q.select.return_value.ask.return_value = "Exit"

        with patch("opsinsight.cli.commands.get_questionary", return_value=mock_q):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                run_interactive_config_menu()
            assert "Exiting configuration menu." in stdout_capture.getvalue()
