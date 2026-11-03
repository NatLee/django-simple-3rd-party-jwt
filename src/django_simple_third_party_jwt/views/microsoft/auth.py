"""Microsoft login: sign in at Microsoft, come back to the callback, get JWTs.

The callback answers with a small HTML page (templates/microsoft/index.html) that puts
the JWTs into the browser's localStorage and then redirects to LOGIN_REDIRECT_URL.
"""
from __future__ import annotations

import logging

from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from django_simple_third_party_jwt import settings as jwt_settings
from django_simple_third_party_jwt.utils.accounts import get_or_create_social_user, split_email
from django_simple_third_party_jwt.utils.get_tokens_for_user import get_tokens_for_user
from django_simple_third_party_jwt.views.microsoft.msal_helpers import (
    get_sign_in_flow,
    get_token_from_code,
    remove_user_and_token,
)
from django_simple_third_party_jwt.views.microsoft.utils import get_user

logger = logging.getLogger(__name__)

TEMPLATE = "microsoft/index.html"


def sign_in(request: HttpRequest) -> HttpResponseRedirect:
    """Start the sign-in flow and send the browser to Microsoft."""
    flow = get_sign_in_flow(request.build_absolute_uri("/"))
    try:
        request.session["auth_flow"] = flow
    except Exception:
        logger.exception("[AUTH][MICROSOFT] Could not keep the sign-in flow in the session")
    return HttpResponseRedirect(flow["auth_uri"])


def sign_out(request: HttpRequest) -> HttpResponseRedirect:
    remove_user_and_token(request)
    return HttpResponseRedirect(reverse("microsoft-signin"))


def callback(request: HttpRequest) -> HttpResponse:
    """Where Microsoft sends the browser back to after sign-in."""
    try:
        result = get_token_from_code(request)
        access_token = result["access_token"]
        email = result["id_token_claims"]["preferred_username"]
    except Exception as e:
        logger.error("[AUTH][MICROSOFT] %s", e)
        return render_error(request, "")

    # The Graph profile is fetched but not stored (yet).
    get_user(access_token)

    try:
        username, domain = split_email(email)
    except ValueError:
        # preferred_username is not always an e-mail (it can be a phone number, for one).
        logger.warning("[AUTH][MICROSOFT] `%s` is not an e-mail address", email)
        return render_error(request, email)
    if domain not in jwt_settings.VALID_REGISTER_DOMAINS:
        logger.warning("[AUTH][MICROSOFT] `%s` attempts to register!!", email)
        return render_error(request, email)

    user = get_or_create_user(email, username)
    login(request, user)
    tokens = get_tokens_for_user(user)
    return _render_page(
        request,
        email=email,
        description="Welcome!",
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


def get_or_create_user(email: str, username: str) -> User:
    """The user linked to this Microsoft account (keyed by its e-mail), created on first login."""
    return get_or_create_social_user("microsoft", email, email=email, username=username)


def render_error(request: HttpRequest, email: str) -> HttpResponse:
    """The callback page without tokens: "not allowed" when we know who it was."""
    if email:
        description = "You are not allowed to access this! :("
    else:
        description = "There are something went wrong! :("
    return _render_page(request, email=email, description=description)


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
