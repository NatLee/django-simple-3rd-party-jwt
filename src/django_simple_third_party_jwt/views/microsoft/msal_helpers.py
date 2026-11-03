"""Thin wrappers around MSAL (Microsoft Authentication Library) for the sign-in flow."""
from __future__ import annotations

from typing import Any, Dict, Optional

import msal
from django.http import HttpRequest

from django_simple_third_party_jwt import settings as jwt_settings

settings = {
    "app_id": jwt_settings.SOCIAL_MICROSOFT_CLIENT_ID,
    "app_secret": jwt_settings.SOCIAL_MICROSOFT_CLIENT_SECRET,
    # "common" accepts both work/school accounts and personal Microsoft accounts.
    "authority": "https://login.microsoftonline.com/common",
    "scopes": ["user.read"],
}

# Where Microsoft sends the browser back to, relative to the site root.
# It has to match a redirect URI registered for the app in Azure.
callback_url = jwt_settings.JWT_3RD_PREFIX + "/auth/microsoft/callback"


def load_cache(request: HttpRequest) -> msal.SerializableTokenCache:
    """MSAL's token cache, restored from the Django session."""
    cache = msal.SerializableTokenCache()
    if request.session.get("token_cache"):
        cache.deserialize(request.session["token_cache"])
    return cache


def save_cache(request: HttpRequest, cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        request.session["token_cache"] = cache.serialize()


def get_msal_app(cache: Optional[msal.SerializableTokenCache] = None) -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        settings["app_id"],
        authority=settings["authority"],
        client_credential=settings["app_secret"],
        token_cache=cache,
    )


def get_sign_in_flow(root_url: str) -> Dict[str, Any]:
    """Start the auth-code flow; `root_url` is the site root, ending in "/"."""
    return get_msal_app().initiate_auth_code_flow(
        settings["scopes"],
        redirect_uri=root_url + callback_url,
    )


def get_token_from_code(request: HttpRequest) -> Dict[str, Any]:
    """Exchange the code Microsoft sent to the callback for tokens.

    Uses (and forgets) the flow that sign_in kept in the session.
    """
    cache = load_cache(request)
    auth_app = get_msal_app(cache)
    flow = request.session.pop("auth_flow", {})
    result = auth_app.acquire_token_by_auth_code_flow(flow, request.GET)
    save_cache(request, cache)
    return result


def get_token(request: HttpRequest) -> Optional[str]:
    """A Microsoft access token for the account in the session's cache, if any."""
    cache = load_cache(request)
    auth_app = get_msal_app(cache)
    accounts = auth_app.get_accounts()
    if accounts:
        result = auth_app.acquire_token_silent(settings["scopes"], account=accounts[0])
        save_cache(request, cache)
        return result["access_token"]
    return None


def remove_user_and_token(request: HttpRequest) -> None:
    request.session.pop("token_cache", None)
    request.session.pop("user", None)
