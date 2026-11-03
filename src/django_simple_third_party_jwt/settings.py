"""Package settings.

Each value is read once from the Django project's settings when this module is
first imported; the defaults below apply when a setting is missing.
"""
from __future__ import annotations

import logging
from typing import Any, List

from django.conf import settings

logger = logging.getLogger(__name__)

# 登入成功後的重定向 URL：Microsoft 登入完成後，瀏覽器會被導到這裡。
# Django 本身就有 LOGIN_REDIRECT_URL（預設 "/accounts/profile/"），
# 所以下面的 "/" 只有在專案的設定裡完全沒有這個值時才會用到。
LOGIN_REDIRECT_URL = getattr(settings, "LOGIN_REDIRECT_URL", "/")


def clean_prefix(prefix: Any) -> str:
    """JWT_3RD_PREFIX without a "/" at either end: "/api/" and "api/" mean "api"."""
    return str(prefix).strip("/")


def auth_route(prefix: str, rest: str) -> str:
    """The route for /<prefix>/auth/<rest>, or /auth/<rest> when the prefix is empty."""
    return f"{prefix}/auth/{rest}" if prefix else f"auth/{rest}"


# 網址前綴：登入網址是 /<JWT_3RD_PREFIX>/auth/...，沒設定時是 "api"。
# 前後的 "/" 會被拿掉（"/api/" 等於 "api"）；空字串代表網址直接從 /auth/... 開始。
DEFAULT_JWT_3RD_PREFIX = "api"


def route_prefix() -> str:
    """JWT_3RD_PREFIX as the routes use it, read from the project's settings right now.

    urls.py calls this when Django loads the URLconf; the module-level JWT_3RD_PREFIX below
    is the same value, read once at import like the other settings.
    """
    return clean_prefix(getattr(settings, "JWT_3RD_PREFIX", DEFAULT_JWT_3RD_PREFIX))


JWT_3RD_PREFIX = route_prefix()

# 允許登入（和自動註冊）的 email 網域，Google 和 Microsoft 都適用。
VALID_REGISTER_DOMAINS = getattr(
    settings,
    "VALID_REGISTER_DOMAINS",
    [
        "gmail.com",
        "outlook.com",
        "hotmail.com",
        "live.com",
    ],
)


def _setting_or_demo(name: str, demo_value: Any, what: str, register_at: str) -> Any:
    """Read a credential setting; fall back to the shared demo value with a warning."""
    value = getattr(settings, name, demo_value)
    if value == demo_value:
        logger.warning(
            "Using the default %s. Set %s to your own value in production; register one at %s",
            what, name, register_at,
        )
    return value


GOOGLE_CREDENTIALS_PAGE = "https://console.cloud.google.com/apis/credentials"
AZURE_APP_REGISTRATIONS_PAGE = (
    "https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/RegisteredApps"
)

# =====================
# 第三方登入的憑證。正式環境一定要換成自己的（申請頁面見上面兩個網址）。
# Google：沒設定時用作者的示範用戶端（client ID 本來就會出現在每個登入頁），並在啟動時印出警告。

__DEV_GOOGLE_CLIENT_ID = '376808175534-d6mefo6b1kqih3grjjose2euree2g3cs.apps.googleusercontent.com'
SOCIAL_GOOGLE_CLIENT_ID = _setting_or_demo(
    "SOCIAL_GOOGLE_CLIENT_ID", __DEV_GOOGLE_CLIENT_ID,
    "Google client ID", GOOGLE_CREDENTIALS_PAGE,
)

# Microsoft：沒有示範應用程式（它的 secret 曾經公開過；使用者 2026-11-04 決定拿掉）。
# 沒設定時，manage.py check 會說要設哪些（django_simple_third_party_jwt.W002），登入頁也會說明。
SOCIAL_MICROSOFT_CLIENT_ID = getattr(settings, "SOCIAL_MICROSOFT_CLIENT_ID", None)
SOCIAL_MICROSOFT_CLIENT_SECRET = getattr(settings, "SOCIAL_MICROSOFT_CLIENT_SECRET", None)


def missing_microsoft_credentials() -> List[str]:
    """The names of the Microsoft credential settings that are not set."""
    values = {
        "SOCIAL_MICROSOFT_CLIENT_ID": SOCIAL_MICROSOFT_CLIENT_ID,
        "SOCIAL_MICROSOFT_CLIENT_SECRET": SOCIAL_MICROSOFT_CLIENT_SECRET,
    }
    return [name for name, value in values.items() if not value]


# =====================
# Microsoft 登入完成後，回呼頁面會把 JWT 存進瀏覽器的 localStorage，用的是下面這兩個鍵名。

MICROSOFT_JWT_REDIRECT_ACCESS_TOKEN_KEY = getattr(
    settings,
    "MICROSOFT_JWT_REDIRECT_ACCESS_TOKEN_KEY",
    "access_token",
)

MICROSOFT_JWT_REDIRECT_REFRESH_TOKEN_KEY = getattr(
    settings,
    "MICROSOFT_JWT_REDIRECT_REFRESH_TOKEN_KEY",
    "refresh_token",
)
