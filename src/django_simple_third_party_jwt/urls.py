from django.urls import path

from django_simple_third_party_jwt.settings import auth_route, route_prefix
from django_simple_third_party_jwt.views import google, microsoft

# Every route lives under /<JWT_3RD_PREFIX>/auth/ (by default /api/auth/google/token and so on).
# A "/" at either end of the prefix is ignored; an empty prefix gives /auth/....
prefix = route_prefix()

urlpatterns = [
    path(auth_route(prefix, "google/token"), google.GoogleLogin.as_view(), name="google-token"),
    path(auth_route(prefix, "google/token/session"), google.GoogleLoginSession.as_view(), name="google-token-session"),
    path(auth_route(prefix, "microsoft/signin"), microsoft.sign_in, name="microsoft-signin"),
    path(auth_route(prefix, "microsoft/signout"), microsoft.sign_out, name="microsoft-signout"),
    path(auth_route(prefix, "microsoft/callback"), microsoft.callback, name="microsoft-callback"),
]
