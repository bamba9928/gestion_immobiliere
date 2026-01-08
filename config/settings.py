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

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
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

ALLOWED_HOSTS = get_env_variable(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1",
).split(",")

CSRF_TRUSTED_ORIGINS = get_env_variable(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:8000",
).split(",")

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
]

THIRD_PARTY_APPS = [
    "widget_tweaks",
    "rest_framework",
    "tailwind",
    "theme",
    "whitenoise",
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
if DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": get_env_variable("DB_NAME"),
            "USER": get_env_variable("DB_USER"),
            "PASSWORD": get_env_variable("DB_PASSWORD"),
            "HOST": get_env_variable("DB_HOST", "localhost"),
            "PORT": get_env_variable("DB_PORT", "5432"),
        }
    }
# ===================== SÉCURITÉ HTTPS (AJOUTÉ) ========================
if not DEBUG:
    # Rediriger tout le trafic HTTP vers HTTPS
    SECURE_SSL_REDIRECT = True
    # Éviter que le cookie de session soit volé via HTTP
    SESSION_COOKIE_SECURE = True
    # Éviter que le cookie CSRF soit volé via HTTP
    CSRF_COOKIE_SECURE = True
    # Protection stricte contre le sniffing
    SECURE_CONTENT_TYPE_NOSNIFF = True
    # Protection XSS
    SECURE_BROWSER_XSS_FILTER = True
    # HTTP Strict Transport Security (HSTS)
    SECURE_HSTS_SECONDS = 31536000  # 1 an
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Indique à Django qu'il est derrière un proxy (Nginx/Traefik) qui gère le SSL
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
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
DEFAULT_FROM_EMAIL = "MADA IMMO <no-reply@mada-immo.com>"
CONTACT_EMAIL = get_env_variable("CONTACT_EMAIL", DEFAULT_FROM_EMAIL)

if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = get_env_variable("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(get_env_variable("EMAIL_PORT", 587))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = get_env_variable("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = get_env_variable("EMAIL_HOST_PASSWORD")

# ===================== CELERY ========================
CELERY_BROKER_URL = get_env_variable("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = get_env_variable("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

CELERY_BEAT_SCHEDULE = {
    "generer-loyers-mensuel": {
        "task": "apps.core.tasks.generer_loyers_task",
        "schedule": crontab(hour=6, minute=0, day_of_month=1),
    },
}

TAILWIND_APP_NAME = "theme"
