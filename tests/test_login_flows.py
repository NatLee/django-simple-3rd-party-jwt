"""Login flows with Google and Microsoft mocked out.

No real OAuth credentials or network access are needed: the calls that would go to
Google (token verification) and Microsoft (MSAL and Graph) are replaced with mocks.
These tests describe the current behaviour of the views.
"""
import logging
from unittest import mock

from django.contrib.auth.models import User
from google.auth import exceptions as google_exceptions
from django.test import TestCase
from django.test.utils import override_script_prefix
from django.urls import reverse
from django.utils.html import escapejs
from rest_framework_simplejwt.tokens import AccessToken

from django_simple_third_party_jwt import settings as jwt_settings
from django_simple_third_party_jwt.models import SocialAccount

from .helpers import package_settings

GOOGLE_VERIFY = "django_simple_third_party_jwt.serilizers.google_login.id_token.verify_oauth2_token"
MICROSOFT_AUTH = "django_simple_third_party_jwt.views.microsoft.auth"


def google_idinfo(email="alice@gmail.com", sub="google-sub-1"):
    """What Google's verify_oauth2_token returns for a valid credential."""
    return {
        "iss": "https://accounts.google.com",
        "aud": jwt_settings.SOCIAL_GOOGLE_CLIENT_ID,
        "sub": sub,
        "email": email,
        "email_verified": True,
        "given_name": "Alice",
        "family_name": "Liddell",
    }


class UrlLayoutTests(TestCase):
    def test_routes_follow_jwt_3rd_prefix(self):
        """Included at the root with JWT_3RD_PREFIX = "api", the routes are the ones the
        README's frontend snippets and Microsoft redirect URI use."""
        self.assertEqual(reverse("google-token"), "/api/auth/google/token")
        self.assertEqual(reverse("google-token-session"), "/api/auth/google/token/session")
        self.assertEqual(reverse("microsoft-signin"), "/api/auth/microsoft/signin")
        self.assertEqual(reverse("microsoft-signout"), "/api/auth/microsoft/signout")
        self.assertEqual(reverse("microsoft-callback"), "/api/auth/microsoft/callback")


class GoogleLoginTests(TestCase):
    url = "/api/auth/google/token"

    def post(self, url=None):
        return self.client.post(url or self.url, {"credential": "google-id-token"})

    @mock.patch(GOOGLE_VERIFY, return_value=google_idinfo())
    def test_new_user_gets_jwt_pair(self, verify):
        response = self.post()

        self.assertEqual(response.status_code, 200)
        verify.assert_called_once()
        self.assertEqual(verify.call_args.args[0], "google-id-token")
        user = User.objects.get(email="alice@gmail.com")
        self.assertEqual(user.username, "alice")
        self.assertEqual((user.first_name, user.last_name), ("Alice", "Liddell"))
        self.assertTrue(
            SocialAccount.objects.filter(user=user, provider="google", unique_id="google-sub-1").exists()
        )
        body = response.json()
        # Both the package's own keys and Simple JWT's keys are returned,
        # and every access token belongs to the new user.
        self.assertEqual(set(body), {"access", "refresh", "access_token", "refresh_token"})
        # The Simple JWT names are aliases: one pair of tokens, two sets of keys.
        self.assertEqual(body["refresh"], body["refresh_token"])
        self.assertEqual(body["access"], body["access_token"])
        self.assertEqual(str(AccessToken(body["access"])["user_id"]), str(user.id))

    @mock.patch(GOOGLE_VERIFY, return_value=google_idinfo())
    def test_returning_user_is_matched_by_google_id(self, verify):
        user = User.objects.create_user(username="someone-else", email="old@gmail.com")
        SocialAccount.objects.create(user=user, provider="google", unique_id="google-sub-1")

        response = self.post()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(str(AccessToken(response.json()["access"])["user_id"]), str(user.id))

    @mock.patch(GOOGLE_VERIFY, return_value=google_idinfo())
    def test_taken_username_gets_a_random_one(self, verify):
        User.objects.create_user(username="alice", email="alice@example.com")

        response = self.post()

        self.assertEqual(response.status_code, 200)
        new_user = SocialAccount.objects.get(provider="google", unique_id="google-sub-1").user
        self.assertNotEqual(new_user.username, "alice")
        self.assertEqual(len(new_user.username), 36)  # uuid4

    @mock.patch(GOOGLE_VERIFY, return_value=google_idinfo(email="bob@example.com"))
    def test_email_domain_outside_allow_list_is_refused(self, verify):
        response = self.post()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"status": "error", "detail": "This email is invalid."})
        self.assertFalse(User.objects.exists())

    @mock.patch(GOOGLE_VERIFY)
    def test_missing_credential_is_a_bad_request(self, verify):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, 400)
        verify.assert_not_called()

    @mock.patch(GOOGLE_VERIFY, return_value=google_idinfo())
    def test_token_only_endpoint_does_not_start_a_session(self, verify):
        self.post()

        self.assertNotIn("_auth_user_id", self.client.session)

    @mock.patch(GOOGLE_VERIFY, return_value=google_idinfo())
    def test_session_endpoint_also_logs_in(self, verify):
        response = self.post("/api/auth/google/token/session")

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="alice@gmail.com")
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        self.assertIn("access", response.json())

    @mock.patch(GOOGLE_VERIFY, return_value=google_idinfo())
    def test_json_body_works_too(self, verify):
        """The README's fetch() snippet posts JSON, without a CSRF token."""
        client = self.client_class(enforce_csrf_checks=True)
        response = client.post(self.url, {"credential": "google-id-token"}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(verify.call_args.args[0], "google-id-token")

    @mock.patch(GOOGLE_VERIFY, return_value=google_idinfo())
    def test_credential_is_checked_against_the_configured_client_id(self, verify):
        self.post()

        self.assertEqual(verify.call_args.args[2], jwt_settings.SOCIAL_GOOGLE_CLIENT_ID)


class GoogleLoginErrorTests(TestCase):
    """A credential that does not check out is the client's problem: 401 with the reason
    (the user's decision, 2026-11-04; it used to be a 500 "Something went wrong :(")."""
    url = "/api/auth/google/token"
    serializer_logger = "django_simple_third_party_jwt.serilizers.google_login"

    def post(self):
        return self.client.post(self.url, {"credential": "google-id-token"})

    def assertRefused(self, response, detail):
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"status": "error", "detail": detail})
        self.assertFalse(User.objects.exists())

    def test_credential_google_rejects(self):
        for error in [ValueError("Token expired, 1 < 2"), google_exceptions.GoogleAuthError("Wrong issuer.")]:
            with self.subTest(error=error), mock.patch(GOOGLE_VERIFY, side_effect=error), \
                    self.assertLogs(self.serializer_logger, "WARNING") as logs:
                response = self.post()
            self.assertRefused(response, f"Google did not accept the credential: {error}")
            # A client error, not a crash: logged as a warning, without a traceback.
            self.assertEqual({r.levelno for r in logs.records}, {logging.WARNING})
            self.assertFalse(any(r.exc_info for r in logs.records))

    def test_wrong_issuer(self):
        with mock.patch(GOOGLE_VERIFY, return_value=dict(google_idinfo(), iss="https://evil.example")):
            response = self.post()

        self.assertRefused(response, "Google did not accept the credential: it was not issued by Google.")

    def test_token_for_another_client_id(self):
        with mock.patch(GOOGLE_VERIFY, return_value=dict(google_idinfo(), aud="someone-else.apps.googleusercontent.com")):
            response = self.post()

        self.assertRefused(response, "Google did not accept the credential: it was issued for another client ID.")

    def test_unverified_email_is_refused(self):
        """email_verified is checked by default (the user's decision, 2026-11-04)."""
        for flag in [False, None]:
            claims = dict(google_idinfo(), email_verified=flag)
            if flag is None:
                del claims["email_verified"]
            with self.subTest(email_verified=flag), mock.patch(GOOGLE_VERIFY, return_value=claims):
                response = self.post()
            self.assertRefused(response, "Google has not verified this e-mail address.")

    def test_google_out_of_reach_is_still_a_server_error(self):
        """Not the client's fault when Google's keys cannot be fetched, so no 401."""
        with mock.patch(GOOGLE_VERIFY, side_effect=google_exceptions.TransportError("no network")):
            with self.assertRaises(google_exceptions.TransportError):
                self.post()


class MicrosoftLoginTests(TestCase):
    def test_sign_in_redirects_to_microsoft(self):
        flow = {"auth_uri": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?x=1", "state": "s"}
        with mock.patch(f"{MICROSOFT_AUTH}.get_sign_in_flow", return_value=flow) as get_flow:
            response = self.client.get("/api/auth/microsoft/signin")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], flow["auth_uri"])
        get_flow.assert_called_once_with(redirect_uri="http://testserver/api/auth/microsoft/callback")
        self.assertEqual(self.client.session["auth_flow"], flow)

    def test_sign_in_sends_microsoft_back_to_wherever_the_callback_is_served(self):
        """The redirect URI is the callback route's own URL. It used to be the site root plus a
        path rebuilt from JWT_3RD_PREFIX, which left out a SCRIPT_NAME (a site served under a
        sub-path) and so sent Microsoft to a URL outside the site."""
        flow = {"auth_uri": "https://login.microsoftonline.com/x", "state": "s"}
        # What Django's WSGI handler does for a site whose SCRIPT_NAME is /sub.
        with override_script_prefix("/sub/"):
            with mock.patch(f"{MICROSOFT_AUTH}.get_sign_in_flow", return_value=flow) as get_flow:
                self.client.get("/api/auth/microsoft/signin")

        get_flow.assert_called_once_with(redirect_uri="http://testserver/sub/api/auth/microsoft/callback")

    def callback(self, email="carol@gmail.com"):
        token_result = {"access_token": "graph-token", "id_token_claims": {"preferred_username": email}}
        with mock.patch(f"{MICROSOFT_AUTH}.get_token_from_code", return_value=token_result), \
                mock.patch(f"{MICROSOFT_AUTH}.get_user", return_value={"displayName": "Carol"}):
            return self.client.get("/api/auth/microsoft/callback", {"code": "c", "state": "s"})

    def test_callback_creates_user_logs_in_and_hands_over_tokens(self):
        response = self.callback()

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "microsoft/index.html")
        user = User.objects.get(email="carol@gmail.com")
        self.assertEqual(user.username, "carol")
        self.assertTrue(
            SocialAccount.objects.filter(user=user, provider="microsoft", unique_id="carol@gmail.com").exists()
        )
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        self.assertEqual(str(AccessToken(response.context["access_token"])["user_id"]), str(user.id))
        self.assertEqual(response.context["redirect_url"], jwt_settings.LOGIN_REDIRECT_URL)
        self.assertEqual(response.context["access_token_key"], "access_token")
        self.assertEqual(response.context["refresh_token_key"], "refresh_token")

    def test_callback_page_stores_the_tokens_and_redirects(self):
        response = self.callback()

        html = response.content.decode()
        self.assertIn(escapejs(response.context["access_token"]), html)
        self.assertIn(escapejs(response.context["refresh_token"]), html)
        self.assertIn("localStorage.setItem(access_token_key, access_token)", html)
        self.assertIn("window.location.replace('%s')" % escapejs(jwt_settings.LOGIN_REDIRECT_URL), html)
        self.assertIn("Welcome!", html)

    def test_callback_uses_the_configured_storage_keys(self):
        with package_settings(
            MICROSOFT_JWT_REDIRECT_ACCESS_TOKEN_KEY="jwt_access",
            MICROSOFT_JWT_REDIRECT_REFRESH_TOKEN_KEY="jwt_refresh",
        ):
            response = self.callback()

        self.assertEqual(response.context["access_token_key"], "jwt_access")
        self.assertEqual(response.context["refresh_token_key"], "jwt_refresh")

    def test_callback_reuses_existing_microsoft_account(self):
        self.callback()
        self.client.logout()
        self.callback()

        self.assertEqual(User.objects.filter(email="carol@gmail.com").count(), 1)

    def test_callback_with_a_taken_username_gets_a_random_one(self):
        User.objects.create_user(username="carol", email="carol@example.com")

        self.callback()

        new_user = SocialAccount.objects.get(provider="microsoft", unique_id="carol@gmail.com").user
        self.assertNotEqual(new_user.username, "carol")
        self.assertEqual(len(new_user.username), 36)  # uuid4
        self.assertEqual(new_user.email, "carol@gmail.com")

    def test_callback_refuses_email_domain_outside_allow_list(self):
        response = self.callback(email="dave@example.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["access_token"], "")
        self.assertEqual(response.context["description"], "Sorry, this account is not allowed to sign in here.")
        self.assertFalse(User.objects.exists())

    def test_callback_refuses_a_username_that_is_not_an_email(self):
        """Some Microsoft accounts sign in with a name that has no "@"; that used to be a 500."""
        response = self.callback(email="no-at-sign")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["access_token"], "")
        self.assertEqual(response.context["description"], "Sorry, this account is not allowed to sign in here.")
        self.assertFalse(User.objects.exists())

    def test_callback_shows_error_when_microsoft_rejects_the_code(self):
        with mock.patch(f"{MICROSOFT_AUTH}.get_token_from_code", return_value={"error": "invalid_grant"}):
            response = self.client.get("/api/auth/microsoft/callback", {"code": "bad"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["access_token"], "")
        self.assertEqual(response.context["description"], "Something went wrong while signing in with Microsoft. Please try again.")
        self.assertFalse(User.objects.exists())

    def test_callback_logs_why_microsoft_refused_the_code(self):
        """A wrong client secret used to show up in the log as just access_token."""
        refusal = {
            "error": "invalid_client",
            "error_description": "AADSTS7000215: Invalid client secret provided.",
        }
        with mock.patch(f"{MICROSOFT_AUTH}.get_token_from_code", return_value=refusal),                 mock.patch(f"{MICROSOFT_AUTH}.get_user") as get_user,                 self.assertLogs(MICROSOFT_AUTH, "ERROR") as logs:
            response = self.client.get("/api/auth/microsoft/callback", {"code": "c"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["access_token"], "")
        self.assertEqual(response.context["description"], "Something went wrong while signing in with Microsoft. Please try again.")
        self.assertIn("invalid_client", logs.output[0])
        self.assertIn("AADSTS7000215: Invalid client secret provided.", logs.output[0])
        get_user.assert_not_called()
        self.assertFalse(User.objects.exists())

    def test_callback_page_shows_the_message_without_javascript_too(self):
        page = self.callback(email="mallory@example.com").content.decode()

        self.assertIn('<div id="description">Sorry, this account is not allowed to sign in here.</div>', page)
        self.assertNotIn("Hello World!", page)

    def test_callback_page_counts_down_in_proper_english(self):
        """It used to say "Redirecting in 1 seconds..."."""
        page = self.callback().content.decode()

        self.assertIn('(timeleft === 1 ? " second" : " seconds")', page)
        self.assertNotIn('timeleft + " seconds..."', page)

    def test_sign_out_clears_microsoft_token_cache(self):
        session = self.client.session
        session["token_cache"] = "{}"
        session.save()

        response = self.client.get("/api/auth/microsoft/signout")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/api/auth/microsoft/signin")
        self.assertNotIn("token_cache", self.client.session)
