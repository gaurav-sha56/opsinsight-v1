"""
This module defines the tools declarations for file operations in the local workspace. These declarations specify the name, description, and parameters for each function, enabling structured interactions with files for reading and writing purposes.

"""

open_file_declaration = {
  "name": "open_file",
  "description": "Reads and returns the full text content of a file from the local workspace. Use this function when you need to inspect source code, configuration files, logs, or any text file to understand project context or debug errors.",
  "parameters": {
    "type": "object",
    "properties": {
      "file_name": {
        "type": "string",
        "description": "The relative or absolute path of the file to be opened. Example: 'main.cpp', 'src/app.py', './logs/error.log'."
      }
    },
    "required": ["file_name"]
  }
}

write_file_declaration = {
  "name": "write_file",
  "description": "Creates or overwrites a file with the provided text content. Use this function when you need to generate new source files, update configuration, write fixes, or store logs and analysis results.",
  "parameters": {
    "type": "object",
    "properties": {
      "file_name": {
        "type": "string",
        "description": "The relative or absolute path of the file to write. Example: 'fixed_main.cpp', 'notes/debug_report.txt'."
      },
      "content": {
        "type": "string",
        "description": "The full text content that should be written into the file."
      }
    },
    "required": ["file_name", "content"]
  }
}

get_file_list_declaration = {
  "name": "get_file_list",
  "description": "Returns a complete list of all files and their relative paths within the current workspace directory. Use this tool to inspect the directory structure if a file is not found, or to see if the user misspelled the filename.",
  "parameters": {
    "type": "object",
    "properties": {}
  }
}
