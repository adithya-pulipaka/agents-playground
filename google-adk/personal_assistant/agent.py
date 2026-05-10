from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from file_summarizer import root_agent as _file_summarizer
from research_agent import root_agent as _research_agent
from daily_digest import root_agent as _digest

from .memory import memory_store, memory_recall

root_agent = LlmAgent(
    name="personal_assistant",
    model=LiteLlm(model="openai/gpt-4o"),
    instruction="""You are Adithya's personal AI assistant with long-term memory.

At the start of every conversation, call memory_recall with the user's first message
to surface any relevant context from past sessions before responding.

When the user asks you to:
- Run the morning digest / what's on today → use the daily_digest tool
- Research a topic / look something up → use the research_agent tool
- Summarise files or documents → use the file_summarizer tool
- Remember something → use memory_store with type "fact" or "preference"

Be conversational and concise. Use recalled memories to personalise responses —
reference past context naturally without being mechanical about it.""",
    tools=[
        memory_recall,
        memory_store,
        AgentTool(agent=_digest),
        AgentTool(agent=_research_agent),
        AgentTool(agent=_file_summarizer),
    ],
)
