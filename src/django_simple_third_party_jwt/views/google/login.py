from __future__ import annotations

from typing import Any

from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from django_simple_third_party_jwt.serilizers import GoogleLoginSerializer
from django_simple_third_party_jwt.utils.third_party_login import third_party_login


class _GoogleLoginBase(TokenObtainPairView):
    """POST {"credential": <Google ID token>} and get a JWT pair back."""

    permission_classes = (AllowAny,)  # AllowAny for login
    serializer_class = GoogleLoginSerializer
    start_session = False

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        return third_party_login(serializer, request, session=self.start_session)


class GoogleLogin(_GoogleLoginBase):
    """Google login that only answers with JWTs."""


class GoogleLoginSession(_GoogleLoginBase):
    """Google login that answers with JWTs and also logs the user into the Django session."""

    start_session = True
