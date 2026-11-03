"""The thin wrappers around MSAL (Microsoft's auth library) and Microsoft Graph.
MSAL and the HTTP calls are mocked; nothing here talks to Microsoft."""
from unittest import mock

import msal
from django.conf import settings
from django.test import RequestFactory, SimpleTestCase

from django_simple_third_party_jwt.views.microsoft import msal_helpers
from django_simple_third_party_jwt.views.microsoft import utils as graph

APP = "django_simple_third_party_jwt.views.microsoft.msal_helpers.msal.ConfidentialClientApplication"


def request_with_session(session=None, query=None):
    request = RequestFactory().get("/api/auth/microsoft/callback", query or {})
    request.session = {} if session is None else session
    return request


class MsalAppTests(SimpleTestCase):
    @mock.patch(APP)
    def test_app_uses_configured_credentials_and_common_authority(self, app):
        msal_helpers.get_msal_app()

        app.assert_called_once_with(
            settings.SOCIAL_MICROSOFT_CLIENT_ID,
            authority="https://login.microsoftonline.com/common",
            client_credential=settings.SOCIAL_MICROSOFT_CLIENT_SECRET,
            token_cache=None,
        )

    @mock.patch(APP)
    def test_sign_in_flow_asks_for_user_read_and_comes_back_to_the_callback(self, app):
        app.return_value.initiate_auth_code_flow.return_value = {"auth_uri": "https://login"}

        flow = msal_helpers.get_sign_in_flow(redirect_uri="http://testserver/sub/api/auth/microsoft/callback")

        self.assertEqual(flow, {"auth_uri": "https://login"})
        app.return_value.initiate_auth_code_flow.assert_called_once_with(
            ["user.read"], redirect_uri="http://testserver/sub/api/auth/microsoft/callback"
        )

    @mock.patch(APP)
    def test_sign_in_flow_still_takes_the_site_root_like_0_3(self, app):
        """Compatibility: code written against 0.3.x passes the site root (see msal_helpers)."""
        msal_helpers.get_sign_in_flow("http://testserver/")

        app.return_value.initiate_auth_code_flow.assert_called_once_with(
            ["user.read"], redirect_uri="http://testserver/api/auth/microsoft/callback"
        )

    @mock.patch(APP)
    def test_code_is_exchanged_with_the_flow_kept_in_the_session(self, app):
        app.return_value.acquire_token_by_auth_code_flow.return_value = {"access_token": "t"}
        request = request_with_session({"auth_flow": {"state": "s"}}, {"code": "c", "state": "s"})

        result = msal_helpers.get_token_from_code(request)

        self.assertEqual(result, {"access_token": "t"})
        flow, query = app.return_value.acquire_token_by_auth_code_flow.call_args.args
        self.assertEqual(flow, {"state": "s"})
        self.assertEqual(query.dict(), {"code": "c", "state": "s"})
        self.assertNotIn("auth_flow", request.session)  # one flow, one use

    @mock.patch(APP)
    def test_code_exchange_without_a_flow_passes_an_empty_one(self, app):
        msal_helpers.get_token_from_code(request_with_session())

        flow, _ = app.return_value.acquire_token_by_auth_code_flow.call_args.args
        self.assertEqual(flow, {})

    @mock.patch(APP)
    def test_get_token_without_a_signed_in_account(self, app):
        app.return_value.get_accounts.return_value = []

        self.assertIsNone(msal_helpers.get_token(request_with_session()))

    @mock.patch(APP)
    def test_get_token_refreshes_silently_for_the_first_account(self, app):
        app.return_value.get_accounts.return_value = ["account-1", "account-2"]
        app.return_value.acquire_token_silent.return_value = {"access_token": "fresh"}

        self.assertEqual(msal_helpers.get_token(request_with_session()), "fresh")
        app.return_value.acquire_token_silent.assert_called_once_with(["user.read"], account="account-1")


class TokenCacheTests(SimpleTestCase):
    def test_cache_round_trips_through_the_session(self):
        request = request_with_session()
        cache = msal_helpers.load_cache(request)
        self.assertIsInstance(cache, msal.SerializableTokenCache)

        msal_helpers.save_cache(request, cache)  # unchanged cache: nothing stored
        self.assertNotIn("token_cache", request.session)

        cache.has_state_changed = True
        msal_helpers.save_cache(request, cache)
        self.assertEqual(request.session["token_cache"], cache.serialize())

        restored = msal_helpers.load_cache(request)
        self.assertEqual(restored.serialize(), cache.serialize())

    def test_sign_out_forgets_the_cache_and_the_user(self):
        request = request_with_session({"token_cache": "{}", "user": {"name": "x"}, "other": 1})

        msal_helpers.remove_user_and_token(request)

        self.assertEqual(request.session, {"other": 1})
        msal_helpers.remove_user_and_token(request)  # nothing left to remove: no error


class GraphTests(SimpleTestCase):
    @mock.patch("django_simple_third_party_jwt.views.microsoft.utils.requests.get")
    def test_get_user_calls_graph_me_with_the_bearer_token(self, get):
        get.return_value.json.return_value = {"displayName": "Carol"}

        self.assertEqual(graph.get_user("graph-token"), {"displayName": "Carol"})
        get.assert_called_once_with(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": "Bearer graph-token"},
            params={"$select": "displayName"},
        )
