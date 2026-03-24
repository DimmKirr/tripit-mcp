"""Shared test fixtures for tripit-mcp tests."""

import pytest
from unittest.mock import AsyncMock

from tripit_mcp.auth import TripItAuth
from tripit_mcp.client import TripItClient


TEST_CREDENTIALS = {
    "username": "test@example.com",
    "password": "testpass",
    "client_id": "test-client-id",
    "client_secret": "test-client-secret",
}


@pytest.fixture
def auth():
    return TripItAuth(**TEST_CREDENTIALS)


@pytest.fixture
def client():
    return TripItClient(**TEST_CREDENTIALS)


@pytest.fixture
def mock_tripit_client():
    """Pre-configured mock TripItClient for server tests."""
    mock = AsyncMock()
    mock.list_trips = AsyncMock()
    mock.get_trip = AsyncMock()
    return mock
