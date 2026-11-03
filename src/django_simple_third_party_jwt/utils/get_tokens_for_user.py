from __future__ import annotations

from typing import Dict

from django.contrib.auth.models import AbstractBaseUser
from rest_framework_simplejwt.tokens import RefreshToken


def get_tokens_for_user(user: AbstractBaseUser) -> Dict[str, str]:
    """A fresh refresh/access token pair for `user`, under two sets of key names."""
    refresh = RefreshToken.for_user(user)
    # Every read of `refresh.access_token` mints a new token, so read it once.
    refresh_token = str(refresh)
    access_token = str(refresh.access_token)
    return {
        "refresh_token": refresh_token,
        "access_token": access_token,
        # compatibility with official Simple JWT
        "refresh": refresh_token,
        "access": access_token,
    }
