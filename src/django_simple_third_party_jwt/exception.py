from __future__ import annotations

from typing import Optional


class LoginRefused(Exception):
    """The provider's answer does not let this person in.

    `detail` says why; the login endpoints send it to the client with a 401.
    """

    default_detail = "Login refused."

    def __init__(self, detail: Optional[str] = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class InvalidEmailError(LoginRefused):
    """The e-mail address may not sign in: its domain is not allowed, or it is not verified."""

    default_detail = "This email is invalid."


class InvalidCredentialError(LoginRefused):
    """The provider does not accept the credential: malformed, expired, for another client..."""

    default_detail = "Google did not accept the credential."
