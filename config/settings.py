# =============================================================================
#  MADA IMMO – Plateforme de gestion immobilière       --2025--
#
#  Auteur    : Mouhamadou Bamba DIENG     +221 77 249 05 30
#  Contact   : bigrip2016@gmail.com
#
#  Description :
#      Fichier de configuration principal Django.
#      Toutes les valeurs sensibles (SECRET_KEY, DEBUG, ALLOWED_HOSTS, etc.)
#      sont chargées depuis le fichier .env à la racine du projet.
# =============================================================================

import os
from pathlib import Path
from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def get_env_variable(var_name, default=None):
    """Récupère une variable d'environnement ou lève une erreur si critique."""
    try:
        return os.environ[var_name]
    except KeyError:
        if default is not None:
            return default
        raise ImproperlyConfigured(f"La variable d'environnement {var_name} est manquante.")

# ===================== CORE SETTINGS =====================
SECRET_KEY = get_env_variable("SECRET_KEY")

# IMPORTANT : S'assurer que ceci renvoie bien un booléen
DEBUG = get_env_variable("DEBUG", "False").lower() == "true"

def env_list(name: str, default: str = "") -> list[str]:
    return [x.strip() for x in get_env_variable(name, default).split(",") if x.strip()]

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:8000")


AUTH_USER_MODEL = "accounts.CustomUser"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ===================== APPS ========================
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    'django.contrib.sitemaps'
]

THIRD_PARTY_APPS = [
    "widget_tweaks",
    "rest_framework",
    "tailwind",
    "theme",
]

LOCAL_APPS = [
    "accounts",
    "apps.core",
    "apps.api",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ===================== DATABASE ========================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
# ====================================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Dakar"
USE_I18N = True
USE_TZ = True

# ===================== STATIC FILES ========================
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# ===================== EMAIL ========================


# ===================== CELERY ========================
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_BEAT_SCHEDULE = {
    "generer-loyers-mensuel": {
        "task": "apps.core.tasks.generer_loyers_task",
        "schedule": crontab(hour=6, minute=0, day_of_month=1),
    },
    "relances-quotidiennes": {
        "task": "apps.core.tasks.envoyer_relances_paiement",
        "schedule": crontab(hour=7, minute=0),
    },
}
TAILWIND_APP_NAME = "theme"