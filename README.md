# Planning Pocket

Planning Pocket is a fast, modern, and privacy-first web application for Agile teams to estimate tasks using Planning Poker. It is designed to be extremely simple: no SPA frameworks, just standard HTML/CSS powered by Django and WebSockets.

## Features
- **Facilitator & Guest Architecture:** Only the creator needs an account. Guests join simply by entering a name via a shared URL.
- **Real-time WebSockets:** Powered by Django Channels. Live updates for participants joining, voting status, issue changing, and result revealing.
- **Vote Privacy Guarantee:** A strict backend rule ensures that vote payloads are never transmitted to clients until the facilitator explicitly triggers a reveal.
- **Issue Tracking:** Built-in queue for issues to be estimated, allowing the facilitator to focus the discussion, save the final estimate, and instantly switch to the next topic.
- **Modern UI:** Responsive, clean, and professional design built entirely with native CSS. No React, no Vue—just plain HTML and CSS variables.

## Tech Stack
- **Backend:** Python 3.13, Django 4.2+
- **Real-time:** Django Channels, Daphne, Redis (Production), Vanilla JS (Frontend)
- **Database:** PostgreSQL (Production) / SQLite (Local)
- **Testing:** Pytest, pytest-django

## Getting Started (Local Development)

### 1. Setup Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
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
python -m pytest .
```

## Production Deployment

This project includes a `Dockerfile` and `docker-compose.yml` pre-configured for a production-like environment with PostgreSQL and Redis.

```bash
# Set your environment variables in a .env file or export them
docker-compose up --build -d
```

## Security & Architecture Philosophy
- **Server as the Source of Truth:** All business validations and privacy locks are implemented on the Django consumer. The browser is a dumb terminal.
- **No SPA Frameworks:** Following a minimalist approach to reduce complexity and asset size.

---
*Built with an Agents-first and Human-friendly approach.*
