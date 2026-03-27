from google import genai
from google.genai import types
import time
import os

from utils.declaration import *  # import function declarations for tools
from utils.tools import * # import tool implementations
from utils.commands import get_api_key



def stream_words(text):
    # Print character by character to perfectly preserve newlines and formatting
    for char in text:
        print(char, end="", flush=True)
        time.sleep(0.01)


tools = types.Tool(function_declarations=[
    open_file_declaration,
    write_file_declaration
])

config = types.GenerateContentConfig(tools=[tools])



def send_to_llm(contents: list[types.Content]):
    api_key = get_api_key()
    if not api_key:
        print("\n❌ OpsInsight Error: API Key is missing!")
        print("Please run `ops start` to setup your API key globally.")
        return

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",   
        config=config,
        contents=contents,
        )

    candidate = response.candidates[0]
    
    # Extract any text and tools from all parts safely to avoid SDK warnings
    tool_call = None
    text_content = ""
    for p in candidate.content.parts:
        if p.function_call:
            tool_call = p.function_call
        elif p.text:
            text_content += p.text

    # if model wants tool
    if tool_call:
        if text_content.strip():
            print(f"\n💡 OpsInsight: {text_content.strip()}")

        time.sleep(1)
        print(f"⚙ Tool call → {tool_call.name} {tool_call.args}")

        if tool_call.name == "open_file":
            result = open_file(**tool_call.args)

        elif tool_call.name == "write_file":
            file_name_arg = tool_call.args.get('file_name', 'unknown_file')
            print(f"\n[OpsInsight] The AI wants to apply a fix to '{file_name_arg}'.")
            user_input = input(f"Allow this change? [y/N]: ").strip().lower()
            if user_input in ['y', 'yes']:
                result = write_file(**tool_call.args)
                print(f"[OpsInsight] File '{file_name_arg}' was updated successfully.\n")
            else:
                result = "User denied the write operation."
                print(f"[OpsInsight] Write operation cancelled. Notifying the AI...\n")

        else:
            result = "unknown_tool"

        # append model function call
        contents.append(candidate.content)

        # append tool result
        function_response = types.Part.from_function_response(
            name=tool_call.name,
            response={"result": result}
        )

        contents.append(
            types.Content(role="user", parts=[function_response])
        )

        return send_to_llm(contents)  # recursive call to get next response from model after tool use

    else:
        print("\n💡 OpsInsight Analysis\n")
        time.sleep(1)
        stream_words(text_content)
        print("\n")
        
        try:
            user_reply = input("💬 Your Reply (or press Enter to exit): ").strip()
        except (KeyboardInterrupt, EOFError):
            user_reply = ""
            
        if user_reply:
            contents.append(candidate.content)
            contents.append(types.Content(role="user", parts=[types.Part(text=user_reply)]))
            return send_to_llm(contents)
        else:
            print("Exiting OpsInsight. Happy coding!\n")