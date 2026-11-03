from __future__ import annotations

from typing import Dict

from django.contrib.auth.models import AbstractBaseUser
from rest_framework_simplejwt.tokens import RefreshToken


def get_tokens_for_user(user: AbstractBaseUser) -> Dict[str, str]:
    """A fresh refresh/access token pair for `user`, under two sets of key names."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh_token": str(refresh),
        "access_token": str(refresh.access_token),
        # compatibility with official Simple JWT
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
