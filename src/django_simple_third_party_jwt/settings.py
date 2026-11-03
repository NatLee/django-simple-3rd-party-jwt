"""Package settings.

Each value is read once from the Django project's settings when this module is
first imported; the defaults below apply when a setting is missing.
"""
from __future__ import annotations

import logging
from typing import Any

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


# 網址前綴：登入網址是 /<JWT_3RD_PREFIX>/auth/...，通常設成 "api"。
# 前後的 "/" 會被拿掉（"/api/" 等於 "api"）；空字串代表網址直接從 /auth/... 開始。
# urls.py 直接讀 Django 的設定，所以專案一定要設；這裡的預設值只給 Microsoft 回呼網址用。
JWT_3RD_PREFIX = clean_prefix(getattr(settings, "JWT_3RD_PREFIX", ""))

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
# 第三方登入的憑證。沒設定時會用作者的示範應用程式，並在啟動時印出警告。
# 正式環境一定要換成自己的（申請頁面見上面兩個網址）。

__DEV_GOOGLE_CLIENT_ID = '376808175534-d6mefo6b1kqih3grjjose2euree2g3cs.apps.googleusercontent.com'
SOCIAL_GOOGLE_CLIENT_ID = _setting_or_demo(
    "SOCIAL_GOOGLE_CLIENT_ID", __DEV_GOOGLE_CLIENT_ID,
    "Google client ID", GOOGLE_CREDENTIALS_PAGE,
)

__DEV_MICROSOFT_CLIENT_ID = '32346173-22bc-43b2-b6ed-f88f6a76e38c'
SOCIAL_MICROSOFT_CLIENT_ID = _setting_or_demo(
    "SOCIAL_MICROSOFT_CLIENT_ID", __DEV_MICROSOFT_CLIENT_ID,
    "Microsoft client ID", AZURE_APP_REGISTRATIONS_PAGE,
)

# 警告：使用者端密鑰應該保密，不應該在版本控制中公開。
__DEV_MICROSOFT_CLIENT_SECRET = 'K5z8Q~dIXDiFN5qjMjRjIx34cZOJ3Glkrg.dxcG9'
SOCIAL_MICROSOFT_CLIENT_SECRET = _setting_or_demo(
    "SOCIAL_MICROSOFT_CLIENT_SECRET", __DEV_MICROSOFT_CLIENT_SECRET,
    "Microsoft client secret", AZURE_APP_REGISTRATIONS_PAGE,
)

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
