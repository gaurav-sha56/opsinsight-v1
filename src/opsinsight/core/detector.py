def detect_file_type(file_name: str) -> str:
    """
    Detects the programming or data file type based on file extension.
    """
    if file_name.endswith(".cpp"):
        return "cpp"
    elif file_name.endswith(".c"):
        return "c"
    elif file_name.endswith(".java"):
        return "java"
    elif file_name.endswith(".py"):
        return "python"
    elif file_name.endswith(".txt"):
        return "text"
    elif file_name.endswith(".json"):
        return "json"
    elif file_name.endswith(".yaml") or file_name.endswith(".yml"):
        return "yaml"
    elif file_name.endswith(".log"):
        return "log"
    elif file_name.endswith(".js"):
        return "js"
    else:
        return "text"
