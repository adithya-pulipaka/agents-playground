import asyncio
import json
from datetime import date
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from daily_digest import root_agent
from daily_digest.models import DigestBrief

load_dotenv()


async def get_digest() -> DigestBrief:
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="daily_digest",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="daily_digest",
        user_id="user1",
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=f"Generate my daily digest for {date.today()}")],
    )

    async for event in runner.run_async(
        user_id="user1",
        session_id=session.id,
        new_message=message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                data = json.loads(event.content.parts[0].text)
                return DigestBrief(**data)

    raise ValueError("Agent returned no response")


def print_digest(brief: DigestBrief):
    print(f"\n{'=' * 50}")
    print(f"  Morning Digest — {brief.date}")
    print(f"{'=' * 50}")

    print(f"\n📅 Meetings ({len(brief.meetings)})")
    if brief.meetings:
        for m in brief.meetings:
            location = f" @ {m.location}" if m.location else ""
            print(f"  {m.start_time} — {m.title}{location}")
    else:
        print("  No meetings today")

    print(f"\n✅ Tasks due ({len(brief.tasks)})")
    if brief.tasks:
        for t in brief.tasks:
            print(f"  [{t.board}] {t.title}")
            print(f"    {t.url}")
    else:
        print("  No tasks due today")

    print(f"\n🎂 Upcoming birthdays ({len(brief.birthdays)})")
    if brief.birthdays:
        for b in brief.birthdays:
            print(f"  {b.name} — {b.date}")
    else:
        print("  No birthdays this week")

    print(f"\n💬 Summary\n  {brief.summary}")
    print()


if __name__ == "__main__":
    brief = asyncio.run(get_digest())
    print_digest(brief)
