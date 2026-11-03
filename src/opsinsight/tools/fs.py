import os
from typing import Dict, Any, List


def open_file(file_name: str) -> str:
    """Reads and returns the content of the specified file."""
    with open(file_name, "r", encoding="utf-8") as file:
        return file.read()


def write_file(file_name: str, content: str) -> None:
    """Overwrites or creates the specified file with new content."""
    parent = os.path.dirname(file_name)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(content)


def get_file_list(directory: str = ".") -> List[str]:
    """Returns a list of all files in the directory recursively."""
    files: List[str] = []
    for dirpath, dirnames, filenames in os.walk(directory or "."):
        for filename in filenames:
            files.append(os.path.join(dirpath, filename))
    return files


def execute_tool(tool_name: str, args: Dict[str, Any]) -> str:
    """Executes the specified tool with interactive safety checks."""
    if tool_name == "open_file":
        file_name = args.get("file_name", "")
        try:
            return open_file(file_name)
        except Exception as e:
            return f"Error reading file '{file_name}': {str(e)}"

    elif tool_name == "write_file":
        file_name = args.get("file_name", "unknown_file")
        content = args.get("content", "")
        print(f"\n[OpsInsight] The AI wants to apply a fix to '{file_name}'.")
        try:
            user_input = input("Allow this change? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            user_input = "n"

        if user_input in ("y", "yes"):
            try:
                write_file(file_name, content)
                print(f"[OpsInsight] File '{file_name}' was updated successfully.\n")
                return f"Successfully updated '{file_name}'."
            except Exception as e:
                print(f"[OpsInsight] Error updating file '{file_name}': {str(e)}\n")
                return f"Error writing file '{file_name}': {str(e)}"
        else:
            print(f"[OpsInsight] Write operation cancelled. Notifying the AI...\n")
            return "User denied the write operation."

    elif tool_name == "get_file_list":
        directory = args.get("directory", ".")
        print("[OpsInsight] Scanning workspace files...")
        try:
            return str(get_file_list(directory))
        except Exception as e:
            return f"Error scanning workspace: {str(e)}"

    return f"Unknown tool: '{tool_name}'"
