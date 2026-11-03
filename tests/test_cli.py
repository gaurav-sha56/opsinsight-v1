import io
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from opsinsight.cli.main import main


class TestOpsCLI:
    """Tests for the main `ops` CLI entry point."""

    def test_main_no_args_shows_usage(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["ops"])
        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            main()
        assert "Usage: ops <file> OR ops start OR ops init OR ops config" in stdout_capture.getvalue()

    def test_main_start_command(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["ops", "start"])
        with patch("opsinsight.cli.main.handle_start") as mock_start:
            main()
            mock_start.assert_called_once()

    def test_main_init_command(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["ops", "init"])
        with patch("opsinsight.cli.main.handle_init") as mock_init:
            main()
            mock_init.assert_called_once()

    def test_main_config_command(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["ops", "config", "list"])
        with patch("opsinsight.cli.main.handle_config_command") as mock_config:
            main()
            mock_config.assert_called_once_with(["list"])

    def test_main_nonexistent_file(self, monkeypatch, tmp_path):
        missing = str(tmp_path / "nonexistent.cpp")
        monkeypatch.setattr(sys, "argv", ["ops", missing])
        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            main()
        output = stdout_capture.getvalue()
        assert "❌ Error: File" in output
        assert "not found" in output

    def test_main_missing_api_key_blocks_cloud_providers(self, monkeypatch, tmp_path):
        dummy_file = tmp_path / "test.cpp"
        dummy_file.write_text("int main() { return 0; }")
        monkeypatch.setattr(sys, "argv", ["ops", str(dummy_file)])

        mock_config = {
            "OPS_PROVIDER": ("gemini", "global"),
            "OPS_API_KEY": (None, "unset")
        }
        with patch("opsinsight.cli.main.load_merged_config", return_value=mock_config):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main()
            output = stdout_capture.getvalue()
            assert "OpsInsight is not configured with an API key" in output

    def test_main_ollama_provider_allows_missing_api_key(self, monkeypatch, tmp_path):
        dummy_file = tmp_path / "test.py"
        dummy_file.write_text("print('hello')")
        monkeypatch.setattr(sys, "argv", ["ops", str(dummy_file)])

        mock_config = {
            "OPS_PROVIDER": ("ollama", "global"),
            "OPS_API_KEY": (None, "unset")
        }
        with patch("opsinsight.cli.main.load_merged_config", return_value=mock_config), \
             patch("opsinsight.cli.main.time.sleep"), \
             patch("opsinsight.cli.main.run_program", return_value={"success": True}) as mock_run:
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main()
            mock_run.assert_called_once()

    def test_main_ollama_cloud_requires_api_key(self, monkeypatch, tmp_path):
        dummy_file = tmp_path / "test.py"
        dummy_file.write_text("print('hello')")
        monkeypatch.setattr(sys, "argv", ["ops", str(dummy_file)])

        mock_config = {
            "OPS_PROVIDER": ("ollama-cloud", "global"),
            "OPS_API_KEY": (None, "unset")
        }
        with patch("opsinsight.cli.main.load_merged_config", return_value=mock_config):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main()
            assert "API key is required for 'ollama-cloud'" in stdout_capture.getvalue()

    def test_main_openai_compatible_requires_api_base(self, monkeypatch, tmp_path):
        dummy_file = tmp_path / "test.py"
        dummy_file.write_text("print('hello')")
        monkeypatch.setattr(sys, "argv", ["ops", str(dummy_file)])

        mock_config = {
            "OPS_PROVIDER": ("openai-compatible", "global"),
            "OPS_API_KEY": (None, "unset"),
            "OPS_API_BASE": (None, "unset")
        }
        with patch("opsinsight.cli.main.load_merged_config", return_value=mock_config):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main()
            assert "OPS_API_BASE" in stdout_capture.getvalue()

    def test_main_successful_execution(self, monkeypatch, tmp_path):
        dummy_file = tmp_path / "test.py"
        dummy_file.write_text("print('hello')")
        monkeypatch.setattr(sys, "argv", ["ops", str(dummy_file)])

        mock_config = {
            "OPS_PROVIDER": ("openai", "global"),
            "OPS_API_KEY": ("sk-test-key", "global")
        }
        with patch("opsinsight.cli.main.load_merged_config", return_value=mock_config), \
             patch("opsinsight.cli.main.time.sleep"), \
             patch("opsinsight.cli.main.run_program", return_value={"success": True}), \
             patch("opsinsight.cli.main.analyze_error") as mock_analyze:
            main()
            mock_analyze.assert_not_called()

    def test_main_failed_execution_triggers_analyze_error(self, monkeypatch, tmp_path):
        dummy_file = tmp_path / "test.py"
        dummy_file.write_text("raise RuntimeError('crash')")
        monkeypatch.setattr(sys, "argv", ["ops", str(dummy_file)])

        mock_config = {
            "OPS_PROVIDER": ("gemini", "global"),
            "OPS_API_KEY": ("gemini-key", "global")
        }
        with patch("opsinsight.cli.main.load_merged_config", return_value=mock_config), \
             patch("opsinsight.cli.main.time.sleep"), \
             patch("opsinsight.cli.main.run_program", return_value={"success": False, "error": "RuntimeError: crash"}), \
             patch("opsinsight.cli.main.analyze_error") as mock_analyze:
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main()
            mock_analyze.assert_called_once_with("RuntimeError: crash")
            assert "Error detected!. Analyzing with OpsInsight..." in stdout_capture.getvalue()

    def test_main_unsupported_file_extension(self, monkeypatch, tmp_path):
        dummy_file = tmp_path / "test.unknown"
        dummy_file.write_text("some content")
        monkeypatch.setattr(sys, "argv", ["ops", str(dummy_file)])

        mock_config = {
            "OPS_PROVIDER": ("gemini", "global"),
            "OPS_API_KEY": ("gemini-key", "global")
        }
        with patch("opsinsight.cli.main.load_merged_config", return_value=mock_config), \
             patch("opsinsight.cli.main.time.sleep"):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main()
            output = stdout_capture.getvalue()
            assert "❌ Error: Unsupported file type" in output
