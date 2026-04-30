import os
import json
import anthropic
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# --- Tool definition ---
# This tells the LLM what tools it can call and what arguments they take.
# The LLM doesn't run the tool — it just asks us to run it by returning a tool_use block.
TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file given its path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file.",
                }
            },
            "required": ["path"],
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
    """
    This is the agentic loop. It runs until the LLM returns a plain text response
    (stop_reason == "end_turn") instead of a tool call (stop_reason == "tool_use").

    Loop steps:
      1. Send messages to the LLM
      2. LLM returns a tool_use block → we run the tool and feed the result back
      3. LLM returns end_turn → we extract the final text and return it
    """
    messages = [
        {
            "role": "user",
            "content": f"Please summarize the file at this path in 3-5 sentences: {file_path}",
        }
    ]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )

        # Append the assistant's response to the conversation history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract the text from the final response
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "(no text response)"

        if response.stop_reason == "tool_use":
            # The LLM wants to call one or more tools — run each one and collect results
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            # Feed all tool results back into the conversation as a user message
            messages.append({"role": "user", "content": tool_results})


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
