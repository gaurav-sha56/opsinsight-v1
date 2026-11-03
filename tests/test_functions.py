import subprocess
import sys
import pytest
from unittest.mock import patch, MagicMock

from opsinsight.core.detector import detect_file_type
from opsinsight.core.compilers import get_run_command, get_file_name
from opsinsight.core.runner import run_program
from opsinsight.cli.main import analyze_error


class TestFunctions:
    """Comprehensive test cases for utils/functions.py."""

    # ==========================
    # detect_file_type Tests
    # ==========================

    @pytest.mark.parametrize("filename,expected", [
        ("main.cpp", "cpp"),
        ("program.c", "c"),
        ("App.java", "java"),
        ("script.py", "python"),
        ("notes.txt", "text"),
        ("config.json", "json"),
        ("deploy.yaml", "yaml"),
        ("deploy.yml", "yaml"),
        ("output.log", "log"),
        ("index.js", "js"),
        ("unknown.xyz", "text"),
        ("no_extension", "text"),
    ])
    def test_detect_file_type(self, filename, expected):
        assert detect_file_type(filename) == expected

    # ==========================
    # get_run_command Tests
    # ==========================

    def test_get_run_command_python(self):
        cmd = get_run_command("script.py", "python")
        assert isinstance(cmd, list)
        assert cmd[1] == "script.py"

    def test_get_run_command_cpp(self):
        cmd = get_run_command("main.cpp", "cpp")
        assert isinstance(cmd, dict)
        assert "compile" in cmd and "run" in cmd
        assert cmd["compile"][0] == "g++"
        assert "-fsanitize=address,undefined" in cmd["compile"]
        assert "main.cpp" in cmd["compile"]

    def test_get_run_command_c(self):
        cmd = get_run_command("program.c", "c")
        assert isinstance(cmd, dict)
        assert cmd["compile"][0] == "gcc"

    def test_get_run_command_java(self):
        cmd = get_run_command("src/Main.java", "java")
        assert isinstance(cmd, dict)
        assert cmd["compile"] == ["javac", "src/Main.java"]
        assert cmd["run"] == ["java", "-cp", "src", "Main"]

    def test_get_run_command_js(self):
        cmd = get_run_command("app.js", "js")
        assert cmd == ["node", "app.js"]

    def test_get_run_command_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported file type: rust"):
            get_run_command("main.rs", "rust")

    # ==========================
    # get_file_name Tests
    # ==========================

    def test_get_file_name_present(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["ops", "test.py"])
        assert get_file_name() == "test.py"

    def test_get_file_name_missing(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["ops"])
        assert get_file_name() is None

    # ==========================
    # run_program Tests
    # ==========================

    def test_run_program_interpreted_success(self):
        """Interpreted script that exits 0 returns success."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "")
        mock_proc.returncode = 0

        with patch("subprocess.Popen", return_value=mock_proc):
            res = run_program(["python3", "dummy.py"])
            assert res == {"success": True}

    def test_run_program_interpreted_runtime_error(self):
        """Interpreted script that exits non-zero with stderr returns runtime error."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "ZeroDivisionError: division by zero\n")
        mock_proc.returncode = 1

        with patch("subprocess.Popen", return_value=mock_proc):
            res = run_program(["python3", "dummy.py"])
            assert res["success"] is False
            assert res["stage"] == "runtime"
            assert "ZeroDivisionError" in res["error"]

    def test_run_program_interpreted_timeout(self):
        """Interpreted script that exceeds timeout is killed and reports timeout error."""
        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd=["python3", "infinite.py"], timeout=2.0),
            ("", "")
        ]

        with patch("subprocess.Popen", return_value=mock_proc):
            res = run_program(["python3", "infinite.py"], timeout=2.0)
            mock_proc.kill.assert_called_once()
            assert res["success"] is False
            assert res["stage"] == "runtime"
            assert "[TIMEOUT ERROR]" in res["error"]

    def test_run_program_compiled_compile_failure(self):
        """Compiled program compilation failure returns compile stage error."""
        mock_compile = MagicMock(returncode=1, stderr="fatal error: iostream: No such file")

        with patch("subprocess.run", return_value=mock_compile):
            cmd_info = {
                "compile": ["g++", "main.cpp", "-o", "main.exe"],
                "run": ["./main.exe"]
            }
            res = run_program(cmd_info)
            assert res["success"] is False
            assert res["stage"] == "compile"
            assert "iostream" in res["error"]

    def test_run_program_compiled_compile_timeout(self):
        """Compiled program compilation timeout returns compile timeout error."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="g++", timeout=15.0)):
            cmd_info = {
                "compile": ["g++", "heavy.cpp", "-o", "heavy.exe"],
                "run": ["./heavy.exe"]
            }
            res = run_program(cmd_info)
            assert res["success"] is False
            assert res["stage"] == "compile"
            assert "[COMPILE TIMEOUT]" in res["error"]

    def test_run_program_compiled_runtime_segfault(self):
        """Compiled binary that segfaults without stderr (code 139/-11) returns explanation."""
        mock_compile = MagicMock(returncode=0)
        mock_run = MagicMock()
        mock_run.communicate.return_value = ("", "")
        mock_run.returncode = 139  # SIGSEGV

        with patch("subprocess.run", return_value=mock_compile), \
             patch("subprocess.Popen", return_value=mock_run):
            cmd_info = {
                "compile": ["g++", "segfault.cpp", "-o", "segfault.exe"],
                "run": ["./segfault.exe"]
            }
            res = run_program(cmd_info)
            assert res["success"] is False
            assert res["stage"] == "runtime"
            assert "Segmentation Fault" in res["error"]

    def test_run_program_compiled_floating_point_exception(self):
        """Binary that crashes with Floating Point Exception (code 136/-8)."""
        mock_compile = MagicMock(returncode=0)
        mock_run = MagicMock()
        mock_run.communicate.return_value = ("", "")
        mock_run.returncode = 136

        with patch("subprocess.run", return_value=mock_compile), \
             patch("subprocess.Popen", return_value=mock_run):
            cmd_info = {"compile": ["gcc", "fpe.c"], "run": ["./fpe.exe"]}
            res = run_program(cmd_info)
            assert res["success"] is False
            assert "Arithmetic / Floating Point Exception" in res["error"]

    def test_run_program_compiled_sigabrt(self):
        """Binary that aborts (SIGABRT code 134/-6)."""
        mock_compile = MagicMock(returncode=0)
        mock_run = MagicMock()
        mock_run.communicate.return_value = ("", "")
        mock_run.returncode = 134

        with patch("subprocess.run", return_value=mock_compile), \
             patch("subprocess.Popen", return_value=mock_run):
            cmd_info = {"compile": ["gcc", "abort.c"], "run": ["./abort.exe"]}
            res = run_program(cmd_info)
            assert res["success"] is False
            assert "Process Aborted / SIGABRT" in res["error"]

    def test_run_program_generic_crash_without_stderr(self):
        """Binary that crashes with unknown non-zero code and no stderr."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "")
        mock_proc.returncode = 42

        with patch("subprocess.Popen", return_value=mock_proc):
            res = run_program(["python3", "exit42.py"])
            assert res["success"] is False
            assert "terminated abnormally with exit code 42" in res["error"]

    def test_run_program_system_exception(self):
        """Missing executable raises OSError, handled as system stage error."""
        with patch("subprocess.Popen", side_effect=FileNotFoundError("node: not found")):
            res = run_program(["node", "app.js"])
            assert res["success"] is False
            assert res["stage"] == "system"
            assert "not found" in res["error"]

    # ==========================
    # analyze_error Tests
    # ==========================

    def test_analyze_error_invokes_brain(self):
        with patch("opsinsight.cli.main.get_prompt", return_value="Analyzed prompt") as mock_prompt, \
             patch("opsinsight.cli.main.start_chat_session") as mock_chat:

            analyze_error("Segmentation fault")

            mock_prompt.assert_called_once_with("Segmentation fault")
            mock_chat.assert_called_once_with([{"role": "user", "content": "Analyzed prompt"}])
