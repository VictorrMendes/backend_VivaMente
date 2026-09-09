from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "django_filters",
    "apps.accounts",
    "apps.professionals",
    "apps.clients",
    "apps.leads",
    "apps.appointments",
    "apps.services",
    "apps.public_profiles",
    "apps.notifications",
    "apps.audit",
    "apps.clinical_records",
    "apps.packages",
    "apps.payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.RequestIDMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

TEST_RUNNER = "config.testing.SafeTestRunner"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.FirebaseAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "config.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "config.schema.EnvelopeSchema",
    "EXCEPTION_HANDLER": "config.exceptions.rfc9457_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "public-appointment-requests": "10/min",
        "public-available-slots": "20/min",
        "public-professional-profile": "30/min",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "VivaMente Back API",
    "DESCRIPTION": "API de negocio da VivaMente (terapeutas, clientes, leads, agendamentos).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "config.schema.add_health_paths",
    ],
    "ENUM_NAME_OVERRIDES": {
        "UserRoleEnum": "apps.accounts.models.User.ROLE_CHOICES",
        "IdentityRoleEnum": ["ADMIN", "THERAPIST"],
        "AppointmentStatusEnum": "apps.appointments.models.Appointment.STATUS_CHOICES",
        "LeadStatusEnum": "apps.leads.models.Lead.STATUS_CHOICES",
        "ServiceModalityEnum": "apps.services.models.Service.MODALITY_CHOICES",
        "AppointmentModalityEnum": "apps.appointments.models.Appointment.MODALITY_CHOICES",
        "PackageStatusEnum": "apps.packages.models.Package.STATUS_CHOICES",
        "PaymentStatusEnum": "apps.payments.models.Payment.STATUS_CHOICES",
    },
}

CORS_ALLOWED_ORIGINS = env.list("ALLOWED_ORIGINS", default=[])

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "config.logging.JsonFormatter"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        # evita duplicar log de request/erro (django.request ja tenta
        # logar sozinho); api.errors/api.access sao os nossos, no root.
        "django.request": {"handlers": [], "propagate": False},
    },
}

FIREBASE_CREDENTIALS_PATH = env("FIREBASE_CREDENTIALS_PATH", default=None)

# Chave publica (PEM) usada para validar o JWT de servico (RS256) da API
# interna de sync de identidade (apps.accounts.internal_auth). O Oauth
# assina com a chave privada correspondente - o Back nunca ve a privada,
# entao mesmo comprometido nao consegue forjar um token do Oauth.
INTERNAL_SERVICE_JWT_PUBLIC_KEY = env("INTERNAL_SERVICE_JWT_PUBLIC_KEY").replace(
    "\\n", "\n"
)
