from __future__ import annotations

import logging
from typing import Any, Dict

from django.contrib.auth.base_user import AbstractBaseUser
from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import serializers

from django_simple_third_party_jwt import settings
from django_simple_third_party_jwt.exception import InvalidCredentialError, InvalidEmailError
from django_simple_third_party_jwt.utils.accounts import get_or_create_social_user, split_email

logger = logging.getLogger(__name__)

GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
REJECTED = "Google did not accept the credential: {}"


class GoogleLoginSerializer(serializers.Serializer):
    """Turns the ID token that Google Sign-In gives the browser into a Django user.

    `save()` returns the user linked to the Google account, creating it on first login.
    It raises InvalidCredentialError when Google's token does not check out, and
    InvalidEmailError when the address is not verified or outside VALID_REGISTER_DOMAINS.
    """

    # 用於接收 Google 返回的憑證（JWT 格式的 ID token）
    credential = serializers.CharField(required=True)

    def verify_token(self, credential: str) -> Dict[str, Any]:
        """Check the ID token's signature, expiry, issuer and audience; return its claims."""
        logger.debug("Verify %s...", credential[:50])
        try:
            # 使用 Google 提供的方法驗證 token（會向 Google 取得公鑰）
            idinfo = id_token.verify_oauth2_token(
                credential, google_requests.Request(), settings.SOCIAL_GOOGLE_CLIENT_ID
            )
        except google_exceptions.TransportError:
            raise  # Google's keys could not be fetched: a problem on our side, not the client's
        except (ValueError, google_exceptions.GoogleAuthError) as error:
            self._refuse(REJECTED.format(error))
        # google-auth checks these as well; checked again here because they are what makes
        # the token ours.
        if idinfo["iss"] not in GOOGLE_ISSUERS:
            self._refuse(REJECTED.format("it was not issued by Google."))
        if idinfo["aud"] != settings.SOCIAL_GOOGLE_CLIENT_ID:
            self._refuse(REJECTED.format("it was issued for another client ID."))
        logger.info("successfully verified")
        return idinfo

    @staticmethod
    def _refuse(detail: str) -> None:
        # The client's mistake, not a crash: a warning without a traceback.
        logger.warning("[AUTH][GOOGLE] %s", detail)
        raise InvalidCredentialError(detail) from None

    def create(self, validated_data: Dict[str, Any]) -> AbstractBaseUser:
        idinfo = self.verify_token(validated_data.get("credential"))
        email = idinfo["email"]

        # Google 會告訴我們它有沒有驗證過這個 email；沒驗證過就不能拿來比對網域
        if idinfo.get("email_verified") is not True:
            logger.warning("[AUTH][GOOGLE] `%s` is not verified by Google", email)
            raise InvalidEmailError("Google has not verified this e-mail address.")

        username, domain = split_email(email)

        # 檢查 email 網域是否在允許的列表中
        if domain not in settings.VALID_REGISTER_DOMAINS:
            logger.warning("[AUTH][GOOGLE] `%s` attempts to register!!", email)
            raise InvalidEmailError

        # Google 帳號用 sub（Google 給每個帳號的固定 ID）對應到使用者
        return get_or_create_social_user(
            "google",
            idinfo["sub"],
            email=email,
            username=username,
            first_name=idinfo.get("given_name", ""),
            last_name=idinfo.get("family_name", ""),
        )


# 解碼後的 idinfo 範例：
# {
#     "iss": "https://accounts.google.com",
#     "aud": "123456789-abcdefghijklmnopqrstuvwxyz012345.apps.googleusercontent.com",
#     "sub": "123456789012345678901",
#     "email": "john.doe@example.com",
#     "email_verified": True,
#     "given_name": "John",
#     "family_name": "Doe",
#     ...
# }
