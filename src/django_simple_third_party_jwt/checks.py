"""Start-up checks (run by `manage.py check` and `runserver`) for JWT_3RD_PREFIX."""
from __future__ import annotations

from typing import Any, List

from django.conf import settings
from django.core import checks

from django_simple_third_party_jwt.settings import auth_route, clean_prefix


@checks.register(checks.Tags.urls)
def check_jwt_3rd_prefix(app_configs: Any, **kwargs: Any) -> List[checks.CheckMessage]:
    """Point out a "/" at either end of JWT_3RD_PREFIX (ignored by releases after 0.3.2).

    Up to 0.3.2 the slash was kept, so "/api" or "api/" put the routes at /%2Fapi/auth/...
    or /api//auth/... and the Microsoft redirect URI got a "//". Now they mean "api". That
    moved the routes of projects that had a slash, so the warning says where they are and
    which redirect URI to register in Azure. Writing the prefix without the slash silences it.
    """
    prefix = getattr(settings, "JWT_3RD_PREFIX", None)
    if not isinstance(prefix, str):
        return []  # missing: urls.py raises an ImproperlyConfigured that names the setting
    clean = clean_prefix(prefix)
    if clean == prefix:
        return []
    routes = "/" + auth_route(clean, "...")
    callback = "<your site>/" + auth_route(clean, "microsoft/callback")
    return [
        checks.Warning(
            f"JWT_3RD_PREFIX = {prefix!r} has a '/' at one end, which is ignored, so the login routes "
            f"are at {routes} now. Up to 0.3.2 the slash was kept, which put them and the Microsoft "
            "redirect URI at a '//' address.",
            hint=(
                f"Write JWT_3RD_PREFIX = {clean!r}. If Microsoft login worked with the old address, "
                f"register {callback} as the redirect URI in Azure, and update any frontend URL "
                "that has the '//'."
            ),
            id="django_simple_third_party_jwt.W001",
        )
    ]
