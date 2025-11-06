"""Pytest configuration and fixtures."""

import pytest
from pytest_httpx import HTTPXMock


@pytest.fixture
def mock_login(httpx_mock: HTTPXMock):
    """Mock the login endpoint for JWT authentication.

    Note: This mock is marked as optional because many tests don't trigger
    authentication (e.g., when the global client is already authenticated).
    """
    httpx_mock.add_response(
        url="https://donetick.jason1365.duckdns.org/api/v1/auth/login",
        json={"token": "test_jwt_token"},
        method="POST",
        is_optional=True,  # Allow tests to not trigger login
    )
    return httpx_mock
