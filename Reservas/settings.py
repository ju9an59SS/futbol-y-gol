from pathlib import Path
import os

import dj_database_url


# =========================================================
# BASE DEL PROYECTO
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =========================================================
# SEGURIDAD
# =========================================================

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-desarrollo-local-futbol-y-gol",
)

DEBUG = (
    os.environ.get(
        "DEBUG",
        "True",
    ).lower()
    == "true"
)


ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    ".vercel.app",
]


CSRF_TRUSTED_ORIGINS = [
    "https://*.vercel.app",
]


SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)


# =========================================================
# APLICACIONES
# =========================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "webapp",
]


# =========================================================
# MIDDLEWARE
# =========================================================

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


# =========================================================
# URLS
# =========================================================

ROOT_URLCONF = "Reservas.urls"


# =========================================================
# TEMPLATES
# =========================================================

TEMPLATES = [
    {
        "BACKEND":
            "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates"
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                (
                    "django.template.context_processors.debug"
                ),
                (
                    "django.template.context_processors.request"
                ),
                (
                    "django.contrib.auth.context_processors.auth"
                ),
                (
                    "django.contrib.messages.context_processors.messages"
                ),
            ],
        },
    },
]


# =========================================================
# WSGI
# =========================================================

WSGI_APPLICATION = (
    "Reservas.wsgi.application"
)


# =========================================================
# BASE DE DATOS
# =========================================================

DATABASE_URL = os.environ.get(
    "DATABASE_URL"
)


if DATABASE_URL:

    # PRODUCCIÓN - NEON POSTGRES

    DATABASES = {
        "default":
            dj_database_url.config(
                default=DATABASE_URL,
                conn_max_age=600,
                ssl_require=True,
            )
    }

else:

    # LOCAL - XAMPP MYSQL / MARIADB

    DATABASES = {
        "default": {

            "ENGINE":
                "django.db.backends.mysql",

            "NAME":
                "reservas",

            "USER":
                "root",

            "PASSWORD":
                "",

            "HOST":
                "localhost",

            "PORT":
                "3306",

            "OPTIONS": {
                "charset": "utf8mb4",
            },
        }
    }


# =========================================================
# VALIDACIÓN DE CONTRASEÑAS
# =========================================================

AUTH_PASSWORD_VALIDATORS = [

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# =========================================================
# IDIOMA Y ZONA HORARIA
# =========================================================

LANGUAGE_CODE = "es"

TIME_ZONE = "America/Bogota"

USE_I18N = True

USE_TZ = True


# =========================================================
# ARCHIVOS ESTÁTICOS
# =========================================================

STATIC_URL = "/static/"

STATIC_ROOT = (
    BASE_DIR / "staticfiles"
)


STATICFILES_STORAGE = (
    "whitenoise.storage."
    "CompressedManifestStaticFilesStorage"
)


# =========================================================
# ARCHIVOS MEDIA
# =========================================================

# IMPORTANTE:
# Los comprobantes de pago NO se guardarán aquí en Vercel.
# Se almacenarán en Vercel Blob.
#
# Estas rutas se dejan solo para desarrollo local
# o por compatibilidad con archivos antiguos.

MEDIA_URL = "/media/"

MEDIA_ROOT = (
    BASE_DIR / "media"
)


# =========================================================
# LÍMITES DE CARGA
# =========================================================

DATA_UPLOAD_MAX_MEMORY_SIZE = (
    5 * 1024 * 1024
)

FILE_UPLOAD_MAX_MEMORY_SIZE = (
    4 * 1024 * 1024
)


# =========================================================
# CORREO - GMAIL SMTP
# =========================================================

EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
)

EMAIL_HOST = "smtp.gmail.com"

EMAIL_PORT = 587

EMAIL_USE_TLS = True

EMAIL_USE_SSL = False


EMAIL_HOST_USER = os.environ.get(
    "EMAIL_HOST_USER",
    "",
)


EMAIL_HOST_PASSWORD = os.environ.get(
    "EMAIL_HOST_PASSWORD",
    "",
)


DEFAULT_FROM_EMAIL = (
    EMAIL_HOST_USER
)


EMAIL_TIMEOUT = 20


# =========================================================
# SESIONES
# =========================================================

SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_SAMESITE = "Lax"


# =========================================================
# CSRF
# =========================================================

CSRF_COOKIE_SAMESITE = "Lax"


# =========================================================
# SEGURIDAD EN PRODUCCIÓN
# =========================================================

if not DEBUG:

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True


# =========================================================
# CONFIGURACIÓN DE ID AUTOMÁTICO
# =========================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)