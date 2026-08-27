"""Test-run wiring that has to happen before any fixture is built."""

import asyncio
import os
import sys


def pytest_configure(config):
    """Give the browser tests an event loop that can spawn Chromium.

    Importing daphne — it is in INSTALLED_APPS, so Django imports it during setup —
    installs WindowsSelectorEventLoopPolicy process-wide, and the selector loop has
    no subprocess transport on Windows. Playwright cannot start a browser under it.

    Only flipped for the browser run, which is the one that sets
    DJANGO_ALLOW_ASYNC_UNSAFE (see docs/TESTING.md). The default run keeps daphne's
    policy and Django's async-safety check, because that check is what would catch a
    raw ORM call sneaking into an async consumer method.
    """
    if sys.platform == "win32" and os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
