"""Finding or creating the Django user behind a Google or Microsoft account.

Works with the project's user model (AUTH_USER_MODEL), whatever its fields are called.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Tuple

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import FieldDoesNotExist

from django_simple_third_party_jwt.exception import LoginRefused
from django_simple_third_party_jwt.models import SocialAccount

logger = logging.getLogger(__name__)


def split_email(email: str) -> Tuple[str, str]:
    """Split an address into (local part, domain).

    Raises ValueError unless the address contains exactly one "@".
    """
    username, domain = email.split("@")
    return username, domain


def has_field(model: Any, name: str) -> bool:
    try:
        model._meta.get_field(name)
    except FieldDoesNotExist:
        return False
    return True


def get_or_create_social_user(
    provider: str,
    unique_id: str,
    *,
    email: str,
    username: str,
    **user_fields: str,
) -> AbstractBaseUser:
    """Return the user linked to (provider, unique_id), creating both on first login.

    A new user gets `username` (the e-mail's local part) as its USERNAME_FIELD, or a random
    UUID when that name is already taken. When the model's username *is* the e-mail address,
    it gets the address, and a taken address refuses the login (LoginRefused). Extra keyword
    arguments (first_name, ...) are set when the model has such a field.
    """
    tag = f"[AUTH][{provider.upper()}]"
    try:
        user = SocialAccount.objects.get(provider=provider, unique_id=unique_id).user
    except SocialAccount.DoesNotExist:
        pass
    else:
        logger.debug("%s Existing user logged in: [%s] - [%s]", tag, user.get_username(), email)
        return user

    user_model = get_user_model()
    username_field = user_model.USERNAME_FIELD
    email_field = user_model.get_email_field_name()
    if username_field == email_field:
        username = email
    if user_model._default_manager.filter(**{username_field: username}).exists():
        if username_field == email_field:
            logger.warning("%s `%s` already belongs to another user", tag, email)
            raise LoginRefused("Another account already uses this e-mail address.")
        logger.debug("%s Existing username: [%s]", tag, username)
        username = str(uuid.uuid4())
        logger.debug("%s Creating new username: [%s]", tag, username)

    fields = {username_field: username, email_field: email, **user_fields}
    user = user_model._default_manager.create_user(
        **{name: value for name, value in fields.items() if has_field(user_model, name)}
    )
    SocialAccount.objects.create(user=user, provider=provider, unique_id=unique_id)
    logger.debug("%s Created new user: [%s] - [%s]", tag, username, email)
    return user
