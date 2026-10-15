"""Minimal Steam OpenID 2.0 helper for user authentication."""

from __future__ import annotations

import re
from urllib.parse import urlencode

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"


class SteamAuth:
    """Handles Steam OpenID login flow."""

    def __init__(self, realm: str = "http://localhost:8000", return_to: str = "http://localhost:8000/api/auth/callback"):
        self.realm = realm
        self.return_to = return_to

    def get_login_url(self) -> str:
        """Return the URL the user should be redirected to for Steam login."""
        params = {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.mode": "checkid_setup",
            "openid.return_to": self.return_to,
            "openid.realm": self.realm,
            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
        }
        return f"{STEAM_OPENID_URL}?{urlencode(params)}"

    @staticmethod
    def extract_steam_id(claimed_id: str) -> str | None:
        """Extract the 64-bit Steam ID from the OpenID claimed_id URL."""
        match = re.search(r"openid/id/(\d+)", claimed_id)
        return match.group(1) if match else None

    async def verify_login(self, params: dict[str, str]) -> str | None:
        """
        Verify an OpenID callback and return the Steam ID on success.

        ``params`` should be the query-string parameters the user was
        redirected back with (e.g. ``request.query_params``).
        """
        import httpx

        validation_params = dict(params)
        validation_params["openid.mode"] = "check_authentication"

        async with httpx.AsyncClient() as client:
            resp = await client.post(STEAM_OPENID_URL, data=validation_params)
            if "is_valid:true" in resp.text:
                return self.extract_steam_id(params.get("openid.claimed_id", ""))
        return None
