import importlib
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import clear_url_caches, reverse

import django_simple_third_party_jwt.urls as package_urls
from django_simple_third_party_jwt.views.microsoft import msal_helpers

from . import urls as test_urlconf
from .helpers import package_settings

GOOGLE_VERIFY = "django_simple_third_party_jwt.serilizers.google_login.id_token.verify_oauth2_token"
ROUTE_ENDS = [
    "auth/google/token",
    "auth/google/token/session",
    "auth/microsoft/signin",
    "auth/microsoft/signout",
    "auth/microsoft/callback",
]


def routes():
    return [str(p.pattern) for p in package_urls.urlpatterns]


class ReloadUrlsMixin:
    def tearDown(self):
        importlib.reload(package_urls)  # back to the test settings' routes
        importlib.reload(test_urlconf)  # its include() keeps the route list it saw at import
        clear_url_caches()
        super().tearDown()


class MissingPrefixTests(ReloadUrlsMixin, SimpleTestCase):
    def test_missing_jwt_3rd_prefix_means_api(self):
        """JWT_3RD_PREFIX is optional, default "api" (the user's decision, 2026-11-04).
        It used to stop start-up with an ImproperlyConfigured."""
        with override_settings():
            del settings.JWT_3RD_PREFIX
            importlib.reload(package_urls)

        self.assertEqual(routes(), ["api/" + end for end in ROUTE_ENDS])

    def test_prefix_from_settings_is_used(self):
        with override_settings(JWT_3RD_PREFIX="v2"):
            importlib.reload(package_urls)

        self.assertEqual(routes(), ["v2/" + end for end in ROUTE_ENDS])


class PrefixSlashTests(ReloadUrlsMixin, TestCase):
    """A "/" at either end of JWT_3RD_PREFIX is ignored (the user's decision, 2026-11-03).

    Up to 0.3.2, "/api" and "api/" kept the slash and the routes ended up at /%2Fapi/auth/...
    or /api//auth/..., so the URLs the README and the frontend use answered 404.
    """

    def test_slashes_at_either_end_are_ignored(self):
        for prefix in ["/api", "api/", "/api/"]:
            with self.subTest(prefix), override_settings(JWT_3RD_PREFIX=prefix):
                importlib.reload(package_urls)
                self.assertEqual(routes(), ["api/" + end for end in ROUTE_ENDS])

    def test_an_empty_prefix_serves_the_routes_at_auth(self):
        for prefix in ["", "/"]:
            with self.subTest(prefix), override_settings(JWT_3RD_PREFIX=prefix):
                importlib.reload(package_urls)
                self.assertEqual(routes(), ROUTE_ENDS)

    def test_a_trailing_slash_prefix_answers_at_the_plain_url(self):
        info = {"iss": "https://accounts.google.com", "aud": settings.SOCIAL_GOOGLE_CLIENT_ID,
                "sub": "s", "email": "alice@gmail.com", "email_verified": True}
        with override_settings(JWT_3RD_PREFIX="api/"):
            importlib.reload(package_urls)
            importlib.reload(test_urlconf)
            clear_url_caches()
            self.assertEqual(reverse("google-token"), "/api/auth/google/token")
            with mock.patch(GOOGLE_VERIFY, return_value=info):
                response = self.client.post("/api/auth/google/token", {"credential": "x"})
        self.assertEqual(response.status_code, 200)


class MicrosoftRedirectUriPrefixTests(SimpleTestCase):
    def tearDown(self):
        importlib.reload(msal_helpers)  # back to the test settings' callback URL

    def test_the_redirect_uri_uses_the_same_cleaned_prefix(self):
        cases = [
            ("api", "api/auth/microsoft/callback"),
            ("/api/", "api/auth/microsoft/callback"),
            ("api/", "api/auth/microsoft/callback"),
            ("", "auth/microsoft/callback"),
        ]
        for prefix, expected in cases:
            with self.subTest(prefix), package_settings(JWT_3RD_PREFIX=prefix) as conf:
                self.assertEqual(conf.JWT_3RD_PREFIX, prefix.strip("/"))
                importlib.reload(msal_helpers)
                self.assertEqual(msal_helpers.callback_url, expected)
