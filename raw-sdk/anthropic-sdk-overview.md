# Anthropic SDK — How It Works

A mental model for the SDK before reading the official docs. References `summarizer.py` throughout so concepts stay grounded in code you already have.

---

## The One Core Interface: Messages API

Everything in the Anthropic SDK goes through a single method:

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="You are a helpful assistant.",   # optional
    tools=[...],                             # optional
    messages=[...]                           # required
)
```

That's it. There is no separate "chat" API, "completion" API, or "agent" API. All interactions — simple Q&A, multi-turn conversations, tool calling, agentic loops — use `messages.create()` with different inputs.

---

## Message Structure

The `messages` parameter is a list of turns in the conversation. Each turn has a `role` and `content`.

```python
messages = [
    {"role": "user",      "content": "Summarize this file."},
    {"role": "assistant", "content": "Sure, let me read it first."},
    {"role": "user",      "content": "Here is the file content..."},
]
```

**Rules:**
- Must start with a `user` message
- Roles must alternate: user → assistant → user → assistant...
- You pass the **full history** on every call — the API is stateless, it remembers nothing between calls

The stateless design is important: the "memory" of your agent is just this list. Adding a message to it is how you give the model context about what happened before.

---

## Content Blocks

`content` in a message is not always a plain string. It's a list of **content blocks**, each with a `type`. The string shorthand (`"content": "some text"`) is just sugar for a single text block.

| Block type | Who sends it | What it contains |
|------------|-------------|------------------|
| `text` | user or assistant | Plain text |
| `image` | user | Base64 or URL image |
| `document` | user | PDF or plain text document |
| `tool_use` | assistant | A request to call a tool (name + inputs) |
| `tool_result` | user | The output from running a tool |

The assistant's response in `summarizer.py` contains either a `text` block (when it has an answer) or a `tool_use` block (when it needs to call a tool). This is the key distinction driving the agentic loop.

---

## Tool Use — How It Actually Works

This is the most important thing to understand because it's counterintuitive at first.

**The LLM does not call your tools.** It can only ask you to call them.

The flow:

```
You → send messages + tool definitions to API
API → returns a tool_use block: { name: "read_file", input: { path: "..." } }
You → run the actual function in your Python code
You → send the result back as a tool_result block
API → now has the info it needs, returns a final text response
```

In `summarizer.py`:

```python
# Step 1: You define what tools exist
TOOLS = [{"name": "read_file", "input_schema": {...}}]

# Step 2: LLM returns tool_use — you detect it via stop_reason
if response.stop_reason == "tool_use":

    # Step 3: You run the actual function
    result = run_tool(block.name, block.input)

    # Step 4: You feed the result back as a tool_result
    messages.append({"role": "user", "content": [{"type": "tool_result", ...}]})
```

The tool definition (`TOOLS`) is just a description for the LLM — it tells the model what the tool does and what arguments it takes. The actual implementation lives in your Python code.

---

## The Agentic Loop

An agent is just `messages.create()` called in a loop until the model stops requesting tools.

```
┌─────────────────────────────────────────────┐
│  messages = [initial user message]          │
│                                             │
│  while True:                                │
│    response = client.messages.create(...)   │
│    append response to messages              │
│                                             │
│    if stop_reason == "end_turn":  ──────────┼──► done, return text
│    if stop_reason == "tool_use":            │
│      run the tools                          │
│      append tool_results to messages        │
│      continue loop  ◄───────────────────────┤
└─────────────────────────────────────────────┘
```

The messages list grows with each iteration — by the time the loop ends, it contains the full conversation: your request, the model's tool call, your tool result, and the model's final answer.

---

## stop_reason — The Loop Control Signal

`response.stop_reason` tells you why the model stopped generating. It drives the agentic loop.

| stop_reason | Meaning | What to do |
|-------------|---------|------------|
| `end_turn` | Model finished its response naturally | Extract text, you're done |
| `tool_use` | Model wants to call one or more tools | Run the tools, feed results back, loop again |
| `max_tokens` | Hit the token limit mid-response | Increase `max_tokens` or handle truncation |
| `stop_sequence` | Hit a custom stop string you defined | Application-specific handling |

---

## System Prompt

The `system` parameter sets the model's persona and standing instructions. It lives outside the messages list and is not part of the alternating user/assistant turns.

```python
client.messages.create(
    model="claude-sonnet-4-6",
    system="You are a concise summarizer. Always respond in bullet points.",
    messages=[{"role": "user", "content": "Summarize this doc."}]
)
```

Think of it as the briefing you give the model before the conversation starts. It persists for the entire `messages.create()` call but must be re-sent on every new call (remember: the API is stateless).

---

## Models — When to Use Which

| Model | ID | Use when |
|-------|----|----------|
| **Sonnet** | `claude-sonnet-4-6` | Default for most tasks — best balance of speed, cost, and capability |
| **Opus** | `claude-opus-4-7` | Complex reasoning, long documents, tasks where quality matters most |
| **Haiku** | `claude-haiku-4-5-20251001` | High-volume, low-latency, cost-sensitive tasks |

Start with Sonnet. Switch to Opus only if results are insufficient. Use Haiku for tasks that run many times (e.g., classifying thousands of items).

---

## Key Parameters

| Parameter | What it does | Typical values |
|-----------|-------------|----------------|
| `model` | Which Claude model to use | `"claude-sonnet-4-6"` |
| `max_tokens` | Maximum tokens in the response | `1024` for short, `4096` for long |
| `system` | System prompt (model instructions) | A plain string |
| `temperature` | Randomness of responses (0 = deterministic) | `0` for factual/tool tasks, `1` for creative |
| `tools` | List of tool definitions the model can call | Your TOOLS list |
| `tool_choice` | Force or restrict tool use | `{"type": "auto"}` (default) |

---

## The Response Object

```python
response = client.messages.create(...)

response.id            # unique message ID
response.model         # model used
response.stop_reason   # "end_turn" | "tool_use" | "max_tokens"
response.usage         # token counts: input_tokens, output_tokens
response.content       # list of content blocks (text or tool_use)
```

Iterating `response.content` is how you extract what the model returned:

```python
for block in response.content:
    if block.type == "text":
        print(block.text)
    elif block.type == "tool_use":
        print(block.name, block.input)  # tool name and arguments
        print(block.id)                 # needed when sending tool_result back
```

---

## Things to Know For Later

**Streaming:** `client.messages.stream()` lets you receive tokens as they're generated instead of waiting for the full response. Useful for chat UIs where you want the text to appear progressively.

**Prompt caching:** If you send the same large system prompt or document repeatedly, you can mark it with `cache_control` to avoid re-processing it each call. Reduces latency and cost on repeated calls.

**Vision / images:** Pass an `image` content block in a user message. The model can read screenshots, diagrams, charts, etc.

**PDFs:** Pass a `document` content block with base64-encoded PDF content. The model reads the full document without you needing to extract text first.

---

## How summarizer.py Maps to This

```
summarize_folder()          → iterates files, calls summarize_file() per file
summarize_file()            → the agentic loop (while True)
TOOLS                       → tool definition sent to the API
run_tool()                  → your actual Python implementation of the tool
messages list               → the stateful conversation history you manage
stop_reason == "tool_use"   → model asked to read the file
stop_reason == "end_turn"   → model produced the summary, loop exits
```

---

## Reading Order for Official Docs

1. **Messages API overview** — confirms everything above
2. **Tool use guide** — more detail on tool definitions and parallel tool calls
3. **Models overview** — full capability and pricing comparison
4. **Prompt caching** — once you're past the basics and want to optimize costs
5. **Streaming** — when you build anything with a UI
