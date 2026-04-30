import os
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

# Tools in ADK are plain Python functions.
# ADK reads the function name, docstring, type hints, and Args block automatically
# to generate the tool schema — no manual JSON needed.
def read_file(path: str) -> dict:
    """Read the contents of a file given its path.

    Args:
        path: Absolute or relative path to the file to read.

    Returns:
        A dict with 'content' (the file text) or 'error' (if reading failed).
    """
    try:
        content = Path(path).read_text(encoding="utf-8")
        return {"content": content}
    except Exception as e:
        return {"error": str(e)}


# LlmAgent is used when connecting to non-Gemini models via LiteLlm.
# LiteLlm uses the "provider/model-name" format as the model string.
root_agent = LlmAgent(
    name="file_summarizer",
    model=LiteLlm(model="openai/gpt-4o"),
    instruction="You are a concise document summarizer. When asked to summarize a file, use the read_file tool to read it first, then provide a clear 3-5 sentence summary.",
    tools=[read_file],
)
