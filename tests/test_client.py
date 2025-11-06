"""Unit tests for Donetick API client."""

import pytest
from pytest_httpx import HTTPXMock

from donetick_mcp.client import DonetickClient, TokenBucket
from donetick_mcp.models import Chore, ChoreCreate, User, UserProfile


@pytest.fixture
def client():
    """Create a test client instance."""
    return DonetickClient(
        base_url="https://test.donetick.com",
        username="test_user",
        password="test_password",
        rate_limit_per_second=100.0,  # High limit for fast tests
        rate_limit_burst=100,
    )


@pytest.fixture
def mock_login(httpx_mock: HTTPXMock):
    """Mock the login endpoint for authentication."""
    httpx_mock.add_response(
        url="https://test.donetick.com/api/v1/auth/login",
        json={"token": "test_jwt_token"},
        method="POST",
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
    async def test_list_chores(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test listing all chores."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json=[sample_chore_data],
        )

        async with client:
            chores = await client.list_chores()

        assert len(chores) == 1
        assert isinstance(chores[0], Chore)
        assert chores[0].name == "Test Chore"

    @pytest.mark.asyncio
    async def test_list_chores_filter_active(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test filtering chores by active status."""
        inactive_chore = sample_chore_data.copy()
        inactive_chore["id"] = 2
        inactive_chore["isActive"] = False

        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json=[sample_chore_data, inactive_chore],
        )

        async with client:
            active_chores = await client.list_chores(filter_active=True)

        assert len(active_chores) == 1
        assert active_chores[0].isActive is True

    @pytest.mark.asyncio
    async def test_list_chores_filter_assigned_to(
        self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login
    ):
        """Test filtering chores by assigned user."""
        other_user_chore = sample_chore_data.copy()
        other_user_chore["id"] = 2
        other_user_chore["assignedTo"] = 2

        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json=[sample_chore_data, other_user_chore],
        )

        async with client:
            user_chores = await client.list_chores(assigned_to_user_id=1)

        assert len(user_chores) == 1
        assert user_chores[0].assignedTo == 1

    @pytest.mark.asyncio
    async def test_get_chore(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test getting a specific chore by ID."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json=sample_chore_data,
        )

        async with client:
            chore = await client.get_chore(1)

        assert chore is not None
        assert chore.id == 1
        assert chore.name == "Test Chore"

    @pytest.mark.asyncio
    async def test_get_chore_not_found(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test getting a non-existent chore."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/999",
            status_code=404,
        )

        async with client:
            chore = await client.get_chore(999)

        assert chore is None

    @pytest.mark.asyncio
    async def test_create_chore(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test creating a new chore."""
        # Mock POST response (API returns {'res': chore_id})
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json={"res": 1},
            method="POST",
        )
        # Mock GET response for fetching created chore
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json=sample_chore_data,
        )

        async with client:
            chore_create = ChoreCreate(
                name="Test Chore",
                description="Test description",
                dueDate="2025-11-10",
            )
            chore = await client.create_chore(chore_create)

        assert chore.id == 1
        assert chore.name == "Test Chore"

    @pytest.mark.asyncio
    async def test_delete_chore(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test deleting a chore."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json={},
            method="DELETE",
        )

        async with client:
            result = await client.delete_chore(1)

        assert result is True

    @pytest.mark.asyncio
    async def test_complete_chore(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test completing a chore."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1/do",
            json=sample_chore_data,
            method="POST",
        )

        async with client:
            chore = await client.complete_chore(1)

        assert chore.id == 1
        assert chore.name == "Test Chore"

    @pytest.mark.asyncio
    async def test_update_chore_basic(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test updating basic chore fields (name, description, due date)."""
        # Mock GET to fetch current chore
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json={"res": sample_chore_data},
            method="GET",
        )
        # Mock PUT to update chore
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json={"message": "Chore added successfully"},
            method="PUT",
        )
        # Mock GET to fetch updated chore
        updated_chore = {**sample_chore_data, "name": "Updated Name", "description": "Updated description"}
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json={"res": updated_chore},
            method="GET",
        )

        async with client:
            from donetick_mcp.models import ChoreUpdate
            update = ChoreUpdate(name="Updated Name", description="Updated description")
            chore = await client.update_chore(1, update)

        assert chore.id == 1
        assert chore.name == "Updated Name"
        assert chore.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_chore_assignee_constraint(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test that update_chore enforces assignedTo must be in assignees array."""
        # Mock GET to fetch chore with assignedTo but empty assignees (data inconsistency)
        inconsistent_chore = {
            **sample_chore_data,
            "assignedTo": 5,  # User 5 assigned
            "assignees": [],  # But not in assignees array!
        }
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json={"res": inconsistent_chore},
            method="GET",
        )

        # Mock PUT - should receive payload with assignedTo in assignees
        def check_assignee_constraint(request):
            import json
            import httpx as httpx_lib
            payload = request.read().decode()
            data = json.loads(payload)
            # Verify the constraint is satisfied
            assert data["assignedTo"] == 5
            assert 5 in data["assignees"], "assignedTo must be in assignees array"
            return httpx_lib.Response(200, json={"message": "Chore added successfully"})

        httpx_mock.add_callback(check_assignee_constraint, url="https://test.donetick.com/api/v1/chores/", method="PUT")

        # Mock GET to return updated chore
        fixed_chore = {**inconsistent_chore, "assignees": [{"userId": 5}]}
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json={"res": fixed_chore},
            method="GET",
        )

        async with client:
            from donetick_mcp.models import ChoreUpdate
            update = ChoreUpdate(name="Updated Name")
            chore = await client.update_chore(1, update)

        assert chore.id == 1
        assert chore.assignedTo == 5
        # The fix should have added assignedTo to assignees

    @pytest.mark.asyncio
    async def test_update_chore_priority(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test updating chore priority."""
        updated_chore = {**sample_chore_data, "priority": 4}
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1/priority",
            json=updated_chore,
            method="PUT",
        )

        async with client:
            chore = await client.update_chore_priority(1, 4)

        assert chore.id == 1
        assert chore.priority == 4

    @pytest.mark.asyncio
    async def test_update_chore_priority_validation(self, client):
        """Test update_chore_priority with invalid priority."""
        async with client:
            with pytest.raises(ValueError, match="must be 0-4"):
                await client.update_chore_priority(1, 5)

            with pytest.raises(ValueError, match="must be 0-4"):
                await client.update_chore_priority(1, -1)

    @pytest.mark.asyncio
    async def test_update_chore_assignee(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test reassigning a chore to different user."""
        # Mock GET to fetch current chore
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json={"res": sample_chore_data},
            method="GET",
        )
        # Mock PUT to update chore
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json={"message": "Chore added successfully"},
            method="PUT",
        )
        # Mock GET to fetch updated chore
        updated_chore = {**sample_chore_data, "assignedTo": 2, "assignees": [{"userId": 2}]}
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json={"res": updated_chore},
            method="GET",
        )

        async with client:
            chore = await client.update_chore_assignee(1, 2)

        assert chore.id == 1
        assert chore.assignedTo == 2

    @pytest.mark.asyncio
    async def test_skip_chore(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test skipping a chore."""
        updated_chore = {**sample_chore_data, "nextDueDate": "2025-11-17"}
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1/skip",
            json=updated_chore,
            method="POST",
        )

        async with client:
            chore = await client.skip_chore(1)

        assert chore.id == 1
        assert chore.nextDueDate == "2025-11-17"

    @pytest.mark.asyncio
    async def test_update_subtask_completion(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test updating subtask completion status."""
        # Mock getting the chore with subtasks
        chore_with_subtasks = {
            **sample_chore_data,
            "subTasks": [
                {"id": 1, "name": "Task 1", "orderId": 0, "completedAt": None, "completedBy": 0},
                {"id": 2, "name": "Task 2", "orderId": 1, "completedAt": None, "completedBy": 0},
            ]
        }
        # First GET: update_subtask_completion fetches current chore
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json={"res": chore_with_subtasks},
        )
        # Second GET: update_chore fetches current chore
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json={"res": chore_with_subtasks},
        )

        # Mock PUT response (returns message)
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json={"message": "Chore added successfully"},
            method="PUT",
        )

        # Third GET: update_chore fetches updated chore to return
        updated_chore = {
            **sample_chore_data,
            "subTasks": [
                {"id": 1, "name": "Task 1", "orderId": 0, "completedAt": "2025-11-05T12:00:00Z", "completedBy": 0},
                {"id": 2, "name": "Task 2", "orderId": 1, "completedAt": None, "completedBy": 0},
            ]
        }
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json={"res": updated_chore},
        )

        async with client:
            chore = await client.update_subtask_completion(1, 1, True)

        assert chore.id == 1
        assert len(chore.subTasks) == 2
        assert chore.subTasks[0]["completedAt"] is not None
        assert chore.subTasks[1]["completedAt"] is None

    @pytest.mark.asyncio
    async def test_rate_limit_429_retry(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test retry logic on 429 rate limit."""
        # First request returns 429
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            status_code=429,
            headers={"Retry-After": "0.1"},
        )
        # Second request succeeds
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json=[sample_chore_data],
        )

        async with client:
            chores = await client.list_chores()

        assert len(chores) == 1

    @pytest.mark.asyncio
    async def test_http_error_4xx_no_retry(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test that 4xx errors don't retry (except 429)."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
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
    async def test_concurrent_requests(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test handling concurrent requests."""
        import asyncio

        # Mock multiple responses
        for _ in range(5):
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/",
                json=[sample_chore_data],
            )

        async with client:
            # Launch 5 concurrent requests
            tasks = [client.list_chores() for _ in range(5)]
            results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 5
        assert all(len(r) == 1 for r in results)

    @pytest.mark.asyncio
    async def test_jwt_login(self, client, httpx_mock: HTTPXMock):
        """Test JWT authentication login."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/auth/login",
            json={"token": "test_jwt_token_123"},
            method="POST",
        )

        async with client:
            await client.login()

        assert client._jwt_token == "test_jwt_token_123"
        assert "Authorization" in client.client.headers
        assert client.client.headers["Authorization"] == "Bearer test_jwt_token_123"

    @pytest.mark.asyncio
    async def test_jwt_401_retry(self, client, sample_chore_data, httpx_mock: HTTPXMock):
        """Test that 401 errors trigger token refresh and retry."""
        # First login
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/auth/login",
            json={"token": "initial_token"},
            method="POST",
        )
        # First request returns 401
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            status_code=401,
        )
        # Token refresh
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/auth/login",
            json={"token": "refreshed_token"},
            method="POST",
        )
        # Retry succeeds
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json=[sample_chore_data],
        )

        async with client:
            chores = await client.list_chores()

        assert len(chores) == 1
        assert client._jwt_token == "refreshed_token"

    @pytest.mark.asyncio
    async def test_jwt_401_double_failure(self, client, httpx_mock: HTTPXMock):
        """Test that repeated 401 errors raise authentication error."""
        # First login
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/auth/login",
            json={"token": "initial_token"},
            method="POST",
        )
        # First request returns 401
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            status_code=401,
            method="GET",
        )
        # Token refresh
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/auth/login",
            json={"token": "refreshed_token"},
            method="POST",
        )
        # Retry also fails with 401 - need mocks for remaining retry attempts (max 3 total)
        for _ in range(2):
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/",
                status_code=401,
                method="GET",
            )

        async with client:
            with pytest.raises(Exception) as exc_info:
                await client.list_chores()

        # Should contain HTTP or authentication error message
        exc_message = str(exc_info.value)
        assert "401" in exc_message or "Authentication" in exc_message or "Unauthorized" in exc_message

    # ==================== USER MANAGEMENT TESTS ====================

    @pytest.mark.asyncio
    async def test_list_users_success(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test listing all circle users."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/users/",
            json=[
                {"id": 1, "username": "alice", "displayName": "Alice Smith", "email": "alice@example.com"},
                {"id": 2, "username": "bob", "displayName": "Bob Jones", "email": "bob@example.com"},
            ],
        )

        async with client:
            users = await client.list_users()

        assert len(users) == 2
        assert users[0].username == "alice"
        assert users[0].displayName == "Alice Smith"
        assert users[1].username == "bob"

    @pytest.mark.asyncio
    async def test_list_users_empty(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test listing users when circle is empty."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/users/",
            json=[],
        )

        async with client:
            users = await client.list_users()

        assert len(users) == 0

    @pytest.mark.asyncio
    async def test_list_users_wrapped_response(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test handling wrapped response format."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/users/",
            json={
                "users": [
                    {"id": 1, "username": "charlie", "displayName": "Charlie Brown"},
                ]
            },
        )

        async with client:
            users = await client.list_users()

        assert len(users) == 1
        assert users[0].username == "charlie"

    @pytest.mark.asyncio
    async def test_list_users_res_wrapped(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test handling 'res' wrapped response format."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/users/",
            json={
                "res": [
                    {"id": 3, "username": "diana", "displayName": "Diana Prince"},
                ]
            },
        )

        async with client:
            users = await client.list_users()

        assert len(users) == 1
        assert users[0].username == "diana"

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test getting current user profile with all fields."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/users/profile",
            json={
                "id": 1,
                "username": "alice",
                "displayName": "Alice Smith",
                "email": "alice@example.com",
                "circleId": 10,
                "image": "https://example.com/avatar.jpg",
                "points": 250,
                "pointsRedeemed": 50,
                "isActive": True,
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-11-01T00:00:00Z",
                "storageUsed": 1024,
                "storageLimit": 10485760,
            },
        )

        async with client:
            profile = await client.get_user_profile()

        assert profile.id == 1
        assert profile.username == "alice"
        assert profile.displayName == "Alice Smith"
        assert profile.email == "alice@example.com"
        assert profile.points == 250
        assert profile.pointsRedeemed == 50
        assert profile.storageUsed == 1024

    @pytest.mark.asyncio
    async def test_get_user_profile_wrapped(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test profile with wrapped response."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/users/profile",
            json={
                "res": {
                    "id": 2,
                    "username": "bob",
                    "displayName": "Bob Jones",
                    "email": "bob@example.com",
                }
            },
        )

        async with client:
            profile = await client.get_user_profile()

        assert profile.id == 2
        assert profile.username == "bob"

    @pytest.mark.asyncio
    async def test_get_user_profile_401_refresh(self, client, httpx_mock: HTTPXMock):
        """Test automatic JWT refresh on 401."""
        # First login
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/auth/login",
            json={"token": "initial_token"},
            method="POST",
        )
        # First request returns 401
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/users/profile",
            status_code=401,
        )
        # Token refresh
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/auth/login",
            json={"token": "refreshed_token"},
            method="POST",
        )
        # Retry succeeds
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/users/profile",
            json={
                "id": 1,
                "username": "alice",
                "displayName": "Alice",
                "email": "alice@example.com",
            },
        )

        async with client:
            profile = await client.get_user_profile()

        assert profile.username == "alice"
        assert client._jwt_token == "refreshed_token"

    # ==================== LABEL MANAGEMENT TESTS ====================

    @pytest.mark.asyncio
    async def test_get_labels_success(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test fetching all labels."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            json={
                "res": [
                    {"id": 1, "name": "cleaning", "color": "#FF5733"},
                    {"id": 2, "name": "outdoor", "color": "#33FF57"},
                ]
            },
        )

        async with client:
            labels = await client.get_labels()

        assert len(labels) == 2
        assert labels[0].name == "cleaning"
        assert labels[0].color == "#FF5733"
        assert labels[1].name == "outdoor"

    @pytest.mark.asyncio
    async def test_get_labels_empty(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test fetching labels when none exist."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            json={"res": []},
        )

        async with client:
            labels = await client.get_labels()

        assert len(labels) == 0

    @pytest.mark.asyncio
    async def test_create_label_success(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test creating new label."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            json={"res": {"id": 1, "name": "urgent", "color": "#FF0000"}},
            method="POST",
        )

        async with client:
            label = await client.create_label("urgent", "#FF0000")

        assert label.id == 1
        assert label.name == "urgent"
        assert label.color == "#FF0000"

    @pytest.mark.asyncio
    async def test_create_label_no_color(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test creating label without color."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            json={"res": {"id": 2, "name": "daily", "color": None}},
            method="POST",
        )

        async with client:
            label = await client.create_label("daily")

        assert label.id == 2
        assert label.name == "daily"
        assert label.color is None

    @pytest.mark.asyncio
    async def test_create_label_duplicate_name(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test creating label with duplicate name."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            status_code=409,
            json={"error": "Label already exists"},
            method="POST",
        )

        async with client:
            with pytest.raises(Exception):
                await client.create_label("cleaning")

    @pytest.mark.asyncio
    async def test_update_label_success(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test updating existing label."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            json={"res": {"id": 1, "name": "super urgent", "color": "#FF0000"}},
            method="PUT",
        )

        async with client:
            label = await client.update_label(1, "super urgent", "#FF0000")

        assert label.id == 1
        assert label.name == "super urgent"

    @pytest.mark.asyncio
    async def test_update_label_not_found(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test updating non-existent label."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            status_code=404,
            json={"error": "Label not found"},
            method="PUT",
        )

        async with client:
            with pytest.raises(Exception):
                await client.update_label(999, "nonexistent")

    @pytest.mark.asyncio
    async def test_delete_label_success(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test deleting label."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels/1",
            json={},
            method="DELETE",
        )

        async with client:
            result = await client.delete_label(1)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_label_in_use(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test deleting label that's in use."""
        # Some APIs may succeed with warning, others may return error
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels/1",
            json={"warning": "Label is in use by some chores"},
            method="DELETE",
        )

        async with client:
            result = await client.delete_label(1)

        assert result is True

    @pytest.mark.asyncio
    async def test_lookup_label_ids_all_found(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test label lookup when all labels exist."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            json={
                "res": [
                    {"id": 1, "name": "cleaning", "color": "#FF5733"},
                    {"id": 2, "name": "outdoor", "color": "#33FF57"},
                    {"id": 3, "name": "urgent", "color": "#FF0000"},
                ]
            },
        )

        async with client:
            label_map = await client.lookup_label_ids(["cleaning", "outdoor"])

        assert label_map == {"cleaning": 1, "outdoor": 2}

    @pytest.mark.asyncio
    async def test_lookup_label_ids_partial_match(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test label lookup with some missing."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            json={
                "res": [
                    {"id": 1, "name": "cleaning", "color": "#FF5733"},
                ]
            },
        )

        async with client:
            label_map = await client.lookup_label_ids(["cleaning", "nonexistent"])

        assert label_map == {"cleaning": 1}
        assert "nonexistent" not in label_map

    @pytest.mark.asyncio
    async def test_lookup_label_ids_none_found(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test label lookup when no labels exist."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            json={"res": []},
        )

        async with client:
            label_map = await client.lookup_label_ids(["nonexistent1", "nonexistent2"])

        assert label_map == {}

    @pytest.mark.asyncio
    async def test_lookup_label_ids_empty_input(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test label lookup with empty array."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            json={"res": []},
        )

        async with client:
            label_map = await client.lookup_label_ids([])

        assert label_map == {}

    @pytest.mark.asyncio
    async def test_lookup_label_ids_case_insensitive(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test label lookup is case-insensitive."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            json={
                "res": [
                    {"id": 1, "name": "Cleaning", "color": "#FF5733"},
                    {"id": 2, "name": "OUTDOOR", "color": "#33FF57"},
                ]
            },
        )

        async with client:
            # Test case-insensitive matching with different cases
            label_map = await client.lookup_label_ids(["cleaning", "outdoor"])

        # Should match case-insensitively
        # "cleaning" matches "Cleaning" and "outdoor" matches "OUTDOOR"
        assert label_map["cleaning"] == 1
        assert label_map["outdoor"] == 2
        assert len(label_map) == 2

    # ==================== CIRCLE MEMBERS TESTS ====================

    @pytest.mark.asyncio
    async def test_get_circle_members_success(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test fetching circle members."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/circles/members/",
            json={
                "res": [
                    {
                        "id": 1,
                        "userId": 10,
                        "circleId": 5,
                        "role": "admin",
                        "isActive": True,
                        "username": "alice",
                        "displayName": "Alice Smith",
                        "points": 100,
                        "pointsRedeemed": 20,
                    },
                    {
                        "id": 2,
                        "userId": 11,
                        "circleId": 5,
                        "role": "member",
                        "isActive": True,
                        "username": "bob",
                        "displayName": "Bob Jones",
                        "points": 50,
                        "pointsRedeemed": 0,
                    },
                ]
            },
        )

        async with client:
            members = await client.get_circle_members()

        assert len(members) == 2
        assert members[0].username == "alice"
        assert members[0].role == "admin"
        assert members[0].points == 100
        assert members[1].username == "bob"

    @pytest.mark.asyncio
    async def test_get_circle_members_empty(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test handling empty circle."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/circles/members/",
            json={"res": []},
        )

        async with client:
            members = await client.get_circle_members()

        assert len(members) == 0

    @pytest.mark.asyncio
    async def test_lookup_user_ids_validation(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test username lookup with validation."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/circles/members/",
            json={
                "res": [
                    {
                        "id": 1,
                        "userId": 10,
                        "circleId": 5,
                        "role": "admin",
                        "isActive": True,
                        "username": "alice",
                        "displayName": "Alice Smith",
                        "points": 100,
                    },
                    {
                        "id": 2,
                        "userId": 11,
                        "circleId": 5,
                        "role": "member",
                        "isActive": True,
                        "username": "bob",
                        "displayName": "Bob Jones",
                        "points": 50,
                    },
                ]
            },
        )

        async with client:
            user_map = await client.lookup_user_ids(["alice", "Bob Jones", "nonexistent"])

        # Should match username and displayName (case-insensitive)
        assert user_map["alice"] == 10
        assert user_map["Bob Jones"] == 11
        assert "nonexistent" not in user_map

    # ==================== TRANSFORMATION FUNCTION TESTS ====================

    def test_transform_frequency_metadata_invalid_days(self, client):
        """Test frequency transform with invalid day names."""
        with pytest.raises(ValueError, match="Invalid day name"):
            client.transform_frequency_metadata(
                "days_of_the_week",
                days_of_week=["Mon", "InvalidDay", "Fri"],
            )

    def test_transform_frequency_metadata_empty_days(self, client):
        """Test frequency transform with empty days array."""
        with pytest.raises(ValueError, match="days_of_week parameter is required"):
            client.transform_frequency_metadata(
                "days_of_the_week",
                days_of_week=[],
            )

    def test_transform_frequency_metadata_mixed_case(self, client):
        """Test day name normalization (Mon, monday, MONDAY)."""
        metadata = client.transform_frequency_metadata(
            "days_of_the_week",
            days_of_week=["Mon", "WEDNESDAY", "friday"],
        )

        # All should be normalized to lowercase full names
        assert metadata["days"] == ["monday", "wednesday", "friday"]
        assert metadata["weekPattern"] == "every_week"
        assert metadata["occurrences"] == []
        assert metadata["weekNumbers"] == []

    def test_transform_frequency_metadata_with_time(self, client):
        """Test frequency transform with time component."""
        metadata = client.transform_frequency_metadata(
            "days_of_the_week",
            days_of_week=["Mon", "Wed"],
            time="14:30",
            timezone="America/New_York",
        )

        assert "days" in metadata
        assert "time" in metadata
        assert "T" in metadata["time"]  # Should be ISO format

    def test_transform_notification_metadata_max_templates(self, client):
        """Test notification with multiple templates."""
        metadata = client.transform_notification_metadata(
            offset_minutes=-30,
            remind_at_due_time=True,
            nagging=True,
            predue=True,
        )

        assert metadata["nagging"] is True
        assert metadata["predue"] is True
        assert "templates" in metadata
        assert len(metadata["templates"]) == 2  # offset + due time

    def test_calculate_due_date_edge_cases(self, client):
        """Test due date calculation with edge cases."""
        # Test "once" frequency type
        due_date = client.calculate_due_date(
            "once",
            {},
            timezone="America/New_York",
        )

        # Should be in RFC3339 format
        assert "T" in due_date
        assert due_date.endswith("Z")

    # ==================== ERROR HANDLING TESTS ====================

    @pytest.mark.asyncio
    async def test_json_decode_error_handling(self, client, httpx_mock: HTTPXMock, mock_login):
        """Test handling malformed JSON response."""
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            content=b"Invalid JSON{{{",
            headers={"Content-Type": "application/json"},
        )

        async with client:
            with pytest.raises(ValueError, match="Invalid JSON"):
                await client.list_chores()

    @pytest.mark.asyncio
    async def test_timeout_with_retry(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test timeout retry with exponential backoff."""
        import httpx

        # First two attempts timeout
        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))
        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))
        # Third attempt succeeds
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json=[sample_chore_data],
        )

        async with client:
            chores = await client.list_chores()

        assert len(chores) == 1

    @pytest.mark.asyncio
    async def test_5xx_error_retry(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test retry on 500/502/503 errors."""
        # First attempt returns 500
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            status_code=500,
            json={"error": "Internal server error"},
        )
        # Second attempt succeeds
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json=[sample_chore_data],
        )

        async with client:
            chores = await client.list_chores()

        assert len(chores) == 1

    @pytest.mark.asyncio
    async def test_get_chore_history(self, httpx_mock: HTTPXMock, mock_login):
        """Test getting chore history."""
        history_data = [
            {
                "id": 1,
                "choreId": 123,
                
                "performedAt": "2025-11-05T10:00:00Z",
                "completedBy": 1,
                "note": "Completed successfully",
                "assignedTo": 1,
                "dueDate": "2025-11-05T00:00:00Z",
            },
            {
                "id": 2,
                "choreId": 123,
                
                "performedAt": "2025-11-04T10:00:00Z",
                "completedBy": 1,
                "note": None,
                "assignedTo": 1,
                "dueDate": "2025-11-04T00:00:00Z",
            },
        ]

        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/123/history",
            json={"res": history_data},
        )

        client = DonetickClient(
            base_url="https://test.donetick.com",
            username="test",
            password="test",
        )

        async with client:
            history = await client.get_chore_history(123)

            assert len(history) == 2
            assert history[0].id == 1
            assert history[0].choreId == 123
            assert history[0].completedBy == 1  # User ID (integer), not username
            assert history[0].note == "Completed successfully"
            assert history[1].id == 2
            assert history[1].note is None

    @pytest.mark.asyncio
    async def test_get_all_chores_history(self, httpx_mock: HTTPXMock, mock_login):
        """Test getting all chores history with pagination."""
        history_data = [
            {
                "id": 1,
                "choreId": 123,
                # Note: choreName does NOT exist in ChoreHistory model
                "performedAt": "2025-11-05T10:00:00Z",
                "completedBy": 1,  # User ID (integer)
                "note": None,
                "assignedTo": 1,
                "dueDate": "2025-11-05T00:00:00Z",
            },
            {
                "id": 2,
                "choreId": 124,
                "performedAt": "2025-11-04T10:00:00Z",
                "completedBy": 2,  # User ID (integer)
                "note": None,
                "assignedTo": 2,
                "dueDate": "2025-11-04T00:00:00Z",
            },
        ]

        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/history?limit=10&offset=5",
            json={"res": history_data},
        )

        client = DonetickClient(
            base_url="https://test.donetick.com",
            username="test",
            password="test",
        )

        async with client:
            history = await client.get_all_chores_history(limit=10, offset=5)

            assert len(history) == 2
            assert history[0].choreId == 123
            assert history[0].completedBy == 1
            assert history[1].choreId == 124
            assert history[1].completedBy == 2

    @pytest.mark.asyncio
    async def test_get_chore_details(self, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test getting chore details with statistics."""
        history_entry = {
            "id": 1,
            "choreId": 123,
            
            "performedAt": "2025-11-05T10:00:00Z",
            "completedBy": 1,
            "note": None,
            "assignedTo": 1,
            "dueDate": "2025-11-05T00:00:00Z",
        }

        details_data = {
            **sample_chore_data,
            "id": 123,
            "name": "Detailed Test Chore",
            "totalCompletedCount": 5,
            "lastCompletedDate": "2025-11-05T10:00:00Z",
            "lastCompletedBy": 1,  # User ID (integer), not username
            "averageDuration": 9000.5,  # Seconds (float), not "2h 30m" string
            "completionHistory": [history_entry],  # Field name is completionHistory, not history
        }

        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/123/details",
            json={"res": details_data},
        )

        client = DonetickClient(
            base_url="https://test.donetick.com",
            username="test",
            password="test",
        )

        async with client:
            details = await client.get_chore_details(123)

            assert details.id == 123
            assert details.name == "Detailed Test Chore"
            assert details.totalCompletedCount == 5
            assert details.lastCompletedDate == "2025-11-05T10:00:00Z"
            assert details.lastCompletedBy == 1  # User ID (integer)
            assert details.averageDuration == 9000.5  # Seconds (float)
            assert len(details.completionHistory) == 1
            assert details.completionHistory[0].completedBy == 1  # User ID (integer)
