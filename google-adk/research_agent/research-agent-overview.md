# Research Agent — New ADK Concepts

What this agent introduces on top of the file summarizer. Read this alongside `research_agent/agent.py` and `run_research.py`.

---

## What's New Here

| Concept | Where it appears |
|---------|-----------------|
| Multiple tools | `agent.py` — `tools=[search_web, get_page_content]` |
| Tool selection by the agent | Happens automatically — the agent decides which tool to call and when |
| Structured output with Pydantic | `models.py` + `run_research.py` |
| Instruction prompting for JSON | `agent.py` — the `instruction` field |

---

## Multiple Tools — How the Agent Chooses

In the file summarizer, the agent had one tool and always used it. Here it has two:

- `search_web` — broad search, returns multiple results with snippets
- `get_page_content` — deep fetch, returns full text of a single URL

You don't tell the agent which one to call or when. The `instruction` guides its strategy ("search 2-3 times, then fetch pages if you need detail") but the agent decides the actual sequence. Watch this in `adk web` — you'll see it call `search_web` multiple times with different queries before deciding whether it needs `get_page_content`.

This is multi-step reasoning: the agent plans and executes a sequence of tool calls rather than just one. The ADK loop handles all of it — your code didn't change.

**What the event stream looks like for one research run:**
```
event: tool_use      → search_web("python agent frameworks 2025")
event: tool_result   → 5 search results
event: tool_use      → search_web("pydantic ai vs langchain comparison")
event: tool_result   → 5 more results
event: tool_use      → get_page_content("https://...")   ← agent decided it needed more detail
event: tool_result   → full page text
event: final         → the JSON brief
```

---

## Structured Output — Two Approaches in ADK

### ADK's built-in `output_schema`

ADK supports an `output_schema` parameter on `LlmAgent` that takes a Pydantic model:

```python
root_agent = LlmAgent(
    ...
    output_schema=ResearchBrief,   # ADK forces JSON output matching this schema
)
```

**The catch:** `output_schema` conflicts with tool use in most providers. When the model is forced into JSON-output mode, it can't simultaneously be in tool-calling mode. For a research agent that needs to call tools first and then structure the output, this doesn't work cleanly.

### The approach used here — instruction prompting + manual parsing

Instead, the agent is instructed to format its final response as JSON:

```python
instruction = """...
Return your final response as a JSON object with exactly this structure:
{"topic": "...", "summary": "...", "key_points": [...], "sources": [...]}
Return only the JSON object — no markdown, no extra text."""
```

Then in `run_research.py`, parse and validate with Pydantic:

```python
raw = event.content.parts[0].text   # agent's JSON string
data = json.loads(raw)              # parse JSON
brief = ResearchBrief(**data)       # validate with Pydantic — raises if schema doesn't match
```

**Why this is actually better for tool-using agents:**
- The agent can freely use tools during its work
- Pydantic validates the final output — if the agent returns malformed JSON or missing fields, you get a clear error
- You control the parsing logic — easier to add fallbacks or retries

---

## Pydantic Models — What They Add

`models.py` defines `ResearchBrief`:

```python
class ResearchBrief(BaseModel):
    topic: str
    summary: str
    key_points: list[str]
    sources: list[str]
```

Once the agent's JSON response is parsed into `ResearchBrief`, you get:
- **Type safety** — `brief.key_points` is guaranteed to be a list of strings, not "whatever the LLM returned"
- **Validation** — if the agent forgets a required field, Pydantic raises `ValidationError` immediately
- **IDE autocomplete** — `brief.` shows you the available fields
- **Serialization** — `brief.model_dump()` converts back to a dict; `brief.model_dump_json()` to JSON string

This pattern — agent returns JSON, you validate with Pydantic — is the foundation of every structured-output agent you'll build. The model and the parsing code stay separate, which makes both easier to change.

---

## Running the Research Agent

```bash
# Basic run with default topic
python3 run_research.py

# Custom topic — pass as arguments
python3 run_research.py Google ADK vs LangChain

# Via adk web (select research_agent in the UI)
adk web
```

**What to watch in `adk web`:**
1. How many times the agent calls `search_web` before it's satisfied
2. Whether it decides to call `get_page_content` (it won't always — depends on the topic)
3. The final event containing the raw JSON string before your code parses it

---

## Getting a Tavily API Key

Tavily is a search API built for AI agents. Sign up at tavily.com — the free tier gives 1,000 searches/month, enough for extensive experimentation.

Add the key to your `.env`:
```
TAVILY_API_KEY=tvly-...
```

---

## What's Next After This

Once this is running, the next project is the **daily digest agent** — it adds:
- Google API connectors (Gmail, Calendar) as tools
- Scheduling (run automatically each morning)
- Combining multiple agents: one fetches, one synthesizes
