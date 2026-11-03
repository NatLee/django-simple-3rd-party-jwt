"""Start-up checks (manage.py check, runserver) for JWT_3RD_PREFIX."""
from django.conf import settings
from django.core import checks
from django.test import SimpleTestCase, override_settings

from django_simple_third_party_jwt.checks import check_jwt_3rd_prefix


class PrefixCheckTests(SimpleTestCase):
    def test_a_plain_or_empty_prefix_is_fine(self):
        for prefix in ["api", "v1/api", ""]:
            with self.subTest(prefix), override_settings(JWT_3RD_PREFIX=prefix):
                self.assertEqual(check_jwt_3rd_prefix(None), [])

    def test_a_slash_at_either_end_gets_an_upgrade_hint(self):
        """The slash is ignored now, which moved the routes of projects that had one:
        say where they are and what to re-register in Azure."""
        for prefix in ["/api", "api/", "/api/"]:
            with self.subTest(prefix), override_settings(JWT_3RD_PREFIX=prefix):
                [warning] = check_jwt_3rd_prefix(None)
                self.assertIsInstance(warning, checks.Warning)
                self.assertEqual(warning.id, "django_simple_third_party_jwt.W001")
                self.assertIn(repr(prefix), warning.msg)
                self.assertIn("/api/auth/", warning.msg)
                self.assertIn("0.3.2", warning.msg)
                self.assertIn("JWT_3RD_PREFIX = 'api'", warning.hint)
                self.assertIn("<your site>/api/auth/microsoft/callback", warning.hint)

    def test_a_lone_slash_means_no_prefix(self):
        with override_settings(JWT_3RD_PREFIX="/"):
            [warning] = check_jwt_3rd_prefix(None)
        self.assertIn("/auth/", warning.msg)
        self.assertIn("JWT_3RD_PREFIX = ''", warning.hint)
        self.assertIn("<your site>/auth/microsoft/callback", warning.hint)

    def test_a_missing_prefix_is_left_to_the_urls_error(self):
        """urls.py already stops start-up with an ImproperlyConfigured that names the setting."""
        with override_settings():
            del settings.JWT_3RD_PREFIX
            self.assertEqual(check_jwt_3rd_prefix(None), [])

    def test_the_check_is_registered_with_django(self):
        with override_settings(JWT_3RD_PREFIX="api/"):
            ids = [message.id for message in checks.run_checks(tags=[checks.Tags.urls])]
        self.assertIn("django_simple_third_party_jwt.W001", ids)
