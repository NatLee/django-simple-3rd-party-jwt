"""The package with a custom user model (AUTH_USER_MODEL = "custom_user.EmailUser").

Not collected by the normal test run: AUTH_USER_MODEL cannot change inside one process, so
tests/test_custom_user_model.py runs this file in its own pytest with
DJANGO_SETTINGS_MODULE=tests.custom_user.settings. That run applies the real migration files.
"""
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from django_simple_third_party_jwt import settings as jwt_settings
from django_simple_third_party_jwt.models import SocialAccount
from tests.custom_user.models import EmailUser

GOOGLE_VERIFY = "django_simple_third_party_jwt.serilizers.google_login.id_token.verify_oauth2_token"


def google_idinfo(email="alice@gmail.com", sub="google-sub-1"):
    return {
        "iss": "https://accounts.google.com",
        "aud": jwt_settings.SOCIAL_GOOGLE_CLIENT_ID,
        "sub": sub,
        "email": email,
        "email_verified": True,
        "given_name": "Alice",
        "family_name": "Liddell",
    }


class CustomUserModelTests(TestCase):
    def google_login(self, **claims):
        with mock.patch(GOOGLE_VERIFY, return_value=google_idinfo(**claims)):
            return self.client.post("/api/auth/google/token", {"credential": "google-id-token"})

    def test_the_custom_model_is_in_use(self):
        self.assertIs(get_user_model(), EmailUser)

    def test_shipped_migrations_apply_and_match_the_models(self):
        """This run created the tables from the package's migration files."""
        out = StringIO()
        try:
            call_command("makemigrations", "django_simple_third_party_jwt", check=True, dry_run=True,
                         stdout=out, stderr=StringIO())
        except SystemExit:
            self.fail("Model changes without a migration:\n" + out.getvalue())

    def test_google_login_creates_a_user_of_the_custom_model(self):
        response = self.google_login()

        self.assertEqual(response.status_code, 200)
        user = EmailUser.objects.get()
        # The e-mail address is this model's username; it has no first_name/last_name to set.
        self.assertEqual(user.get_username(), "alice@gmail.com")
        self.assertFalse(user.has_usable_password())
        account = SocialAccount.objects.get()
        self.assertEqual((account.user, account.provider, account.unique_id), (user, "google", "google-sub-1"))
        self.assertEqual(str(account), "alice@gmail.com - google")

    def test_returning_google_user_gets_the_same_account(self):
        self.google_login()
        response = self.google_login()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(EmailUser.objects.count(), 1)

    def test_an_address_already_taken_by_another_user_is_refused(self):
        """With the address as the username there is no other name to fall back to."""
        EmailUser.objects.create_user("alice@gmail.com")

        response = self.google_login(sub="google-sub-2")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Another account already uses this e-mail address.")
        self.assertFalse(SocialAccount.objects.exists())

    def test_admin_list_can_search_users(self):
        self.google_login()
        admin = EmailUser.objects.create_superuser("admin@example.com", "pw")
        self.client.force_login(admin)

        response = self.client.get("/admin/django_simple_third_party_jwt/socialaccount/", {"q": "alice"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alice@gmail.com")
