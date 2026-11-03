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
from rest_framework_simplejwt.tokens import AccessToken

from django_simple_third_party_jwt import settings as jwt_settings
from django_simple_third_party_jwt.models import SocialAccount
from tests.custom_user.models import EmailUser

GOOGLE_VERIFY = "django_simple_third_party_jwt.serilizers.google_login.id_token.verify_oauth2_token"
MICROSOFT_CODE = "django_simple_third_party_jwt.views.microsoft.auth.get_token_from_code"
ACCOUNTS_LOGGER = "django_simple_third_party_jwt.utils.accounts"
CONFLICT = (
    "Another account already uses this e-mail address. Sign in to that account the usual way, "
    "or ask the site's administrator to link your Google or Microsoft sign-in to it."
)


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

    def test_an_address_already_taken_by_another_user_is_refused_with_what_to_do(self):
        """With the address as the username there is no other name to fall back to, and the
        package does not merge accounts by address: it refuses, says why and what to do
        (the user's decision, 2026-11-04), and logs the details for the administrator."""
        existing = EmailUser.objects.create_user("alice@gmail.com")

        with self.assertLogs(ACCOUNTS_LOGGER, "WARNING") as logs:
            response = self.google_login(sub="google-sub-2")

        self.assertEqual(response.status_code, 401)
        # Nothing about the other account reaches the client...
        self.assertEqual(response.json(), {"status": "error", "detail": CONFLICT})
        self.assertFalse(SocialAccount.objects.exists())
        # ...while the log says which sign-in collided with which user.
        [line] = logs.output
        for part in ("google", "google-sub-2", "alice@gmail.com", f"pk={existing.pk}"):
            self.assertIn(part, line)

    def test_the_microsoft_page_gives_the_same_reason(self):
        EmailUser.objects.create_user("carol@gmail.com")
        claims = {"oid": "oid-carol", "tid": "9188040d-6c67-4c5b-b112-36a304b66dad",
                  "preferred_username": "carol@gmail.com", "email": "carol@gmail.com"}
        with mock.patch(MICROSOFT_CODE, return_value={"access_token": "t", "id_token_claims": claims}), \
                self.assertLogs(ACCOUNTS_LOGGER, "WARNING"):
            response = self.client.get("/api/auth/microsoft/callback", {"code": "c"})

        self.assertEqual(response.context["description"], CONFLICT)
        self.assertEqual(response.context["access_token"], "")

    def test_an_administrator_can_link_the_sign_in_to_the_existing_account(self):
        """The README's steps: add a SocialAccount in the admin with the provider and ID from the log."""
        existing = EmailUser.objects.create_user("alice@gmail.com")
        with self.assertLogs(ACCOUNTS_LOGGER, "WARNING"):
            self.assertEqual(self.google_login(sub="google-sub-2").status_code, 401)

        self.client.force_login(EmailUser.objects.create_superuser("admin@example.com", "pw"))
        added = self.client.post("/admin/django_simple_third_party_jwt/socialaccount/add/",
                                 {"user": existing.pk, "provider": "google", "unique_id": "google-sub-2"})
        self.assertEqual(added.status_code, 302, added.content.decode()[:500])
        self.client.logout()

        response = self.google_login(sub="google-sub-2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(AccessToken(response.json()["access"])["user_id"]), str(existing.pk))

    def test_the_id_cannot_be_edited_once_saved(self):
        self.google_login()
        self.client.force_login(EmailUser.objects.create_superuser("admin@example.com", "pw"))
        account = SocialAccount.objects.get()

        page = self.client.get(f"/admin/django_simple_third_party_jwt/socialaccount/{account.pk}/change/")

        self.assertContains(page, "google-sub-1")
        self.assertNotContains(page, 'name="unique_id"')

    def test_admin_list_can_search_users(self):
        self.google_login()
        admin = EmailUser.objects.create_superuser("admin@example.com", "pw")
        self.client.force_login(admin)

        response = self.client.get("/admin/django_simple_third_party_jwt/socialaccount/", {"q": "alice"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alice@gmail.com")

    def test_microsoft_login_creates_a_user_of_the_custom_model(self):
        claims = {"oid": "oid-carol", "tid": "9188040d-6c67-4c5b-b112-36a304b66dad",
                  "preferred_username": "carol@gmail.com", "email": "carol@gmail.com"}
        result = {"access_token": "t", "id_token_claims": claims}
        with mock.patch("django_simple_third_party_jwt.views.microsoft.auth.get_token_from_code", return_value=result):
            response = self.client.get("/api/auth/microsoft/callback", {"code": "c"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(EmailUser.objects.get().get_username(), "carol@gmail.com")
        self.assertEqual(SocialAccount.objects.get().provider, "microsoft")
