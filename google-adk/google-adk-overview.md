# Google ADK — How It Works

A mental model for ADK before reading the official docs. References `file_summarizer/agent.py` and `main.py` throughout so concepts stay grounded in code you already have. Compare this with `../raw-sdk/anthropic-sdk-overview.md` to see what ADK eliminates.

---

## The Core Idea

In the raw SDK you wrote the agentic loop yourself:
- Called the API
- Checked `stop_reason`
- Ran tools manually
- Fed results back
- Repeated until done

**ADK hides all of that.** You define your agent and tools once, and ADK runs the loop internally. You only see the final result (and intermediate events if you want them).

---

## Key Components

```
Agent (LlmAgent)          → what the agent is (model, instructions, tools)
Tool (Python function)    → what the agent can do
Runner                    → executes the agent against a session
Session                   → a single conversation context (memory for one run)
InMemorySessionService    → manages sessions (stores them in memory)
Event                     → a step in the agent's execution (tool call, response, etc.)
```

---

## Agent — Defining What the Agent Is

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

root_agent = LlmAgent(
    name="file_summarizer",
    model=LiteLlm(model="openai/gpt-4o"),
    instruction="You are a concise summarizer...",
    tools=[read_file],
)
```

**`Agent` vs `LlmAgent`:**
- Use `Agent` with native Gemini models (model is a plain string: `"gemini-2.0-flash"`)
- Use `LlmAgent` with any other provider via LiteLLM (model is a `LiteLlm(model=...)` object)

**`instruction`** is the system prompt — ADK sends it automatically on every run. You don't manage it yourself.

**`tools`** is a list of plain Python functions. ADK inspects them to generate tool schemas automatically (more on this below).

---

## Tools — Plain Python Functions

This is the biggest ergonomic improvement over raw SDK. In the raw SDK you wrote JSON schemas by hand:

```python
# Raw SDK — you wrote this manually
TOOLS = [{"name": "read_file", "input_schema": {"type": "object", "properties": {...}}}]
```

In ADK, you just write a Python function:

```python
def read_file(path: str) -> dict:
    """Read the contents of a file given its path.

    Args:
        path: Absolute or relative path to the file to read.

    Returns:
        A dict with 'content' (the file text) or 'error' (if reading failed).
    """
    try:
        return {"content": Path(path).read_text(encoding="utf-8")}
    except Exception as e:
        return {"error": str(e)}
```

ADK reads:
- **Function name** → tool name
- **Docstring** → tool description
- **`Args:` block in docstring** → parameter descriptions
- **Type hints** → parameter types and schema
- **Return type** → expected output shape

**Return dicts, not strings.** ADK expects tools to return dicts. If you return a plain string, ADK wraps it in `{"result": "..."}`. Returning structured dicts keeps things clean and predictable.

---

## Models — Gemini Native vs LiteLLM

| Model type | How to specify | Example |
|------------|----------------|---------|
| Gemini (native) | Plain string in `Agent` | `model="gemini-2.0-flash"` |
| OpenAI via LiteLLM | `LiteLlm` wrapper in `LlmAgent` | `model=LiteLlm(model="openai/gpt-4o")` |
| Anthropic via LiteLLM | `LiteLlm` wrapper in `LlmAgent` | `model=LiteLlm(model="anthropic/claude-sonnet-4-6")` |

LiteLLM uses the `"provider/model-name"` format. It reads the standard provider env vars (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) automatically.

Switching from OpenAI to Gemini is two changes: swap `LlmAgent` → `Agent`, and swap the model string. Your tool functions and instructions stay identical.

---

## Project Structure — The `root_agent` Convention

```
file_summarizer/
  __init__.py    ← exports root_agent
  agent.py       ← defines root_agent
main.py          ← runs the agent
```

ADK discovers your agent by looking for a variable named **`root_agent`**. This matters when using the ADK CLI tools (`adk run`, `adk web`). For programmatic use (like `main.py`) you can import it directly, but naming it `root_agent` is convention you should follow.

---

## Runner and Sessions — Running the Agent

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

session_service = InMemorySessionService()

runner = Runner(
    agent=root_agent,
    app_name="file_summarizer",
    session_service=session_service,
)
```

**`Runner`** — the execution engine. It knows which agent to run and where to store session state.

**`SessionService`** — manages conversation history. `InMemorySessionService` stores everything in memory (gone when the process stops). For persistent agents, you'd swap this for a database-backed implementation.

**`Session`** — a single conversation context. Think of it as one chat window. Each session has its own message history. In `main.py`, each file gets its own session so summaries don't bleed into each other.

```python
session = await session_service.create_session(
    app_name="file_summarizer",
    user_id="user1",
)
```

---

## Running the Agent — Messages and Events

```python
message = types.Content(
    role="user",
    parts=[types.Part(text="Summarize the file at: sample_docs/notes.txt")],
)

async for event in runner.run_async(
    user_id="user1",
    session_id=session.id,
    new_message=message,
):
    if event.is_final_response():
        print(event.content.parts[0].text)
```

**`types.Content` / `types.Part`** — how you structure messages to send to the agent. `Content` is a message, `Part` is a piece of content within it (text, image, etc.). This mirrors the Google Gen AI SDK message format.

**`runner.run_async()`** — triggers the agent. It yields a stream of events as the agent works.

**Events** — everything the agent does produces an event: tool calls, tool results, intermediate model outputs, and the final response. You typically only care about `is_final_response()`.

---

## Events — What's Happening Inside the Loop

Even though ADK hides the agentic loop, you can watch it through events:

| Event type | What it means |
|------------|---------------|
| Tool call event | Agent decided to call one of your tools |
| Tool result event | Your tool ran and returned a result |
| Model output event | An intermediate model response (before tools finish) |
| Final response event | The agent is done — extract text here |

```python
async for event in runner.run_async(...):
    if event.is_final_response():
        # This is the only one you usually care about
        text = event.content.parts[0].text
```

---

## The Agentic Loop — What ADK Is Doing For You

This is what you wrote manually in `raw-sdk/summarizer.py` and what ADK now handles internally:

```
You send a message
  └─► ADK calls the model
        └─► Model requests a tool call
              └─► ADK runs your tool function
                    └─► ADK feeds the result back to the model
                          └─► Model produces final response
                                └─► ADK emits a final_response event
                                      └─► You receive it
```

In `raw-sdk/summarizer.py` you wrote ~30 lines for this loop. In ADK it's handled inside `runner.run_async()`.

---

## What ADK Eliminated vs Raw SDK

| Raw SDK | ADK |
|---------|-----|
| Manually write JSON tool schemas | Define a Python function — ADK generates the schema |
| Write the `while True` agentic loop | `runner.run_async()` handles it |
| Manage the messages list yourself | `SessionService` manages conversation history |
| Pass the full history on every call | ADK handles state per session |
| Check `stop_reason` to detect tool calls | ADK routes tool calls automatically |
| Append tool results to messages manually | ADK feeds results back automatically |

---

## ADK CLI Tools (Bonus)

Because you used the `root_agent` convention and the package structure, you also get these for free:

```bash
# Run your agent interactively in the terminal
adk run file_summarizer

# Launch a local web UI to chat with your agent and inspect events
adk web
```

`adk web` is particularly useful — it shows you every event (tool calls, results, model outputs) as the agent runs, which is a great way to understand what's happening inside the loop.

---

## Reading Order for Official Docs

1. **Quickstart** — confirms setup and the root_agent convention
2. **Agents (LlmAgent)** — full Agent/LlmAgent parameters
3. **Tools → Function Tools** — more on how ADK inspects your functions
4. **Models → LiteLLM** — connecting non-Gemini models
5. **Runtime → Sessions** — persistent sessions beyond InMemorySessionService
6. **Events** — full event schema when you need to inspect intermediate steps
