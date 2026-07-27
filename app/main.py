import argparse
import os
import sys
import json
import subprocess
from openai import OpenAI

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    messages= [{"role": "user", "content": args.p}]
    tools=[{
        "type": "function",
        "function": {
            "name": "Read",
            "description": "Read and return the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to read"
                        }
                    },
                "required": ["file_path"]
                }
            }
        },
           {
               "type": "function",
               "function": {
                   "name": "Write",
                   "description": "Write content to a file",
                   "parameters": {
                       "type": "object",
                       "required": ["file_path", "content"],
                       "properties": {
                           "file_path": {
                               "type": "string",
                               "description": "The path of the file to write to"
                               },
                           "content": {
                               "type": "string",
                               "description": "The content to write to the file"
                               }
                           }
                       }
                   }
               },
           {
               "type": "function",
               "function": {
                   "name": "Bash",
                   "description": "Execute a shell command",
                   "parameters": {
                       "type": "object",
                       "required": ["command"],
                       "properties": {
                           "command": {
                               "type": "string",
                               "description": "The command to execute"
                               }
                           }
                       }
                   }
               }
           ]

    while True:
        chat = client.chat.completions.create(model="anthropic/claude-haiku-4.5", messages=messages, tools=tools)
        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")

        # You can use print statements as follows for debugging, they'll be visible when running tests.
        print("Logs from your program will appear here!", file=sys.stderr)

        r = chat.choices[0]
        if not r.message.tool_calls:
            print(r.message.content)
            break
        messages.append(r.message)
        for tc in r.message.tool_calls or []:
            arguments_dict = json.loads(tc.function.arguments)

            if tc.function.name == "Read":
                path = arguments_dict["file_path"]

                with open(path, "r", encoding="utf-8") as file:
                    content = file.read()
                    messages.append({"role": "tool","tool_call_id": tc.id, "content": content, "name": "Read"})
            elif tc.function.name == "Write":
                path = arguments_dict["file_path"]

                try:
                    with open(path, "w", encoding="utf-8") as file:
                        file.write(arguments_dict["content"])
                        tool_response = "Success"
                except Exception as e:
                    tool_response = f"Error writing file: {str(e)}"
            elif tc.function.name == "Bash":
                tool_response = subprocess.run([arguments_dict["command"]], capture_output=True, text=True)
            messages.append({"role": "tool","tool_call_id": tc.id, "content": tool_response, "name": "Write"})


if __name__ == "__main__":
    main()
