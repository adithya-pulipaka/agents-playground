import asyncio
import json
import sys
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from research_agent import root_agent
from research_agent.models import ResearchBrief

load_dotenv()


async def research_topic(topic: str) -> ResearchBrief:
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="research_agent",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="research_agent",
        user_id="user1",
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=f"Research this topic and provide a structured brief: {topic}")],
    )

    async for event in runner.run_async(
        user_id="user1",
        session_id=session.id,
        new_message=message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                raw = event.content.parts[0].text
                # The agent returns JSON — parse and validate it with Pydantic.
                # If the agent returns malformed JSON, Pydantic raises a clear error.
                data = json.loads(raw)
                return ResearchBrief(**data)

    raise ValueError("Agent returned no response")


async def main():
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Python agent frameworks in 2025"

    print(f"Researching: {topic}\n")
    brief = await research_topic(topic)

    print(f"Topic:   {brief.topic}")
    print(f"\nSummary:\n{brief.summary}")
    print(f"\nKey Points:")
    for point in brief.key_points:
        print(f"  • {point}")
    print(f"\nSources:")
    for url in brief.sources:
        print(f"  - {url}")


if __name__ == "__main__":
    asyncio.run(main())
