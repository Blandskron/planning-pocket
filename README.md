# Planning Pocket

Planning Pocket is a fast, modern, and privacy-first web application for Agile teams to estimate tasks using Planning Poker. It is designed to be extremely simple: no SPA frameworks, just standard HTML/CSS powered by Django and WebSockets.

## Features
- **Facilitator & Guest Architecture:** Only the creator needs an account. Guests join simply by entering a name via a shared URL.
- **Real-time WebSockets:** Powered by Django Channels. Live updates for participants joining, voting status, issue changing, and result revealing.
- **Vote Privacy Guarantee:** A strict backend rule ensures that vote payloads are never transmitted to clients until the facilitator explicitly triggers a reveal.
- **Issue Tracking:** Built-in queue for issues to be estimated, allowing the facilitator to focus the discussion, save the final estimate, and instantly switch to the next topic.
- **A Table, Not a Form:** Seats are placed on an elliptical ring computed from the number of
  participants, the felt itself reports the round, the deck is a fanned hand, and the reveal has a
  countdown and a staggered flip. Everyone sees their own seat at the front.
- **Characters:** Each person gets a face, a pet and a colour, chosen on the way in or from the room
  and derived from a stable hash otherwise. The pet mirrors its owner's state with body language.
- **A Playful Layer:** Anyone can toss a soft object at anyone else, and the facilitator can open a
  recess where people leave their seats and walk around while the table waits for the last vote.
  Both are cosmetic, rate-limited by the server, and switchable off for the room or for one screen.
  See `docs/DECISIONS.md` ADR-005 for the rules that keep it from becoming pressure.
- **Modern UI:** Responsive, clean, and professional design built entirely with native CSS. No React,
  no Vue—just plain HTML and CSS variables. Every animation touches only `transform` and `opacity`,
  and sound is five tones synthesised in the browser, off by default.

## Tech Stack
- **Backend:** Python 3.13, Django 4.2+
- **Real-time:** Django Channels, Daphne, Redis (Production), Vanilla JS (Frontend)
- **Database:** PostgreSQL (Production) / SQLite (Local)
- **Testing:** Pytest, pytest-django

## Getting Started (Local Development)

### 1. Setup Environment
```powershell
python --version # Python 3.11+ is required
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

### 2. Database Setup
```powershell
python manage.py migrate
```

### 3. Run Server
```powershell
python manage.py runserver
```
Navigate to `http://localhost:8000`.

### 4. Running Tests
```powershell
python -m pytest . -p no:cacheprovider
python -m ruff check .
python manage.py check
```

## Production Deployment

This project includes a `Dockerfile` and `docker-compose.yml` pre-configured for a production-like environment with PostgreSQL and Redis.

```bash
# Set your environment variables in a .env file or export them
docker-compose up --build -d
```

For production, set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
`DJANGO_CSRF_TRUSTED_ORIGINS`, and (when not using the included Compose database)
`DATABASE_URL`. Start from `.env.example`; do not commit a real `.env` file.

## Security & Architecture Philosophy
- **Server as the Source of Truth:** All business validations and privacy locks are implemented on the Django consumer. The browser is a dumb terminal.
- **No SPA Frameworks:** Following a minimalist approach to reduce complexity and asset size.

---
*Built with an Agents-first and Human-friendly approach.*
