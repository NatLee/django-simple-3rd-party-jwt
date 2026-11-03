from __future__ import annotations

import logging

from django.contrib.auth import login
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from django_simple_third_party_jwt.exception import InvalidEmailError
from django_simple_third_party_jwt.utils.get_tokens_for_user import get_tokens_for_user

logger = logging.getLogger(__name__)


def third_party_login(serializer: BaseSerializer, request: Request, session: bool = False) -> Response:
    """Validate the login data, save it into a user and answer with a JWT pair.

    Missing or malformed data raises DRF's ValidationError (a 400 answer). An e-mail
    outside VALID_REGISTER_DOMAINS answers 401; any ValueError from the serializer
    (for example a credential Google rejects) answers 500.
    With `session=True` the user is also logged into the Django session.
    """
    serializer.is_valid(raise_exception=True)
    try:
        user = serializer.save()
        if session:
            login(request=request, user=user)
        return Response(get_tokens_for_user(user))
    except InvalidEmailError:
        return Response({"status": "error", "detail": "This email is invalid."}, status=401)
    except ValueError as exception:
        logger.error(exception)
        return Response({"status": "error", "detail": "Something went wrong :("}, status=500)
