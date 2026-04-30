import asyncio
from pathlib import Path
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from file_summarizer import root_agent

load_dotenv()


async def summarize_file(runner: Runner, session_service: InMemorySessionService, file_path: str) -> str:
    # Each file gets its own session so conversations don't bleed into each other
    session = await session_service.create_session(
        app_name="file_summarizer",
        user_id="user1",
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=f"Please summarize the file at this path: {file_path}")],
    )

    # ADK handles the agentic loop internally — you just iterate events.
    # The loop (call model → run tools → call model again) is invisible to you.
    async for event in runner.run_async(
        user_id="user1",
        session_id=session.id,
        new_message=message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                return event.content.parts[0].text

    return "(no response)"


async def summarize_folder(folder_path: str):
    folder = Path(folder_path)
    files = [f for f in folder.iterdir() if f.is_file()]

    if not files:
        print(f"No files found in {folder_path}")
        return

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="file_summarizer",
        session_service=session_service,
    )

    print(f"Summarizing {len(files)} file(s) in {folder_path}\n")
    print("=" * 60)

    for file in sorted(files):
        print(f"\nFile: {file.name}")
        print("-" * 40)
        summary = await summarize_file(runner, session_service, str(file))
        print(summary)
        print()


if __name__ == "__main__":
    # sample_docs is one level up in raw-sdk/ — reusing the same test files
    asyncio.run(summarize_folder("../raw-sdk/sample_docs"))
