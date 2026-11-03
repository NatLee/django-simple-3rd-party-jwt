from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import path

from django_simple_third_party_jwt.settings import auth_route, clean_prefix
from django_simple_third_party_jwt.views import google, microsoft

# Every route lives under /<JWT_3RD_PREFIX>/auth/ (for example /api/auth/google/token).
# A "/" at either end of the prefix is ignored; an empty prefix gives /auth/....
try:
    prefix = clean_prefix(settings.JWT_3RD_PREFIX)
except AttributeError:
    raise ImproperlyConfigured(
        "django-simple-third-party-jwt needs JWT_3RD_PREFIX in your settings, "
        "for example JWT_3RD_PREFIX = 'api' to serve the login routes at /api/auth/..."
    ) from None

urlpatterns = [
    path(auth_route(prefix, "google/token"), google.GoogleLogin.as_view(), name="google-token"),
    path(auth_route(prefix, "google/token/session"), google.GoogleLoginSession.as_view(), name="google-token-session"),
    path(auth_route(prefix, "microsoft/signin"), microsoft.sign_in, name="microsoft-signin"),
    path(auth_route(prefix, "microsoft/signout"), microsoft.sign_out, name="microsoft-signout"),
    path(auth_route(prefix, "microsoft/callback"), microsoft.callback, name="microsoft-callback"),
]
