"""The package reads its settings once, when django_simple_third_party_jwt.settings is
imported. These tests reload that module under different Django settings to check the
defaults and the warnings about the shared demo credentials."""
import logging

from django.test import SimpleTestCase

from .helpers import package_settings

LOGGER = "django_simple_third_party_jwt.settings"
CREDENTIAL_SETTINGS = (
    "SOCIAL_GOOGLE_CLIENT_ID",
    "SOCIAL_MICROSOFT_CLIENT_ID",
    "SOCIAL_MICROSOFT_CLIENT_SECRET",
)


class DefaultsTests(SimpleTestCase):
    def test_defaults_when_nothing_is_set(self):
        optional = (
            "LOGIN_REDIRECT_URL",
            "JWT_3RD_PREFIX",
            "VALID_REGISTER_DOMAINS",
            "MICROSOFT_JWT_REDIRECT_ACCESS_TOKEN_KEY",
            "MICROSOFT_JWT_REDIRECT_REFRESH_TOKEN_KEY",
        )
        with self.assertLogs(LOGGER, "WARNING"):
            with package_settings(remove=optional + CREDENTIAL_SETTINGS) as conf:
                self.assertEqual(conf.LOGIN_REDIRECT_URL, "/")
                self.assertEqual(conf.JWT_3RD_PREFIX, "")
                self.assertEqual(
                    conf.VALID_REGISTER_DOMAINS,
                    ["gmail.com", "outlook.com", "hotmail.com", "live.com"],
                )
                self.assertEqual(conf.MICROSOFT_JWT_REDIRECT_ACCESS_TOKEN_KEY, "access_token")
                self.assertEqual(conf.MICROSOFT_JWT_REDIRECT_REFRESH_TOKEN_KEY, "refresh_token")
                # Shared demo credentials are filled in (values deliberately not compared).
                self.assertTrue(conf.SOCIAL_GOOGLE_CLIENT_ID.endswith(".apps.googleusercontent.com"))
                self.assertTrue(conf.SOCIAL_MICROSOFT_CLIENT_ID)
                self.assertTrue(conf.SOCIAL_MICROSOFT_CLIENT_SECRET)

    def test_project_settings_win_over_defaults(self):
        with package_settings(
            VALID_REGISTER_DOMAINS=["example.com"],
            MICROSOFT_JWT_REDIRECT_ACCESS_TOKEN_KEY="jwt_access",
            MICROSOFT_JWT_REDIRECT_REFRESH_TOKEN_KEY="jwt_refresh",
            LOGIN_REDIRECT_URL="/after-login/",
        ) as conf:
            self.assertEqual(conf.VALID_REGISTER_DOMAINS, ["example.com"])
            self.assertEqual(conf.MICROSOFT_JWT_REDIRECT_ACCESS_TOKEN_KEY, "jwt_access")
            self.assertEqual(conf.MICROSOFT_JWT_REDIRECT_REFRESH_TOKEN_KEY, "jwt_refresh")
            self.assertEqual(conf.LOGIN_REDIRECT_URL, "/after-login/")


class DemoCredentialWarningTests(SimpleTestCase):
    def test_each_missing_credential_logs_a_warning(self):
        for name, words in (
            ("SOCIAL_GOOGLE_CLIENT_ID", "default Google client ID"),
            ("SOCIAL_MICROSOFT_CLIENT_ID", "default Microsoft client ID"),
            ("SOCIAL_MICROSOFT_CLIENT_SECRET", "default Microsoft client secret"),
        ):
            with self.subTest(name), self.assertLogs(LOGGER, "WARNING") as logs:
                with package_settings(remove=[name]):
                    pass
            self.assertTrue(any(words in line for line in logs.output), logs.output)

    def test_own_credentials_do_not_warn(self):
        # tests/settings.py has placeholder Microsoft credentials; give Google one too.
        # (assertNoLogs would do, but it needs Python 3.10+.)
        records = []
        handler = logging.Handler(logging.WARNING)
        handler.emit = records.append
        logger = logging.getLogger(LOGGER)
        logger.addHandler(handler)
        try:
            with package_settings(SOCIAL_GOOGLE_CLIENT_ID="own-id.apps.googleusercontent.com"):
                warnings = [r.getMessage() for r in records]
        finally:
            logger.removeHandler(handler)
        self.assertEqual(warnings, [])
