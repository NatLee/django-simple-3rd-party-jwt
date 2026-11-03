"""Microsoft login: sign in at Microsoft, come back to the callback, get JWTs.

The callback answers with a small HTML page (templates/microsoft/index.html) that puts
the JWTs into the browser's localStorage and then redirects to LOGIN_REDIRECT_URL.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.contrib.auth import login
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from django_simple_third_party_jwt import settings as jwt_settings
from django_simple_third_party_jwt.exception import InvalidEmailError, LoginRefused
from django_simple_third_party_jwt.utils.accounts import get_or_create_social_user, split_email
from django_simple_third_party_jwt.utils.get_tokens_for_user import get_tokens_for_user
from django_simple_third_party_jwt.views.microsoft.msal_helpers import (
    get_sign_in_flow,
    get_token_from_code,
    remove_user_and_token,
)

logger = logging.getLogger(__name__)

TEMPLATE = "microsoft/index.html"

# Microsoft's tenant ID for personal Microsoft accounts (outlook.com, hotmail.com, live.com, ...).
# Microsoft verifies these accounts' e-mail addresses itself.
PERSONAL_ACCOUNTS_TENANT_ID = "9188040d-6c67-4c5b-b112-36a304b66dad"

NOT_ALLOWED = "Sorry, this account is not allowed to sign in here."
NO_VERIFIED_EMAIL = "Sorry, Microsoft has not confirmed an e-mail address for this account."
FAILED = "Something went wrong while signing in with Microsoft. Please try again."


def sign_in(request: HttpRequest) -> HttpResponseRedirect:
    """Start the sign-in flow and send the browser to Microsoft."""
    flow = get_sign_in_flow(redirect_uri=request.build_absolute_uri(reverse("microsoft-callback")))
    try:
        request.session["auth_flow"] = flow
    except Exception:
        logger.exception("[AUTH][MICROSOFT] Could not keep the sign-in flow in the session")
    return HttpResponseRedirect(flow["auth_uri"])


def sign_out(request: HttpRequest) -> HttpResponseRedirect:
    remove_user_and_token(request)
    return HttpResponseRedirect(reverse("microsoft-signin"))


def account_id(claims: Dict[str, Any]) -> str:
    """The account's immutable ID: tenant ID and object ID, the pair Microsoft recommends.

    preferred_username and email can be changed by whoever runs the account, so they never
    decide who the user is.
    """
    return f"{claims['tid']}/{claims['oid']}"


def verified_email(claims: Dict[str, Any]) -> Optional[str]:
    """The e-mail address in the ID token, if Microsoft vouches for it; otherwise None.

    Personal accounts: Microsoft verifies the address. Work and school accounts: only when the
    token says the domain's owner is verified (xms_edov), which, like the email claim itself,
    is an optional claim to switch on in the app registration's token configuration.
    """
    email = claims.get("email")
    if email and (claims.get("tid") == PERSONAL_ACCOUNTS_TENANT_ID or claims.get("xms_edov") is True):
        return email
    return None


def callback(request: HttpRequest) -> HttpResponse:
    """Where Microsoft sends the browser back to after sign-in."""
    try:
        result = get_token_from_code(request)
        if "error" in result:
            # Microsoft said no (for example AADSTS7000215, a wrong client secret): log its reason.
            logger.error(
                "[AUTH][MICROSOFT] Microsoft refused the sign-in: %s: %s",
                result["error"], result.get("error_description", ""),
            )
            return _render_page(request, email="", description=FAILED)
        claims = result["id_token_claims"]
        unique_id = account_id(claims)
    except Exception as e:
        logger.error("[AUTH][MICROSOFT] %s", e)
        return _render_page(request, email="", description=FAILED)

    email = verified_email(claims) or ""
    try:
        user = get_or_create_user(unique_id, email, claims)
    except LoginRefused as refusal:
        return _render_page(request, email=email, description=refusal.detail)
    login(request, user)
    tokens = get_tokens_for_user(user)
    return _render_page(
        request,
        email=email,
        description="Welcome!",
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


def get_or_create_user(unique_id: str, email: str, claims: Dict[str, Any]) -> AbstractBaseUser:
    """The user linked to this Microsoft account, created on first login.

    Raises LoginRefused when Microsoft does not vouch for an address, or its domain is not in
    VALID_REGISTER_DOMAINS. Up to 0.4.0 accounts were keyed by preferred_username; such a
    record is found through the verified address and keyed by `unique_id` from then on.
    """
    if not email:
        logger.warning(
            "[AUTH][MICROSOFT] No verified e-mail address for `%s` (%s). Work and school accounts "
            "need the optional claims email and xms_edov in the app's token configuration.",
            claims.get("preferred_username", ""), unique_id,
        )
        raise LoginRefused(NO_VERIFIED_EMAIL)
    try:
        username, domain = split_email(email)
    except ValueError:
        raise InvalidEmailError(NOT_ALLOWED) from None
    if domain not in jwt_settings.VALID_REGISTER_DOMAINS:
        logger.warning("[AUTH][MICROSOFT] `%s` attempts to register!!", email)
        raise InvalidEmailError(NOT_ALLOWED)
    return get_or_create_social_user(
        "microsoft", unique_id, email=email, username=username, previous_ids=[email],
    )


def _render_page(
    request: HttpRequest,
    *,
    email: str,
    description: str,
    access_token: str = "",
    refresh_token: str = "",
) -> HttpResponse:
    return render(
        request,
        TEMPLATE,
        {
            "email": email,
            "refresh_token": refresh_token,
            "access_token": access_token,
            "description": description,
            "redirect_url": jwt_settings.LOGIN_REDIRECT_URL,
            "access_token_key": jwt_settings.MICROSOFT_JWT_REDIRECT_ACCESS_TOKEN_KEY,
            "refresh_token_key": jwt_settings.MICROSOFT_JWT_REDIRECT_REFRESH_TOKEN_KEY,
        },
    )
