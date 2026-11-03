import os
import sys
import shutil
from typing import Union, List, Dict, Any, Optional


def get_file_name() -> Optional[str]:
    """Helper to retrieve target filename from argv."""
    if len(sys.argv) < 2:
        print("Usage: ops <file>")
        return None
    return sys.argv[1]


def get_run_command(file_name: str, file_type: str) -> Union[List[str], Dict[str, List[str]]]:
    """
    Constructs the appropriate compile and/or execution commands for the specified file.
    """
    file_type = file_type.lower()

    if file_type == "python":
        python_exe = shutil.which("python") or shutil.which("python3") or sys.executable
        return [python_exe, file_name]

    elif file_type in ("cpp", "c"):
        compiler = "g++" if file_type == "cpp" else "gcc"
        exe_path = os.path.abspath(os.path.splitext(file_name)[0] + ".exe")
        return {
            "compile": [compiler, "-g", "-fsanitize=address,undefined", file_name, "-o", exe_path],
            "run": [exe_path]
        }

    elif file_type == "js":
        return ["node", file_name]

    elif file_type == "java":
        java_dir = os.path.dirname(file_name) or "."
        class_name = os.path.splitext(os.path.basename(file_name))[0]
        return {
            "compile": ["javac", file_name],
            "run": ["java", "-cp", java_dir, class_name]
        }

    else:
        raise ValueError(f"Unsupported file type: {file_type}")
