import importlib

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from django.urls import clear_url_caches

import django_simple_third_party_jwt.urls as package_urls


class MissingPrefixTests(SimpleTestCase):
    def tearDown(self):
        importlib.reload(package_urls)  # back to the test settings' routes
        clear_url_caches()

    def test_missing_jwt_3rd_prefix_says_what_to_set(self):
        """Still a start-up error (the routes cannot be built without it), but a
        Django ImproperlyConfigured that names the setting instead of an
        AttributeError from django.conf.global_settings."""
        with override_settings():
            del settings.JWT_3RD_PREFIX
            with self.assertRaisesMessage(ImproperlyConfigured, "JWT_3RD_PREFIX = 'api'"):
                importlib.reload(package_urls)

    def test_prefix_from_settings_is_used(self):
        with override_settings(JWT_3RD_PREFIX="v2"):
            importlib.reload(package_urls)

        routes = [str(p.pattern) for p in package_urls.urlpatterns]
        self.assertEqual(
            routes,
            [
                "v2/auth/google/token",
                "v2/auth/google/token/session",
                "v2/auth/microsoft/signin",
                "v2/auth/microsoft/signout",
                "v2/auth/microsoft/callback",
            ],
        )
