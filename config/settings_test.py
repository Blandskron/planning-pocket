"""Settings isolated from local and production environment variables for test runs."""

import os

os.environ.setdefault("DJANGO_DEBUG", "True")

from .settings import *  # noqa: F403

DEBUG = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
MIDDLEWARE = [
    middleware
    for middleware in MIDDLEWARE  # noqa: F405
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]

STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Django's default hasher is PBKDF2 with a deliberately expensive iteration count. That is
# the right call in production and the wrong one here: every test that logs someone in paid
# ~9 seconds for it, and the suite took eight and a half minutes to say "96 passed". MD5 is
# not a security decision — nothing in the test database outlives the run — it is what makes
# the suite fast enough to be part of CI at all.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
