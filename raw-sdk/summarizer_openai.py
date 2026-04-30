import os
import json
import openai
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Tool definition shape is different from Anthropic — note the "function" wrapper
# and "parameters" instead of "input_schema"
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file given its path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the file.",
                    }
                },
                "required": ["path"],
            },
        },
    }
]


def read_file(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"


def run_tool(name: str, inputs: dict) -> str:
    if name == "read_file":
        return read_file(inputs["path"])
    return f"Unknown tool: {name}"


def summarize_file(file_path: str) -> str:
    # System prompt goes inside the messages list in OpenAI, not a separate param
    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes files."},
        {"role": "user", "content": f"Please summarize the file at this path in 3-5 sentences: {file_path}"},
    ]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )

        message = response.choices[0].message

        # Append assistant response to history
        messages.append(message)

        finish_reason = response.choices[0].finish_reason

        if finish_reason == "stop":
            return message.content

        if finish_reason == "tool_calls":
            # Run each tool and collect results
            tool_results = []
            for tool_call in message.tool_calls:
                inputs = json.loads(tool_call.function.arguments)
                result = run_tool(tool_call.function.name, inputs)
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            # Feed results back — each tool result is its own message in OpenAI
            messages.extend(tool_results)


def summarize_folder(folder_path: str):
    folder = Path(folder_path)
    files = [f for f in folder.iterdir() if f.is_file()]

    if not files:
        print(f"No files found in {folder_path}")
        return

    print(f"Summarizing {len(files)} file(s) in {folder_path}\n")
    print("=" * 60)

    for file in sorted(files):
        print(f"\nFile: {file.name}")
        print("-" * 40)
        summary = summarize_file(str(file))
        print(summary)
        print()


if __name__ == "__main__":
    summarize_folder("sample_docs")
