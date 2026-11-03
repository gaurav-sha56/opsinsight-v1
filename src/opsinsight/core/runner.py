import subprocess
from typing import Dict, Any, Union, List


def run_program(command_info: Union[List[str], Dict[str, List[str]]], timeout: float = 5.0) -> Dict[str, Any]:
    """
    Executes a program using subprocess.
    Supports compiled and interpreted languages with timeout and crash detection.
    """
    try:
        # CASE 1: compiled languages (cpp, c, java)
        if isinstance(command_info, dict):
            # Step 1: Compile with 15s safety timeout
            try:
                compile_process = subprocess.run(
                    command_info["compile"],
                    capture_output=True,
                    text=True,
                    timeout=15.0
                )
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "stage": "compile",
                    "error": "[COMPILE TIMEOUT]: Compilation exceeded 15 seconds."
                }

            if compile_process.returncode != 0:
                return {
                    "success": False,
                    "stage": "compile",
                    "error": compile_process.stderr
                }

            # Step 2: Run the compiled binary
            run_process = subprocess.Popen(
                command_info["run"],
                stderr=subprocess.PIPE,
                text=True
            )

        # CASE 2: interpreted languages (python, js)
        else:
            run_process = subprocess.Popen(
                command_info,
                stderr=subprocess.PIPE,
                text=True
            )

        # Capture output with Watchdog Timeout
        try:
            _, stderr = run_process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            run_process.kill()
            _, stderr = run_process.communicate()
            return {
                "success": False,
                "stage": "runtime",
                "error": (
                    f"[TIMEOUT ERROR]: Execution exceeded {timeout} seconds. "
                    "Possible infinite loop, deadlock, or waiting for user input (cin/input)."
                )
            }

        # Check for runtime errors or silent crashes
        if run_process.returncode != 0:
            code = run_process.returncode

            # If binary crashed without stderr (e.g., Segfault, Arithmetic, Abort)
            if not stderr or not stderr.strip():
                # -11 / 139 = Linux SIGSEGV, 3221225477 / -1073741819 = Windows Access Violation
                if code in (-11, 139, 3221225477, -1073741819):
                    stderr = (
                        f"[RUNTIME CRASH]: Segmentation Fault / Memory Access Violation (Exit Code {code}). "
                        "Inspect the code for null pointer dereferences, uninitialized pointers, or out-of-bounds array/vector access."
                    )
                # -8 / 136 = Floating Point Exception (Division by zero)
                elif code in (-8, 136, 3221225620, -1073741676):
                    stderr = (
                        f"[RUNTIME CRASH]: Arithmetic / Floating Point Exception (Exit Code {code}). "
                        "Check for division or modulo by zero."
                    )
                # -6 / 134 = SIGABRT (assert failure, double free, abort())
                elif code in (-6, 134):
                    stderr = (
                        f"[RUNTIME CRASH]: Process Aborted / SIGABRT (Exit Code {code}). "
                        "Check for failed assertions, memory corruption, or unhandled C++ exceptions."
                    )
                else:
                    stderr = f"[RUNTIME CRASH]: Process terminated abnormally with exit code {code} (no stderr output)."

            return {
                "success": False,
                "stage": "runtime",
                "error": stderr
            }

        return {"success": True}

    except Exception as e:
        return {
            "success": False,
            "stage": "system",
            "error": str(e)
        }
