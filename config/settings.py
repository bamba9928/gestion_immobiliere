from pathlib import Path
import os
from celery.schedules import crontab

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# ===================== CONFIGURATION WINDOWS (WEASYPRINT) =====================
if os.name == 'nt':  # Windows uniquement
    GTK_FOLDER = r'C:\Program Files\GTK3-Runtime Win64\bin'
    if os.path.exists(GTK_FOLDER):
        os.environ['PATH'] = f"{GTK_FOLDER};{os.environ['PATH']}"
        try:
            os.add_dll_directory(GTK_FOLDER)  # Python 3.8+
        except AttributeError:
            pass
# ===========================================================================

# ===================== CORE SETTINGS =====================
SECRET_KEY = 'django-insecure-y)wq&$_qu-m-6-^fc@j)ge+xq=^5ri53uokr2ynu^&zi8lgjq+'

# TODO: Mettre à False en production !
DEBUG = True

# TODO: Configurer pour la production
ALLOWED_HOSTS = []

AUTH_USER_MODEL = "accounts.CustomUser"
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# ========================================================

# ===================== APPS ========================
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'widget_tweaks',
    'rest_framework',
    'tailwind',
    'theme',
]

LOCAL_APPS = [
    'accounts',
    'apps.core',
    'apps.api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
# ==================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ===================== TEMPLATES ========================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
# =====================================================

WSGI_APPLICATION = 'config.wsgi.application'

# ===================== DATABASE ========================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
# =====================================================

# ===================== PASSWORD VALIDATION ========================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
# ===============================================================

# ===================== INTERNATIONALIZATION ========================
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True
# ================================================================

# ===================== STATIC & MEDIA FILES ========================
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# ================================================================

# ===================== REDIRECTIONS ========================
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
# ========================================================

# ===================== EMAIL ========================
DEFAULT_FROM_EMAIL = "MADA IMMO <no-reply@mada-immo.com>"

if DEBUG:
    # Développement : les emails vont dans la console
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    # Production : configuration SMTP (exemple Gmail)
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
# =================================================
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

CELERY_BEAT_SCHEDULE = {
    "generer-loyers-mensuel": {
        "task": "apps.core.tasks.generer_loyers_task",
        "schedule": crontab(hour=6, minute=0, day_of_month=1),
    },
}

# ===================== TAILWIND ========================
TAILWIND_APP_NAME = "theme"
# ======================================================