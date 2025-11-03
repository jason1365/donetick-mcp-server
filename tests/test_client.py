"""Unit tests for Donetick API client."""

import pytest
from pytest_httpx import HTTPXMock

from donetick_mcp.client import DonetickClient, TokenBucket
from donetick_mcp.models import Chore, ChoreCreate


@pytest.fixture
def client():
    """Create a test client instance."""
    return DonetickClient(
        base_url="https://test.donetick.com",
        api_token="test_token",
        rate_limit_per_second=100.0,  # High limit for fast tests
        rate_limit_burst=100,
    )


@pytest.fixture
def sample_chore_data():
    """Sample chore data for testing."""
    return {
        "id": 1,
        "name": "Test Chore",
        "description": "Test description",
        "frequencyType": "once",
        "frequency": 1,
        "frequencyMetadata": {},
        "nextDueDate": "2025-11-10T00:00:00Z",
        "isRolling": False,
        "assignedTo": 1,
        "assignees": [{"userId": 1}],
        "assignStrategy": "least_completed",
        "isActive": True,
        "notification": False,
        "notificationMetadata": {"nagging": False, "predue": False},
        "labels": None,
        "labelsV2": [],
        "circleId": 1,
        "createdAt": "2025-11-03T00:00:00Z",
        "updatedAt": "2025-11-03T00:00:00Z",
        "createdBy": 1,
        "updatedBy": 1,
        "status": "active",
        "priority": 2,
        "isPrivate": False,
        "points": None,
        "subTasks": [],
        "thingChore": None,
    }


class TestTokenBucket:
    """Tests for TokenBucket rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_tokens(self):
        """Test acquiring tokens from bucket."""
        bucket = TokenBucket(rate=10.0, capacity=10)
        await bucket.acquire(5)
        assert bucket.tokens == 5.0

    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Test that tokens refill over time."""
        import asyncio

        bucket = TokenBucket(rate=10.0, capacity=10)
        await bucket.acquire(10)
        assert bucket.tokens == 0.0

        # Wait for tokens to refill
        await asyncio.sleep(0.5)
        await bucket.acquire(1)
        # Should have refilled ~5 tokens in 0.5s
        assert bucket.tokens < 10.0


class TestDonetickClient:
    """Tests for DonetickClient."""

    @pytest.mark.asyncio
    async def test_list_chores(self, client, sample_chore_data, httpx_mock: HTTPXMock):
        """Test listing all chores."""
        httpx_mock.add_response(
            url="https://test.donetick.com/eapi/v1/chore",
            json=[sample_chore_data],
        )

        async with client:
            chores = await client.list_chores()

        assert len(chores) == 1
        assert isinstance(chores[0], Chore)
        assert chores[0].name == "Test Chore"

    @pytest.mark.asyncio
    async def test_list_chores_filter_active(self, client, sample_chore_data, httpx_mock: HTTPXMock):
        """Test filtering chores by active status."""
        inactive_chore = sample_chore_data.copy()
        inactive_chore["id"] = 2
        inactive_chore["isActive"] = False

        httpx_mock.add_response(
            url="https://test.donetick.com/eapi/v1/chore",
            json=[sample_chore_data, inactive_chore],
        )

        async with client:
            active_chores = await client.list_chores(filter_active=True)

        assert len(active_chores) == 1
        assert active_chores[0].isActive is True

    @pytest.mark.asyncio
    async def test_list_chores_filter_assigned_to(
        self, client, sample_chore_data, httpx_mock: HTTPXMock
    ):
        """Test filtering chores by assigned user."""
        other_user_chore = sample_chore_data.copy()
        other_user_chore["id"] = 2
        other_user_chore["assignedTo"] = 2

        httpx_mock.add_response(
            url="https://test.donetick.com/eapi/v1/chore",
            json=[sample_chore_data, other_user_chore],
        )

        async with client:
            user_chores = await client.list_chores(assigned_to_user_id=1)

        assert len(user_chores) == 1
        assert user_chores[0].assignedTo == 1

    @pytest.mark.asyncio
    async def test_get_chore(self, client, sample_chore_data, httpx_mock: HTTPXMock):
        """Test getting a specific chore by ID."""
        httpx_mock.add_response(
            url="https://test.donetick.com/eapi/v1/chore",
            json=[sample_chore_data],
        )

        async with client:
            chore = await client.get_chore(1)

        assert chore is not None
        assert chore.id == 1
        assert chore.name == "Test Chore"

    @pytest.mark.asyncio
    async def test_get_chore_not_found(self, client, sample_chore_data, httpx_mock: HTTPXMock):
        """Test getting a non-existent chore."""
        httpx_mock.add_response(
            url="https://test.donetick.com/eapi/v1/chore",
            json=[sample_chore_data],
        )

        async with client:
            chore = await client.get_chore(999)

        assert chore is None

    @pytest.mark.asyncio
    async def test_create_chore(self, client, sample_chore_data, httpx_mock: HTTPXMock):
        """Test creating a new chore."""
        httpx_mock.add_response(
            url="https://test.donetick.com/eapi/v1/chore",
            json=sample_chore_data,
            method="POST",
        )

        async with client:
            chore_create = ChoreCreate(
                Name="Test Chore",
                Description="Test description",
                DueDate="2025-11-10",
            )
            chore = await client.create_chore(chore_create)

        assert chore.id == 1
        assert chore.name == "Test Chore"

    @pytest.mark.asyncio
    async def test_delete_chore(self, client, httpx_mock: HTTPXMock):
        """Test deleting a chore."""
        httpx_mock.add_response(
            url="https://test.donetick.com/eapi/v1/chore/1",
            json={},
            method="DELETE",
        )

        async with client:
            result = await client.delete_chore(1)

        assert result is True

    @pytest.mark.asyncio
    async def test_complete_chore(self, client, sample_chore_data, httpx_mock: HTTPXMock):
        """Test completing a chore."""
        httpx_mock.add_response(
            url="https://test.donetick.com/eapi/v1/chore/1/complete",
            json=sample_chore_data,
            method="POST",
        )

        async with client:
            chore = await client.complete_chore(1)

        assert chore.id == 1
        assert chore.name == "Test Chore"

    @pytest.mark.asyncio
    async def test_rate_limit_429_retry(self, client, sample_chore_data, httpx_mock: HTTPXMock):
        """Test retry logic on 429 rate limit."""
        # First request returns 429
        httpx_mock.add_response(
            url="https://test.donetick.com/eapi/v1/chore",
            status_code=429,
            headers={"Retry-After": "0.1"},
        )
        # Second request succeeds
        httpx_mock.add_response(
            url="https://test.donetick.com/eapi/v1/chore",
            json=[sample_chore_data],
        )

        async with client:
            chores = await client.list_chores()

        assert len(chores) == 1

    @pytest.mark.asyncio
    async def test_http_error_4xx_no_retry(self, client, httpx_mock: HTTPXMock):
        """Test that 4xx errors don't retry (except 429)."""
        httpx_mock.add_response(
            url="https://test.donetick.com/eapi/v1/chore",
            status_code=404,
            json={"error": "Not found"},
        )

        async with client:
            with pytest.raises(Exception):
                await client.list_chores()

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, client):
        """Test that context manager properly cleans up."""
        async with client:
            pass

        # Client should be closed after context exit
        assert client.client.is_closed

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client, sample_chore_data, httpx_mock: HTTPXMock):
        """Test handling concurrent requests."""
        import asyncio

        # Mock multiple responses
        for _ in range(5):
            httpx_mock.add_response(
                url="https://test.donetick.com/eapi/v1/chore",
                json=[sample_chore_data],
            )

        async with client:
            # Launch 5 concurrent requests
            tasks = [client.list_chores() for _ in range(5)]
            results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 5
        assert all(len(r) == 1 for r in results)
