import os
import json
import sys

CONFIG_DIR = os.path.expanduser("~/.opsinsight")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def handle_start():
    print("🚀 Welcome to OpsInsight!")
    print("To get started, you need a Google Gemini API Key.")
    print("You can get one for free at: https://aistudio.google.com/app/apikey\n")
    
    api_key = input("Paste your Gemini API Key here: ").strip()
    
    if not api_key:
        print("❌ Error: API Key cannot be empty. Setup aborted.")
        sys.exit(1)
        
    # Ensure config directory exists
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # Save key securely
    with open(CONFIG_FILE, "w") as f:
        json.dump({"GEMINI_API_KEY": api_key}, f, indent=4)
        
    print(f"\n✅ Success! Your API key has been securely saved globally at {CONFIG_FILE}")
    print("You can now run `ops <filename>` from ANY folder on your computer!")

def handle_init():
    cwd = os.getcwd()
    local_ops_dir = os.path.join(cwd, ".opsinsight")
    
    if os.path.exists(local_ops_dir):
        print("⚠️ OpsInsight workspace is already initialized in this directory.")
        return
        
    # Create local hidden directory
    os.makedirs(local_ops_dir, exist_ok=True)
    
    # Create a simple main.cpp template
    cpp_template = """#include <iostream>

int main() {
    std::cout << "Hello OpsInsight!" << std::endl;
    
    // Try forcing an error below to test the AI tutor!
    // int x;
    // std::cout << x; // Uninitialized variable
    
    return 0;
}
"""
    main_cpp_path = os.path.join(cwd, "main.cpp")
    if not os.path.exists(main_cpp_path):
        with open(main_cpp_path, "w") as f:
            f.write(cpp_template)
        
    print("✅ Initialized empty OpsInsight workspace in current directory.")
    print("✨ Created a starter `main.cpp` file.")
    print("Run `ops main.cpp` to see OpsInsight in action!")

def get_api_key():
    """Retrieve the API key from the global config file."""
    if not os.path.exists(CONFIG_FILE):
        return None
        
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("GEMINI_API_KEY")
    except Exception:
        return None
