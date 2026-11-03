
# At least 32 bytes, so PyJWT does not warn about a short HMAC key.
SECRET_KEY = 'test-secret-key-used-only-by-the-test-suite'
DEBUG = True
USE_TZ = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:"
    }
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "rest_framework",
    "django_simple_third_party_jwt",
]

MIGRATION_MODULES = {app: None for app in INSTALLED_APPS}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
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

ROOT_URLCONF = 'tests.urls'
SITE_ID = 1

ALLOWED_HOSTS = ['*']

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

SECURE_REFERRER_POLICY = "no-referrer-when-downgrade"
SECURE_CROSS_ORIGIN_OPENER_POLICY = None
SOCIAL_GOOGLE_CLIENT_ID = "376808175534-d6mefo6b1kqih3grjjose2euree2g3cs.apps.googleusercontent.com"
LOGIN_REDIRECT_URL = "/"
VALID_REGISTER_DOMAINS = ["gmail.com"]

# Routes are served at /<JWT_3RD_PREFIX>/auth/..., as described in the README.
JWT_3RD_PREFIX = "api"

# Placeholder Microsoft app credentials: the tests mock every call to Microsoft,
# so no real client ID or secret is needed.
SOCIAL_MICROSOFT_CLIENT_ID = "test-microsoft-client-id"
SOCIAL_MICROSOFT_CLIENT_SECRET = "test-placeholder-not-a-secret"
