import os
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Paths relative to the google-adk directory where credentials live
_BASE_DIR = Path(__file__).parent.parent
_CREDENTIALS_FILE = _BASE_DIR / "credentials.json"
_TOKEN_FILE = _BASE_DIR / "token.json"


def _get_calendar_service():
    """Builds and returns an authenticated Google Calendar service client.

    On first run, opens a browser for OAuth2 consent and saves token.json.
    On subsequent runs, reuses the saved token (refreshing if expired).
    """
    creds = None
    if _TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(_CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        _TOKEN_FILE.write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def get_todays_meetings() -> dict:
    """Get today's meetings and events from Google Calendar.

    Returns:
        A dict with a 'meetings' list, each item containing title, start_time,
        end_time, and optional location.
    """
    service = _get_calendar_service()

    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

    result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day,
        timeMax=end_of_day,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    meetings = []
    for event in result.get("items", []):
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))
        meetings.append({
            "title": event.get("summary", "Untitled"),
            "start_time": start,
            "end_time": end,
            "location": event.get("location"),
        })

    return {"meetings": meetings}


def get_upcoming_birthdays(days_ahead: int = 7) -> dict:
    """Get upcoming birthdays from the Google Calendar Birthdays calendar.

    Args:
        days_ahead: How many days ahead to look. Defaults to 7.

    Returns:
        A dict with a 'birthdays' list, each item containing name and date.
    """
    service = _get_calendar_service()

    calendars = service.calendarList().list().execute()
    birthday_cal_id = None
    for cal in calendars.get("items", []):
        summary = (cal.get("summaryOverride") or cal.get("summary") or "").lower()
        if "birthday" in summary:
            birthday_cal_id = cal["id"]
            break

    if not birthday_cal_id:
        return {"birthdays": [], "note": "No Birthdays calendar found in Google Calendar"}

    now = datetime.now(timezone.utc)
    future = now + timedelta(days=days_ahead)

    result = service.events().list(
        calendarId=birthday_cal_id,
        timeMin=now.isoformat(),
        timeMax=future.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    birthdays = []
    for event in result.get("items", []):
        date = event["start"].get("date", event["start"].get("dateTime", ""))
        name = event.get("summary", "Unknown")
        for suffix in ["'s Birthday", "'s birthday", " Birthday", " birthday"]:
            name = name.replace(suffix, "")
        birthdays.append({"name": name.strip(), "date": date})

    return {"birthdays": birthdays}


def get_tasks_due_today() -> dict:
    """Get Trello cards that are due today or overdue across all open boards.

    Returns:
        A dict with a 'tasks' list, each item containing title, due, board, and url.
    """
    api_key = os.environ["TRELLO_API_KEY"]
    token = os.environ["TRELLO_TOKEN"]
    today = datetime.now(timezone.utc).date()

    boards_resp = requests.get(
        "https://api.trello.com/1/members/me/boards",
        params={"key": api_key, "token": token, "filter": "open"},
    )
    boards_resp.raise_for_status()

    tasks = []
    for board in boards_resp.json():
        cards_resp = requests.get(
            f"https://api.trello.com/1/boards/{board['id']}/cards",
            params={"key": api_key, "token": token, "due": "incomplete"},
        )
        cards_resp.raise_for_status()

        for card in cards_resp.json():
            if card.get("due"):
                due_date = datetime.fromisoformat(card["due"].replace("Z", "+00:00")).date()
                if due_date <= today:
                    tasks.append({
                        "title": card["name"],
                        "due": card["due"],
                        "board": board["name"],
                        "url": card["shortUrl"],
                    })

    return {"tasks": tasks}
