import time
from utils.functions import * # import every helper functions
from utils.llm_handler import send_to_llm # import llm handler function



from utils.commands import handle_start, handle_init, get_api_key
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: ops <file> OR ops start OR ops init")
        return

    arg = sys.argv[1]

    if arg == "start":
        handle_start()
        return
    elif arg == "init":
        handle_init()
        return

    file_name = arg
    
    # Check for API key in global config before launching into execution
    if not get_api_key():
        print("❌ OpsInsight is not configured globally!")
        print("👉 Please run `ops start` to setup your API key and get started.")
        return
    time.sleep(1)   
    file_type = detect_file_type(file_name)   # detect the file type using detect file type function
    
    run_program_command = get_run_command(file_name, file_type)  # run the command 
    program_output = run_program(run_program_command)
    if program_output["success"]:
        # The output was already printed to the terminal natively
        pass
    else:
        print(f"\nError detected!. Analyzing with OpsInsight...\n")
        time.sleep(2)
        analyze_error(program_output["error"])

if __name__ == "__main__":
    main()