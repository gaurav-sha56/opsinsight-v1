import time
import subprocess
import sys
from utils.llm_handler import send_to_llm


def get_file_name():
    if len(sys.argv) < 2:
        print("Usage: ops <file>")
        return None
        
    file = sys.argv[1]
    return file



def detect_file_type(file_name: str) -> str:
    """
    Detects the file type based on the file extension.
    This function helps determine how to process the file content,
    such as applying syntax highlighting for code files or parsing
    structured data formats.
    """
    if file_name.endswith('.cpp'):
        return 'cpp'
    elif file_name.endswith('.c'):
        return 'c'
    elif file_name.endswith('.py'):
        return 'python'
    elif file_name.endswith('.txt'):
        return 'text'
    elif file_name.endswith('.json'):
        return 'json'
    elif file_name.endswith('.yaml') or file_name.endswith('.yml'):
        return 'yaml'
    elif file_name.endswith('.log'):
        return 'log'
    else:
        return 'text'
    

def get_run_command(file_name: str, file_type: str):
    file_type = file_type.lower()

    if file_type == "python":
        return ["python", file_name]

    elif file_type == "cpp":
        # compile + run (two-step)
        exe_name = file_name.replace(".cpp", ".exe")
        return {
            "compile": ["g++", file_name, "-o", exe_name],
            "run": [exe_name]
        }

    elif file_type == "c":
        exe_name = file_name.replace(".c", ".exe")
        return {
            "compile": ["gcc", file_name, "-o", exe_name],
            "run": [exe_name]
        }

    elif file_type == "js":
        return ["node", file_name]

    elif file_type == "java":
        class_name = file_name.replace(".java", "")
        return {
            "compile": ["javac", file_name],
            "run": ["java", class_name]
        }

    else:
        raise ValueError(f"Unsupported file type: {file_type}")
    

def run_program(command_info):
    """
    Executes a program using subprocess.
    Supports both compiled and interpreted languages.
    """

    try:
        # CASE 1: compiled languages (cpp, c, java)
        if isinstance(command_info, dict):

            # Step 1: Compile
            compile_process = subprocess.run(
                command_info["compile"],
                capture_output=True,
                text=True
            )

            if compile_process.returncode != 0:   # if not compiled return the error msg
                return {
                    "success": False,
                    "stage": "compile",
                    "error": compile_process.stderr
                }

            # run the program
            run_process = subprocess.Popen(
                command_info["run"],
                stderr=subprocess.PIPE,
                text=True
            )

        # CASE 2: interpreted languages (python, js)
        # in case of intereted languages, command is 
        # directly run the command whose output is captured in
        # single run_process
        # run_process is for both compiled and interpreted languages
        else:
            run_process = subprocess.Popen(
                command_info,
                stderr=subprocess.PIPE,
                text=True
            )

        # Capture output (stdout will be None because we let it flow naturally to terminal)
        _, stderr = run_process.communicate()

        if run_process.returncode != 0:
            return {
                "success": False,
                "stage": "runtime",
                "error": stderr
            }

        return {
            "success": True
        }

    except Exception as e:
        return {
            "success": False,
            "stage": "system",
            "error": str(e)
        }
    

def analyze_error(error_message: str):
    """
    Main function that initializes ml brain and give the prompt to it
    """
    from utils.prompts import get_prompt
    from google.genai import types
    prompts = get_prompt(error_message)
    contents = [
        types.Content(role="user", parts=[types.Part(text=prompts)])
    ]
    send_to_llm(contents)
    