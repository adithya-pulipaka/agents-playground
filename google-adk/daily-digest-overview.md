# Daily Digest Agent — Setup & Concepts

What this agent introduces on top of the research agent. Read before running.

---

## What's New Here

| Concept | Where |
|---------|-------|
| Real external API integrations | `tools.py` — Google Calendar + Trello |
| Google OAuth2 flow | `tools.py` — `_get_calendar_service()` |
| Token persistence | `token.json` saved after first auth |
| Multiple data sources combined | `agent.py` — 3 tools called and synthesized |

---

## Future Improvements

### Google Calendar — switch to a service account
The current implementation uses OAuth2 which opens a browser consent popup on first run. For a personal assistant you control, a **service account** is cleaner:
- No browser popup ever — auth is a downloaded JSON key file
- Credentials don't expire (no refresh token needed)
- One-time setup: share your Google Calendar with the service account's email in Calendar settings

Trello auth is fine as-is — the `expiration=never` token generated once is the correct permanent credential for a personal tool. No changes needed there.

---

## One-Time Setup

### 1. Google Calendar credentials

1. Go to **console.cloud.google.com** → create a project (or reuse one)
2. Enable the **Google Calendar API** for the project
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
4. Application type: **Desktop app**
5. Download the JSON file and save it as `google-adk/credentials.json`

First time you run `run_digest.py`, a browser window opens asking you to authorise access. After approving, `token.json` is saved next to `credentials.json`. Subsequent runs skip the browser entirely.

Both files are in `.gitignore` — never commit them.

### 2. Trello API key and token

1. Go to **trello.com/power-ups/admin** → create a new Power-Up (name it anything)
2. Click **API Key** — copy it
3. On the same page, click **Token** link → approve → copy the token
4. Add both to your `.env`:

```
TRELLO_API_KEY=your-api-key
TRELLO_TOKEN=your-token
```

---

## How the OAuth2 Flow Works

```python
def _get_calendar_service():
    creds = None

    # 1. Try loading a saved token from a previous run
    if token.json exists:
        creds = load from token.json

    # 2. If no valid token, get one
    if not creds or not creds.valid:
        if token is expired but has refresh_token:
            creds.refresh()          # silent background refresh
        else:
            open browser → user approves → get new token

    # 3. Save for next time
    save creds to token.json

    return Calendar API client
```

The browser only opens **once** (or if you delete `token.json`). After that, the token refreshes silently in the background. This is the standard pattern for any Google API integration.

---

## Tools — What Each Does

### `get_todays_meetings()`
Queries Google Calendar primary calendar for all events between 00:00 and 23:59 today. Returns title, start time, end time, and optional location.

### `get_tasks_due_today()`
Fetches all open Trello boards, then filters cards where `due <= today` and the card isn't marked complete. Returns cards due today **and** any overdue cards (so nothing falls through).

### `get_upcoming_birthdays(days_ahead=7)`
Finds the "Birthdays" calendar in your Google Calendar list (auto-populated from Google Contacts) and returns birthdays in the next 7 days. Returns an empty list gracefully if no Birthdays calendar exists.

---

## Extending the Digest

The agent is designed to be extended. Adding a new data source is two steps:

**Step 1** — add a tool function in `tools.py`:
```python
def get_urgent_emails() -> dict:
    """Fetch unread emails marked important from Gmail."""
    ...
    return {"emails": [...]}
```

**Step 2** — add it to `agent.py`:
```python
tools=[get_todays_meetings, get_tasks_due_today, get_upcoming_birthdays, get_urgent_emails]
```

Update the instruction to include it in the JSON output, add the field to `DigestBrief` in `models.py`, and update `print_digest()` in `run_digest.py`. That's it.

---

## Running

```bash
cd /Users/.../agents-playground/google-adk
source .venv/bin/activate
pip install -r requirements.txt

# First run — browser opens for Google auth
python3 run_digest.py

# Subsequent runs — no browser, uses saved token
python3 run_digest.py
```
