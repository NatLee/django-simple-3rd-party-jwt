from __future__ import annotations

from typing import Any, Dict

import requests

from django_simple_third_party_jwt.views.microsoft.msal_helpers import callback_url  # noqa: F401 (old import path)

graph_url = "https://graph.microsoft.com/v1.0"


def get_user(token: str) -> Dict[str, Any]:
    """The signed-in user's display name from Microsoft Graph."""
    response = requests.get(
        f"{graph_url}/me",
        headers={"Authorization": f"Bearer {token}"},
        params={"$select": "displayName"},
    )
    return response.json()
