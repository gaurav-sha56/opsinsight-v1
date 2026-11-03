import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from opsinsight.config.manager import (
    parse_dotenv_lines,
    read_config_file,
    write_config_file,
    load_merged_config,
    get_config_value,
    set_config_value,
    validate_config_key,
    mask_api_key,
    ensure_gitignore_has_ops_config,
    migrate_legacy_config,
    VALID_PROVIDERS,
    VALID_KEYS
)
from opsinsight.ai.brain import start_chat_session
from opsinsight.ai.resolver import resolve_litellm_model, validate_credentials
from opsinsight.ai.errors import handle_api_error
from opsinsight.tools.fs import execute_tool
from opsinsight.cli.commands import handle_config_command


class TestConfigEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.cwd = self.test_dir.name
        self.global_dir = os.path.join(self.cwd, ".global_ops")
        os.makedirs(self.global_dir, exist_ok=True)
        self.global_config_path = os.path.join(self.global_dir, ".ops.config")
        self.legacy_config_path = os.path.join(self.global_dir, "config.json")
        self.local_config_path = os.path.join(self.cwd, ".ops.config")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_parse_dotenv_lines(self):
        content = """
        # This is a comment
        OPS_PROVIDER=openai
        OPS_MODEL = "gpt-4o-mini"
        OPS_API_KEY = 'sk-123456789'
        OPS_API_BASE=http://localhost:8000/v1 # inline comments or urls
        """
        parsed = parse_dotenv_lines(content)
        self.assertEqual(parsed["OPS_PROVIDER"], "openai")
        self.assertEqual(parsed["OPS_MODEL"], "gpt-4o-mini")
        self.assertEqual(parsed["OPS_API_KEY"], "sk-123456789")
        self.assertTrue(parsed["OPS_API_BASE"].startswith("http://localhost:8000/v1"))

    @patch("opsinsight.config.manager.GLOBAL_CONFIG_FILE")
    @patch("opsinsight.config.manager.LEGACY_GLOBAL_CONFIG_FILE")
    def test_per_key_merge_priority(self, mock_legacy, mock_global):
        mock_global.__str__ = MagicMock(return_value=self.global_config_path)
        mock_legacy.__str__ = MagicMock(return_value=self.legacy_config_path)

        with patch("opsinsight.config.manager.get_config_paths") as mock_paths:
            mock_paths.return_value = {
                "local": self.local_config_path,
                "global": self.global_config_path,
                "legacy": self.legacy_config_path
            }

            # 1. Global config defines provider, model, and api key
            write_config_file(self.global_config_path, {
                "OPS_PROVIDER": "gemini",
                "OPS_MODEL": "gemini-2.5-flash",
                "OPS_API_KEY": "global-gemini-key"
            })

            # 2. Local config defines ONLY model
            write_config_file(self.local_config_path, {
                "OPS_MODEL": "gpt-4o"
            })

            # Check per-key fallback:
            # Model comes from local, while provider & api key still come from global
            merged = load_merged_config(cwd=self.cwd)
            self.assertEqual(merged["OPS_MODEL"], ("gpt-4o", "local"))
            self.assertEqual(merged["OPS_PROVIDER"], ("gemini", "global"))
            self.assertEqual(merged["OPS_API_KEY"], ("global-gemini-key", "global"))

            # 3. Environment variable overrides both
            with patch.dict(os.environ, {"OPS_MODEL": "claude-3-5-sonnet", "OPS_PROVIDER": "anthropic"}):
                merged_env = load_merged_config(cwd=self.cwd)
                self.assertEqual(merged_env["OPS_MODEL"], ("claude-3-5-sonnet", "env"))
                self.assertEqual(merged_env["OPS_PROVIDER"], ("anthropic", "env"))
                self.assertEqual(merged_env["OPS_API_KEY"], ("global-gemini-key", "global"))

    def test_validation_errors(self):
        # Valid provider
        valid, _ = validate_config_key("OPS_PROVIDER", "groq")
        self.assertTrue(valid)

        # Invalid provider
        valid, err = validate_config_key("OPS_PROVIDER", "unsupported-llm")
        self.assertFalse(valid)
        self.assertIn("Invalid provider", err)

        # Invalid key
        valid, err = validate_config_key("RANDOM_KEY", "value")
        self.assertFalse(valid)
        self.assertIn("Invalid configuration key", err)

    def test_key_masking(self):
        self.assertEqual(mask_api_key(None), "<not set>")
        self.assertEqual(mask_api_key(""), "<not set>")
        self.assertEqual(mask_api_key("1234"), "****")
        self.assertEqual(mask_api_key("sk-proj-1234567890abcdef"), "sk-p****cdef")
        self.assertEqual(mask_api_key("gsk_mygroqsecretkey9999"), "gsk_****9999")

    def test_gitignore_protection(self):
        # Fresh directory without .gitignore
        self.assertTrue(ensure_gitignore_has_ops_config(self.cwd))
        gitignore_path = os.path.join(self.cwd, ".gitignore")
        self.assertTrue(os.path.exists(gitignore_path))
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(".ops.config", content)

        # Re-running does not duplicate
        ensure_gitignore_has_ops_config(self.cwd)
        with open(gitignore_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.read().splitlines() if l.strip() == ".ops.config"]
        self.assertEqual(len(lines), 1)

    def test_legacy_migration(self):
        # Write legacy config.json
        import json
        with open(self.legacy_config_path, "w", encoding="utf-8") as f:
            json.dump({"GEMINI_API_KEY": "legacy-key-xyz"}, f)

        with patch("opsinsight.config.manager.get_config_paths") as mock_paths:
            mock_paths.return_value = {
                "local": self.local_config_path,
                "global": self.global_config_path,
                "legacy": self.legacy_config_path
            }
            migrate_legacy_config()
            self.assertTrue(os.path.exists(self.global_config_path))
            parsed = read_config_file(self.global_config_path)
            self.assertEqual(parsed.get("OPS_API_KEY"), "legacy-key-xyz")
            self.assertEqual(parsed.get("OPS_PROVIDER"), "gemini")


class TestBrainResolution(unittest.TestCase):
    def test_model_formatting(self):
        # Gemini
        self.assertEqual(resolve_litellm_model("gemini", "gemini-2.5-flash"), "gemini/gemini-2.5-flash")

        # Anthropic
        self.assertEqual(resolve_litellm_model("anthropic", "claude-3-5-sonnet"), "anthropic/claude-3-5-sonnet")

        # Groq
        self.assertEqual(resolve_litellm_model("groq", "llama-3.3-70b-versatile"), "groq/llama-3.3-70b-versatile")

        # Ollama local (passed directly to official ollama library)
        self.assertEqual(resolve_litellm_model("ollama", "llama3.2"), "llama3.2")
        self.assertEqual(resolve_litellm_model("ollama", "ollama_chat/llama3.2"), "llama3.2")

        # Ollama cloud (passed directly to official ollama library)
        self.assertEqual(resolve_litellm_model("ollama-cloud", "llama3.2"), "llama3.2")
        self.assertEqual(resolve_litellm_model("ollama-cloud", "ollama/llama3.2"), "llama3.2")

        # OpenAI-compatible
        self.assertEqual(resolve_litellm_model("openai-compatible", "my-local-model"), "openai/my-local-model")

        # OpenAI
        self.assertEqual(resolve_litellm_model("openai", "gpt-4o-mini"), "gpt-4o-mini")

    def test_credential_validation(self):
        # Ollama local does not require key
        self.assertTrue(validate_credentials("ollama", None, "http://localhost:11434"))

        # Ollama cloud requires key
        self.assertFalse(validate_credentials("ollama-cloud", "", "https://ollama.com"))
        self.assertTrue(validate_credentials("ollama-cloud", "valid-key", "https://ollama.com"))

        # OpenAI without key fails
        self.assertFalse(validate_credentials("openai", "", None))
        self.assertTrue(validate_credentials("openai", "valid-key", None))

    def test_tool_execution(self):
        # Test open_file
        with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
            tf.write("test content")
            tf_path = tf.name

        try:
            content = execute_tool("open_file", {"file_name": tf_path})
            self.assertEqual(content, "test content")

            # Test write_file with user denial
            with patch("builtins.input", return_value="n"):
                res = execute_tool("write_file", {"file_name": tf_path, "content": "denied update"})
                self.assertIn("User denied", res)
                # Verify file was NOT modified
                with open(tf_path, "r") as f:
                    self.assertEqual(f.read(), "test content")

            # Test write_file with user approval
            with patch("builtins.input", return_value="y"):
                res = execute_tool("write_file", {"file_name": tf_path, "content": "approved update"})
                self.assertIn("Successfully updated", res)
                # Verify file WAS modified
                with open(tf_path, "r") as f:
                    self.assertEqual(f.read(), "approved update")

            # Test get_file_list
            res = execute_tool("get_file_list", {})
            self.assertIsInstance(res, str)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    @patch("litellm.completion")
    def test_mock_chat_flow_with_tool_call(self, mock_completion):
        # Setup mock for litellm.completion
        # First call returns a tool_call to get_file_list
        tool_call_mock = MagicMock()
        tool_call_mock.id = "call_123"
        tool_call_mock.function.name = "get_file_list"
        tool_call_mock.function.arguments = "{}"

        first_resp = MagicMock()
        first_resp.choices = [
            MagicMock(message=MagicMock(tool_calls=[tool_call_mock], content="Let me inspect the workspace."))
        ]

        # Second call returns the final text
        second_resp = MagicMock()
        second_resp.choices = [
            MagicMock(message=MagicMock(tool_calls=None, content="Found the issue!"))
        ]

        mock_completion.side_effect = [first_resp, second_resp]

        test_config = {"OPS_PROVIDER": "openai", "OPS_MODEL": "gpt-4o-mini", "OPS_API_KEY": "test-key"}
        messages = [{"role": "user", "content": "Help me fix this bug."}]

        # User presses Enter to exit chat
        with patch("builtins.input", return_value=""):
            with patch("opsinsight.ai.brain.stream_words") as mock_stream:
                start_chat_session(messages, config=test_config)

        # Check that litellm was called twice (tool call + final answer)
        self.assertEqual(mock_completion.call_count, 2)
        # Check messages history contains the assistant response and tool output
        roles = [m["role"] for m in messages]
        self.assertIn("tool", roles)
        self.assertIn("assistant", roles)

    @patch("ollama.Client")
    def test_mock_chat_flow_with_ollama_local(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Mock tool call in response
        tc_mock = MagicMock()
        tc_mock.id = "call_ollama_1"
        tc_mock.function.name = "get_file_list"
        tc_mock.function.arguments = {}

        first_resp = MagicMock()
        first_resp.message = MagicMock(tool_calls=[tc_mock], content="Checking workspace files.")

        second_resp = MagicMock()
        second_resp.message = MagicMock(tool_calls=None, content="Everything looks clean.")

        mock_client.chat.side_effect = [first_resp, second_resp]

        test_config = {"OPS_PROVIDER": "ollama", "OPS_MODEL": "llama3.2", "OPS_API_BASE": "http://localhost:11434"}
        messages = [{"role": "user", "content": "Scan project."}]

        with patch("builtins.input", return_value=""):
            with patch("opsinsight.ai.brain.stream_words"):
                start_chat_session(messages, config=test_config)

        mock_client_cls.assert_called_with(host="http://localhost:11434")
        self.assertEqual(mock_client.chat.call_count, 2)
        roles = [m["role"] for m in messages]
        self.assertIn("tool", roles)
        self.assertIn("assistant", roles)

    @patch("ollama.Client")
    def test_mock_chat_flow_with_ollama_cloud(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.message = MagicMock(tool_calls=None, content="Ollama Cloud response.")
        mock_client.chat.return_value = resp

        test_config = {"OPS_PROVIDER": "ollama-cloud", "OPS_MODEL": "llama3.2", "OPS_API_KEY": "my-ollama-key"}
        messages = [{"role": "user", "content": "Hello Ollama Cloud."}]

        with patch("builtins.input", return_value=""):
            with patch("opsinsight.ai.brain.stream_words"):
                start_chat_session(messages, config=test_config)

        mock_client_cls.assert_called_with(host="https://ollama.com", headers={"Authorization": "Bearer my-ollama-key"})
        self.assertEqual(mock_client.chat.call_count, 1)

    def test_handle_api_error_ollama_cloud(self):
        # 401 Unauthorized for ollama-cloud
        import io
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            handle_api_error(Exception("Unauthorized: invalid api key"), "ollama-cloud", "https://ollama.com")
        output = buf.getvalue()
        self.assertIn("Invalid or missing API key for Ollama-cloud", output)
        self.assertIn("https://ollama.com/settings/keys", output)

        # Connection error for ollama-cloud does NOT tell user to run `ollama serve`
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            handle_api_error(ConnectionError("ECONNREFUSED"), "ollama-cloud", "https://ollama.com")
        output = buf.getvalue()
        self.assertIn("Could not connect to Ollama-cloud", output)
        self.assertNotIn("ollama serve", output)
        self.assertIn("https://docs.ollama.com/cloud", output)

        # Connection error for local ollama DOES tell user to run `ollama serve`
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            handle_api_error(ConnectionError("ECONNREFUSED"), "ollama", "http://localhost:11434")
        output = buf.getvalue()
        self.assertIn("ollama serve", output)



class TestCLIBehavior(unittest.TestCase):
    @patch("sys.stdin.isatty", return_value=False)
    def test_non_tty_menu_behavior(self, mock_isatty):
        from io import StringIO
        captured = StringIO()
        with patch("sys.stdout", captured):
            handle_config_command([])
        output = captured.getvalue()
        self.assertIn("requires an interactive terminal (TTY)", output)
        self.assertIn("ops config list", output)

    def test_direct_subcommands(self):
        from io import StringIO
        captured = StringIO()
        with patch("sys.stdout", captured):
            handle_config_command(["list"])
        self.assertIn("OpsInsight Configuration", captured.getvalue())

    def test_api_key_security_rejection_in_cli(self):
        from io import StringIO
        captured = StringIO()
        with patch("sys.stdout", captured):
            # Attempting to pass plain API key on command line should be rejected
            handle_config_command(["set", "OPS_API_KEY", "sk-secret-plain-text"])
        output = captured.getvalue()
        self.assertIn("requires an interactive terminal (TTY) for security", output)


if __name__ == "__main__":
    unittest.main()
