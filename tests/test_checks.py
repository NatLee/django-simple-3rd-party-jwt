"""Start-up checks (manage.py check, runserver) for settings that silently break the routes."""
from django.conf import settings
from django.core import checks
from django.test import SimpleTestCase, override_settings

from django_simple_third_party_jwt.checks import check_jwt_3rd_prefix


class PrefixCheckTests(SimpleTestCase):
    def test_a_plain_prefix_is_fine(self):
        for prefix in ["api", "v1/api"]:
            with self.subTest(prefix), override_settings(JWT_3RD_PREFIX=prefix):
                self.assertEqual(check_jwt_3rd_prefix(None), [])

    def test_a_slash_at_either_end_gets_a_warning_with_the_value_to_use(self):
        """With "/api" or "api/" the routes end up at /%2Fapi/auth/... or /api//auth/...
        and the Microsoft redirect URI gets a "//", with nothing said at start-up."""
        for prefix in ["/api", "api/", "/api/"]:
            with self.subTest(prefix), override_settings(JWT_3RD_PREFIX=prefix):
                [warning] = check_jwt_3rd_prefix(None)
                self.assertIsInstance(warning, checks.Warning)
                self.assertEqual(warning.id, "django_simple_third_party_jwt.W001")
                self.assertIn(repr(prefix), warning.msg)
                self.assertIn("JWT_3RD_PREFIX = 'api'", warning.hint)

    def test_an_empty_prefix_gets_a_warning(self):
        for prefix in ["", "/"]:
            with self.subTest(prefix), override_settings(JWT_3RD_PREFIX=prefix):
                [warning] = check_jwt_3rd_prefix(None)
                self.assertEqual(warning.id, "django_simple_third_party_jwt.W002")
                self.assertIn("JWT_3RD_PREFIX = 'api'", warning.hint)

    def test_a_missing_prefix_is_left_to_the_urls_error(self):
        """urls.py already stops start-up with an ImproperlyConfigured that names the setting."""
        with override_settings():
            del settings.JWT_3RD_PREFIX
            self.assertEqual(check_jwt_3rd_prefix(None), [])

    def test_the_check_is_registered_with_django(self):
        with override_settings(JWT_3RD_PREFIX="api/"):
            ids = [message.id for message in checks.run_checks(tags=[checks.Tags.urls])]
        self.assertIn("django_simple_third_party_jwt.W001", ids)
