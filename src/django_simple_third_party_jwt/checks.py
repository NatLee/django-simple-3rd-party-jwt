"""Start-up checks (run by `manage.py check` and `runserver`) for settings that break the routes quietly."""
from __future__ import annotations

from typing import Any, List

from django.conf import settings
from django.core import checks

EXAMPLE = "JWT_3RD_PREFIX = 'api'"


@checks.register(checks.Tags.urls)
def check_jwt_3rd_prefix(app_configs: Any, **kwargs: Any) -> List[checks.CheckMessage]:
    """Warn when JWT_3RD_PREFIX is empty or has a "/" at either end.

    urls.py builds the routes as f"{prefix}/auth/...", so "/api" or "api/" give
    /%2Fapi/auth/... or /api//auth/... instead of /api/auth/..., and the Microsoft
    redirect URI gets a "//". Only a warning: the routes stay as they are, because a
    project may have registered exactly that redirect URI in Azure.
    """
    prefix = getattr(settings, "JWT_3RD_PREFIX", None)
    if not isinstance(prefix, str):
        return []  # missing: urls.py raises an ImproperlyConfigured that names the setting
    clean = prefix.strip("/")
    if not clean:
        return [
            checks.Warning(
                f"JWT_3RD_PREFIX = {prefix!r} is empty, so every login route starts with '/' "
                "and is not served at /auth/... as you would expect.",
                hint=f"Set a path segment, for example {EXAMPLE} for routes at /api/auth/....",
                id="django_simple_third_party_jwt.W002",
            )
        ]
    if clean != prefix:
        return [
            checks.Warning(
                f"JWT_3RD_PREFIX = {prefix!r} starts or ends with '/', so the login routes are not "
                f"at /{clean}/auth/... and the Microsoft redirect URI gets a '//'.",
                hint=(
                    f"Use JWT_3RD_PREFIX = {clean!r} and register "
                    f"<your site>/{clean}/auth/microsoft/callback as the redirect URI in Azure."
                ),
                id="django_simple_third_party_jwt.W001",
            )
        ]
    return []
