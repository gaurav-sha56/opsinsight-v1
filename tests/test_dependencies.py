import importlib
import pytest
from unittest.mock import patch
import io
import sys

# List of required external dependencies declared in pyproject.toml
REQUIRED_DEPENDENCIES = [
    "questionary",
    "litellm",
    "dotenv",       # package python-dotenv
    "pytest",
    "fastuuid",
    "pydantic_core",
    "tiktoken",
]

# List of internal project modules
INTERNAL_MODULES = [
    "opsinsight",
    "opsinsight.cli",
    "opsinsight.cli.main",
    "opsinsight.cli.commands",
    "opsinsight.core",
    "opsinsight.core.detector",
    "opsinsight.core.compilers",
    "opsinsight.core.runner",
    "opsinsight.config",
    "opsinsight.config.constants",
    "opsinsight.config.manager",
    "opsinsight.ai",
    "opsinsight.ai.brain",
    "opsinsight.ai.resolver",
    "opsinsight.ai.prompts",
    "opsinsight.ai.errors",
    "opsinsight.tools",
    "opsinsight.tools.schemas",
    "opsinsight.tools.fs",
]


class TestDependencies:
    """
    Tests ensuring all dependencies in pyproject.toml and internal modules
    are installed, importable, and won't crash when commands are executed.
    """

    @pytest.mark.parametrize("pkg_name", REQUIRED_DEPENDENCIES)
    def test_required_dependency_is_importable(self, pkg_name):
        """Verify each dependency in pyproject.toml can be imported without error."""
        try:
            mod = importlib.import_module(pkg_name)
            assert mod is not None, f"Module {pkg_name} imported as None"
        except ImportError as exc:
            pytest.fail(f"Required dependency '{pkg_name}' is NOT installed or importable: {exc}")

    @pytest.mark.parametrize("mod_name", INTERNAL_MODULES)
    def test_internal_module_is_importable(self, mod_name):
        """Verify all internal modules can be imported without side effects or crashes."""
        try:
            mod = importlib.import_module(mod_name)
            assert mod is not None, f"Internal module {mod_name} imported as None"
        except ImportError as exc:
            pytest.fail(f"Internal module '{mod_name}' failed to import: {exc}")

    def test_questionary_missing_graceful_handling_in_handle_start(self, monkeypatch):
        """Verify handle_start prints a helpful error instead of crashing if questionary is missing."""
        from opsinsight.cli.commands import handle_start
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        with patch("opsinsight.cli.commands.get_questionary", return_value=None):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                handle_start()
            output = stdout_capture.getvalue()
            # Must not crash, should exit cleanly
            assert "Welcome to OpsInsight Setup Wizard" in output

    def test_questionary_missing_graceful_handling_in_handle_init(self, monkeypatch, tmp_path):
        """Verify handle_init prints a helpful error instead of crashing if questionary is missing."""
        from opsinsight.cli.commands import handle_init
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        with patch("opsinsight.cli.commands.get_questionary", return_value=None):
            with patch("os.getcwd", return_value=str(tmp_path)):
                stdout_capture = io.StringIO()
                with patch("sys.stdout", stdout_capture):
                    handle_init()
                output = stdout_capture.getvalue()
                # Should not raise ModuleNotFoundError
                assert "Initializing OpsInsight workspace" in output

    def test_questionary_missing_graceful_handling_in_interactive_config(self, monkeypatch):
        """Verify run_interactive_config_menu exits cleanly if questionary is missing."""
        from opsinsight.cli.commands import run_interactive_config_menu
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        with patch("opsinsight.cli.commands.get_questionary", return_value=None):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                run_interactive_config_menu()
            # Should return cleanly without unhandled exception

    def test_litellm_missing_graceful_handling_in_start_chat_session(self, monkeypatch):
        """Verify start_chat_session prints an informative message instead of an unhandled exception if litellm is missing."""
        from opsinsight.ai.brain import start_chat_session

        # Simulate ImportError when importing litellm inside start_chat_session()
        orig_import = __import__
        def fake_import(name, *args, **kwargs):
            if name == "litellm":
                raise ImportError("No module named 'litellm'")
            return orig_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                start_chat_session([{"role": "user", "content": "hello"}], config={"OPS_PROVIDER": "gemini", "OPS_API_KEY": "test-key"})
            output = stdout_capture.getvalue()
            assert "Missing required dependency 'litellm'" in output

    def test_ollama_missing_graceful_handling_in_start_chat_session(self, monkeypatch):
        """Verify start_chat_session prints an informative message instead of unhandled exception if ollama is missing."""
        from opsinsight.ai.brain import start_chat_session

        orig_import = __import__
        def fake_import(name, *args, **kwargs):
            if name == "ollama":
                raise ImportError("No module named 'ollama'")
            return orig_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                start_chat_session([{"role": "user", "content": "hello"}], config={"OPS_PROVIDER": "ollama"})
            output = stdout_capture.getvalue()
            assert "Missing required dependency 'ollama'" in output
