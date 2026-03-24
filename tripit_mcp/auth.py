"""OAuth2 ROPC auth client for TripIt v2 API (spoofed iOS client)."""

import time
import httpx

TRIPIT_BASE_URL = "https://api.tripit.com"

BASE_HEADERS = {
    "user-agent": "Tripit/18.1.0.2310191134 iPhone/17.0.2",
    "accept-language": "en-GB,en;q=0.9",
    "X-TRIPIT-APP-INFO": "iOS/18.1.0",
    "accept": "*/*",
}


class TripItAuth:
    """Manages OAuth2 ROPC tokens with in-memory caching."""

    def __init__(self, username: str, password: str, client_id: str, client_secret: str):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_headers = dict(BASE_HEADERS)
        self._client = httpx.AsyncClient(timeout=30.0)
        self._access_token: str | None = None
        self._token_type: str = "Bearer"
        self._token_expiry: float = 0

    async def get_token(self) -> str:
        """Return a valid Bearer token, refreshing if expired."""
        if self._access_token and time.time() < self._token_expiry:
            return f"{self._token_type} {self._access_token}"

        response = await self._client.post(
            f"{TRIPIT_BASE_URL}/oauth2/token",
            headers=self.base_headers,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "openid offline_access email",
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
            },
        )

        if response.status_code != 200:
            raise RuntimeError(f"OAuth2 token request failed: {response.status_code} {response.text}")

        data = response.json()
        self._access_token = data["access_token"]
        self._token_type = data.get("token_type", "Bearer")
        # TripIt tokens expire in 600s; refresh early at 1/10 TTL (60s) as safety margin
        self._token_expiry = time.time() + float(data["expires_in"]) / 10

        return f"{self._token_type} {self._access_token}"

    async def close(self):
        await self._client.aclose()
