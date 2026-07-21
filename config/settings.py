"""Réglages Django — application locale mono-utilisateur, SQLite."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from .env import load_env_file

BASE_DIR = Path(__file__).resolve().parent.parent

# Secrets locaux (identifiants Garmin, …) — jamais commité, voir la page /setup/
load_env_file(BASE_DIR / ".env.local")

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

# Clé de dev tolérée uniquement avec DEBUG : hors debug, une clé prévisible
# affaiblirait la signature des cookies/sessions.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY est requis quand DJANGO_DEBUG=0"
        )
    SECRET_KEY = "dev-only-insecure-key-application-locale"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "sleep",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DATABASE_NAME", BASE_DIR / "db.sqlite3"),
    }
}

LANGUAGE_CODE = "fr"
TIME_ZONE = os.environ.get("GARMIN_SLEEP_TZ", "Europe/Zurich")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Identifiants Garmin Connect pour `manage.py sync_garmin` (jamais en dur dans le
# code). Tout reste dans le dossier du projet : pas de lecture hors de BASE_DIR
# (l'app doit pouvoir tourner en conteneur).
GARMIN_EMAIL = os.environ.get("GARMIN_EMAIL")
GARMIN_PASSWORD = os.environ.get("GARMIN_PASSWORD")
GARMIN_TOKENSTORE = os.environ.get("GARMIN_TOKENSTORE", str(BASE_DIR / ".garmin_tokens"))
