# Personal Assistant — New ADK Concepts

What this agent introduces on top of the previous agents. Read alongside `personal_assistant/agent.py`, `memory.py`, and `run_assistant.py`.

---

## What's New Here

| Concept | Where |
|---------|-------|
| `AgentTool` — existing agents become callable tools | `agent.py` |
| ChromaDB PersistentClient — local vector store on disk | `memory.py` |
| OpenAI embeddings for semantic memory search | `memory.py` |
| Conversation summary stored at session end | `run_assistant.py` |
| Interactive chat loop | `run_assistant.py` |
| `--digest` flag for scheduled/cron use | `run_assistant.py` |

---

## AgentTool — Wrapping Agents as Tools

The key pattern that makes this an orchestrator. In previous agents, tools were plain Python functions. Here, entire agents become tools:

```python
from google.adk.tools.agent_tool import AgentTool

AgentTool(agent=_digest)        # daily_digest agent becomes a tool
AgentTool(agent=_research_agent) # research_agent becomes a tool
AgentTool(agent=_file_summarizer) # file_summarizer becomes a tool
```

When the personal assistant calls `AgentTool(agent=_digest)`, it:
1. Spins up the daily_digest agent in its own session
2. Runs it to completion (including all its internal tool calls)
3. Returns the final response back to the personal assistant

The personal assistant never sees the internal workings — it just gets the result. Watch this in `adk web`: you'll see a nested event stream when an AgentTool fires.

**AgentTool vs sub_agents:** ADK also has a `sub_agents` parameter where the parent transfers control entirely. AgentTool is different — the parent calls it like a function and gets the result back. For an orchestrator that combines results, AgentTool is the right choice.

---

## Memory — How ChromaDB Is Used

```
personal_assistant/
  memory.py         ← ChromaDB client + tool functions
google-adk/
  chroma_data/      ← persisted vector data (auto-created on first run, in .gitignore)
```

### Lazy initialisation
The ChromaDB client is initialised on first use, not at import time. This ensures `OPENAI_API_KEY` is loaded from `.env` before ChromaDB tries to create the embedding function.

### Two tool functions

**`memory_store(content, memory_type)`**
- Generates a UUID, embeds the content via OpenAI `text-embedding-3-small`, stores in ChromaDB
- `memory_type` is metadata: `"fact"`, `"preference"`, or `"summary"`
- The agent calls this when you say "remember that..." or explicitly ask it to note something

**`memory_recall(query, n_results=5)`**
- Embeds the query and runs cosine similarity search against all stored memories
- Returns the top matches with a relevance score (0–1, higher = more similar)
- The agent calls this automatically at the start of each conversation

### What gets stored
- **Facts**: explicit things you tell the assistant ("my deadline is Friday")
- **Preferences**: recurring preferences ("I prefer morning meetings")
- **Summaries**: auto-generated at end of each session — 1-2 sentences of what was discussed

### Persistent storage
`chromadb.PersistentClient(path="./chroma_data")` writes vector data to disk. Data survives restarts. No server needed — ChromaDB handles everything in-process.

---

## run_assistant.py — Two Modes

### Interactive mode (default)
```bash
python3 run_assistant.py
```
- Terminal chat loop: type a message, get a response, repeat
- On exit (quit / Ctrl+C): sends one final message asking for a session summary, stores it to ChromaDB

### Digest mode
```bash
python3 run_assistant.py --digest
```
- Triggers the daily_digest agent automatically via the personal assistant
- Prints the result and stores a summary to memory
- Suitable for a morning cron job:
  ```
  0 8 * * * cd /path/to/google-adk && .venv/bin/python run_assistant.py --digest
  ```

---

## Memory Across Sessions

```
Session 1:
  You: "Remember I prefer not to have meetings before 10am"
  Assistant: calls memory_store("prefers no meetings before 10am", "preference")

Session 2 (next day):
  You: "Can you help me plan my week?"
  Assistant: calls memory_recall("plan week") → retrieves the preference
  Assistant: "I'll keep in mind you prefer no meetings before 10am..."
```

This is the core pattern of a personal assistant that learns over time.

---

## Future: Migrating Memory to MongoDB Atlas

ChromaDB PersistentClient is ideal for local development. When deploying:
1. Replace `chromadb.PersistentClient` with MongoDB Atlas Vector Search client in `memory.py`
2. No changes needed anywhere else — `memory_store` and `memory_recall` are the only interface

The agent, tools, and run scripts are all unaffected by the storage backend swap.

---

## adk web Tips for This Agent

Select `personal_assistant` in the UI and watch:
- `memory_recall` fires on your first message — see what it retrieves
- When you ask for a digest, the `daily_digest` AgentTool fires — nested events appear
- `memory_store` fires when the assistant decides to save something
- Each AgentTool invocation shows its own complete event stream inside the parent's stream
