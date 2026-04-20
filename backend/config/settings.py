from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


SECRET_KEY = env("DJANGO_SECRET_KEY", "unsafe-dev-secret-key")
DEBUG = env("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [host.strip() for host in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
for internal_host in ("api",):
    if internal_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(internal_host)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "apps.common",
    "apps.access",
    "apps.strategies",
    "apps.backtesting",
    "apps.trading",
    "apps.operations",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {}

if env("DJANGO_DB_ENGINE", "sqlite") == "sqlite":
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
else:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DJANGO_DB_NAME", "stock_trading"),
        "USER": env("DJANGO_DB_USER", "stock_trading"),
        "PASSWORD": env("DJANGO_DB_PASSWORD", "stock_trading"),
        "HOST": env("DJANGO_DB_HOST", "localhost"),
        "PORT": env("DJANGO_DB_PORT", "5432"),
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "access.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.access.authentication.DatabaseTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in env("FRONTEND_URL", "http://localhost:5173").split(",") if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

CELERY_BROKER_URL = env("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER", "0") == "1"
CELERY_BEAT_SCHEDULER = "celery.beat:PersistentScheduler"
CELERY_BEAT_SCHEDULE = {
    "sync-live-deployments": {
        "task": "apps.trading.tasks.sync_live_deployments",
        "schedule": 300.0,
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
FRONTEND_INVITE_URL = env("FRONTEND_INVITE_URL", "http://localhost:5173/accept-invitation")
