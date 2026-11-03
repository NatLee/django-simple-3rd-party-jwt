"""Finding or creating the Django user behind a Google or Microsoft account."""
from __future__ import annotations

import logging
import uuid
from typing import Tuple

from django.contrib.auth.models import User

from django_simple_third_party_jwt.models import SocialAccount

logger = logging.getLogger(__name__)


def split_email(email: str) -> Tuple[str, str]:
    """Split an address into (local part, domain).

    Raises ValueError unless the address contains exactly one "@".
    """
    username, domain = email.split("@")
    return username, domain


def get_or_create_social_user(
    provider: str,
    unique_id: str,
    *,
    email: str,
    username: str,
    **user_fields: str,
) -> User:
    """Return the user linked to (provider, unique_id), creating both on first login.

    A new user gets `username` (the e-mail's local part), or a random UUID when that
    name is already taken. Extra keyword arguments go to `User.objects.create_user`.
    """
    tag = f"[AUTH][{provider.upper()}]"
    try:
        user = SocialAccount.objects.get(provider=provider, unique_id=unique_id).user
    except SocialAccount.DoesNotExist:
        pass
    else:
        logger.debug("%s Existing user logged in: [%s] - [%s]", tag, user.username, email)
        return user

    if User.objects.filter(username=username).exists():
        logger.debug("%s Existing username: [%s]", tag, username)
        username = str(uuid.uuid4())
        logger.debug("%s Creating new username: [%s]", tag, username)

    user = User.objects.create_user(username=username, email=email, **user_fields)
    SocialAccount.objects.create(user=user, provider=provider, unique_id=unique_id)
    logger.debug("%s Created new user: [%s] - [%s]", tag, username, email)
    return user
