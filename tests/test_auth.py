"""Tests for TripIt OAuth2 ROPC auth client."""

import time
import httpx
import pytest
from unittest.mock import AsyncMock, patch


def make_token_response(expires_in=3600):
    return httpx.Response(
        200,
        json={
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_in": expires_in,
        },
    )


class TestTripItAuth:
    async def test_get_token_fetches_new_token(self, auth):
        with patch.object(auth._client, "post", new_callable=AsyncMock, return_value=make_token_response()):
            token = await auth.get_token()
            assert token == "Bearer test-access-token"

    async def test_get_token_caches_token(self, auth):
        mock_post = AsyncMock(return_value=make_token_response())
        with patch.object(auth._client, "post", mock_post):
            await auth.get_token()
            await auth.get_token()
            assert mock_post.call_count == 1

    async def test_get_token_refreshes_expired_token(self, auth):
        mock_post = AsyncMock(return_value=make_token_response(expires_in=0))
        with patch.object(auth._client, "post", mock_post):
            await auth.get_token()
            auth._token_expiry = time.time() - 1
            await auth.get_token()
            assert mock_post.call_count == 2

    async def test_get_token_raises_on_auth_failure(self, auth):
        error_response = httpx.Response(401, json={"error": "invalid_grant"})
        with patch.object(auth._client, "post", new_callable=AsyncMock, return_value=error_response):
            with pytest.raises(RuntimeError, match="OAuth2 token request failed"):
                await auth.get_token()

    async def test_headers_include_iphone_user_agent(self, auth):
        assert "iPhone" in auth.base_headers["user-agent"]
