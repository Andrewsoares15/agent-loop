import argparse
import json
import os
import subprocess

from openai import OpenAI


MODEL = "anthropic/claude-haiku-4.5"
BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "Read",
            "description": "Read and return the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "File to read"}
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Write",
            "description": "Write content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "File to write"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Bash",
            "description": "Execute a shell command",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"}
                },
                "required": ["command"],
            },
        },
    },
]


def run_tool(name, arguments):
    """Run a tool requested by the model and return its result."""
    try:
        if name == "Read":
            with open(arguments["file_path"], encoding="utf-8") as file:
                return file.read()

        if name == "Write":
            with open(arguments["file_path"], "w", encoding="utf-8") as file:
                file.write(arguments["content"])
            return "Success"

        if name == "Bash":
            result = subprocess.run(
                arguments["command"], shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout
            return f"Error (Exit Code {result.returncode}):\n{result.stderr}"

        return f"Error: unknown tool '{name}'"
    except (OSError, KeyError, TypeError) as error:
        return f"Error running {name}: {error}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--prompt", required=True)
    args = parser.parse_args()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    messages = [{"role": "user", "content": args.prompt}]

    while True:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS
        )
        if not response.choices:
            raise RuntimeError("No choices in response")

        message = response.choices[0].message
        if not message.tool_calls:
            print(message.content or "")
            return

        messages.append(message)
        for tool_call in message.tool_calls:
            try:
                arguments = json.loads(tool_call.function.arguments)
                tool_response = run_tool(tool_call.function.name, arguments)
            except json.JSONDecodeError as error:
                tool_response = f"Error: invalid tool arguments: {error}"

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": tool_response,
                }
            )


if __name__ == "__main__":
    main()
