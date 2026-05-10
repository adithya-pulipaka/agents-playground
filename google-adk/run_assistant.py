import asyncio
import sys
from datetime import date
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from personal_assistant import root_agent
from personal_assistant.memory import memory_store

load_dotenv()

APP_NAME = "personal_assistant"
USER_ID = "user1"


async def _run_turn(runner: Runner, session_id: str, text: str) -> str:
    message = types.Content(role="user", parts=[types.Part(text=text)])
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                return event.content.parts[0].text
    return ""


async def _store_session_summary(runner: Runner, session_id: str):
    """Ask the agent to summarise the conversation and persist it to memory."""
    summary = await _run_turn(
        runner,
        session_id,
        "In 1-2 sentences, summarise what we discussed in this conversation.",
    )
    if summary:
        memory_store(content=summary, memory_type="summary")
        print(f"\n[Session saved to memory]")


async def chat():
    """Interactive terminal chat with the personal assistant."""
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    print("\nPersonal Assistant ready. Type 'quit' to exit.\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "bye"):
                break

            response = await _run_turn(runner, session.id, user_input)
            if response:
                print(f"\nAssistant: {response}\n")

    except KeyboardInterrupt:
        pass
    finally:
        await _store_session_summary(runner, session.id)


async def digest():
    """Run the morning digest automatically and store a summary to memory.
    Intended for use as a scheduled cron job:
      0 8 * * * cd /path/to/google-adk && .venv/bin/python run_assistant.py --digest
    """
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    prompt = f"Run my morning digest for today {date.today()} and give me a full summary."
    response = await _run_turn(runner, session.id, prompt)

    if response:
        print(response)
        memory_store(content=f"Digest for {date.today()}: {response}", memory_type="summary")


if __name__ == "__main__":
    if "--digest" in sys.argv:
        asyncio.run(digest())
    else:
        asyncio.run(chat())
