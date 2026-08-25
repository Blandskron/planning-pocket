import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings import database_from_url


def test_database_url_configures_postgresql():
    config = database_from_url("postgres://user:password@db.example:5433/planning_pocket")

    assert config == {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "planning_pocket",
        "USER": "user",
        "PASSWORD": "password",
        "HOST": "db.example",
        "PORT": "5433",
    }


def test_database_url_rejects_unknown_schemes():
    with pytest.raises(ImproperlyConfigured, match="postgres"):
        database_from_url("mysql://user:password@db.example/planning_pocket")
