"""
End-to-end integration tests for workflow scenarios.

Tests realistic user workflows that span multiple API operations:
- Complete chore lifecycle (create, get, update, complete, delete)
- Label management workflow (create label, use in chore, delete)
- User lookup and assignment workflow (lookup users, assign chores)
"""

import pytest
from pytest_httpx import HTTPXMock

from donetick_mcp.client import DonetickClient
from donetick_mcp.models import ChoreCreate


@pytest.fixture
def client():
    """Create a test client instance with high rate limit for fast tests."""
    return DonetickClient(
        base_url="https://test.donetick.com",
        username="test_user",
        password="test_password",
        rate_limit_per_second=100.0,
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


class TestFullChoreLifecycle:
    """Test the complete lifecycle of a chore from creation to deletion."""

    @pytest.mark.asyncio
    async def test_full_chore_lifecycle(self, client, httpx_mock: HTTPXMock, mock_login):
        """
        Test complete chore lifecycle: Create -> Get -> Update -> Complete -> Delete.

        This workflow simulates a typical user journey:
        1. Create a new chore with minimal fields
        2. Retrieve the chore to verify creation
        3. Update the chore with new details
        4. Mark the chore as complete
        5. Delete the chore
        6. Verify the chore is gone

        All operations use realistic API responses and test data flow between steps.
        """
        # STEP 1: Create chore
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json={"res": 1},
            method="POST",
        )
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json={
                "id": 1,
                "name": "Vacuum Living Room",
                "description": "Clean the carpets",
                "frequencyType": "weekly",
                "frequency": 1,
                "isActive": True,
                "nextDueDate": "2025-11-10T00:00:00Z",
                "circleId": 1,
                "createdAt": "2025-11-03T00:00:00Z",
                "updatedAt": "2025-11-03T00:00:00Z",
                "createdBy": 1,
            },
        )

        async with client:
            chore_create = ChoreCreate(
                name="Vacuum Living Room",
                description="Clean the carpets",
                dueDate="2025-11-10",
            )
            created_chore = await client.create_chore(chore_create)

            assert created_chore.id == 1
            assert created_chore.name == "Vacuum Living Room"
            assert created_chore.description == "Clean the carpets"

            # STEP 2: Get chore to verify
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/1",
                json={
                    "id": 1,
                    "name": "Vacuum Living Room",
                    "description": "Clean the carpets",
                    "frequencyType": "weekly",
                    "frequency": 1,
                    "isActive": True,
                    "nextDueDate": "2025-11-10T00:00:00Z",
                    "priority": 2,
                    "circleId": 1,
                    "createdAt": "2025-11-03T00:00:00Z",
                    "updatedAt": "2025-11-03T00:00:00Z",
                    "createdBy": 1,
                },
            )

            # Clear cache to force fresh fetch
            client.clear_cache()
            fetched_chore = await client.get_chore(1)

            assert fetched_chore is not None
            assert fetched_chore.id == 1
            assert fetched_chore.name == "Vacuum Living Room"

            # STEP 3: Update chore (Premium feature)
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/1",
                json={
                    "id": 1,
                    "name": "Vacuum Living Room",
                    "description": "Clean carpets thoroughly with vacuum attachment",
                    "frequencyType": "weekly",
                    "frequency": 1,
                    "isActive": True,
                    "nextDueDate": "2025-11-10T00:00:00Z",
                    "priority": 3,
                    "circleId": 1,
                    "createdAt": "2025-11-03T00:00:00Z",
                    "updatedAt": "2025-11-03T00:00:00Z",
                    "createdBy": 1,
                },
                method="PUT",
            )

            from donetick_mcp.models import ChoreUpdate
            chore_update = ChoreUpdate(
                description="Clean carpets thoroughly with vacuum attachment",
                priority=3,
            )
            updated_chore = await client.update_chore(1, chore_update)

            assert updated_chore.id == 1
            assert updated_chore.description == "Clean carpets thoroughly with vacuum attachment"
            assert updated_chore.priority == 3

            # STEP 4: Complete chore (Premium feature)
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/1/do",
                json={
                    "id": 1,
                    "name": "Vacuum Living Room",
                    "description": "Clean carpets thoroughly with vacuum attachment",
                    "frequencyType": "weekly",
                    "frequency": 1,
                    "isActive": True,
                    "nextDueDate": "2025-11-17T00:00:00Z",  # Next week
                    "priority": 3,
                    "circleId": 1,
                    "createdAt": "2025-11-03T00:00:00Z",
                    "updatedAt": "2025-11-03T00:00:00Z",
                    "createdBy": 1,
                },
                method="POST",
            )

            completed_chore = await client.complete_chore(1)

            assert completed_chore.id == 1
            assert completed_chore.nextDueDate == "2025-11-17T00:00:00Z"

            # STEP 5: Delete chore
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/1",
                json={},
                method="DELETE",
            )

            delete_result = await client.delete_chore(1)
            assert delete_result is True

            # STEP 6: Verify chore is gone
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/1",
                status_code=404,
            )

            # Clear cache to force fresh fetch
            client.clear_cache()
            deleted_chore = await client.get_chore(1)

            assert deleted_chore is None


class TestLabelWorkflow:
    """Test label creation, usage in chores, and cleanup."""

    @pytest.mark.asyncio
    async def test_label_workflow(self, client, httpx_mock: HTTPXMock, mock_login):
        """
        Test label workflow: Create label -> Use in chore -> Delete label -> Verify cleanup.

        This workflow tests:
        1. Create a new label with name and color
        2. Create a chore that uses the label
        3. Verify the label appears in the chore
        4. Delete the label
        5. Verify chore handles orphaned label gracefully (label removed from chore)

        Tests the integration between label and chore management.
        """
        async with client:
            # STEP 1: Create label
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/labels",
                json={"res": {"id": 10, "name": "urgent", "color": "#FF0000"}},
                method="POST",
            )

            label = await client.create_label("urgent", "#FF0000")

            assert label.id == 10
            assert label.name == "urgent"
            assert label.color == "#FF0000"

            # STEP 2: Create chore with label
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/",
                json={"res": 5},
                method="POST",
            )
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/5",
                json={
                    "id": 5,
                    "name": "Fix Leaky Faucet",
                    "description": "Emergency plumbing repair",
                    "frequencyType": "once",
                    "frequency": 0,
                    "isActive": True,
                    "nextDueDate": "2025-11-05T00:00:00Z",
                    "circleId": 1,
                    "createdAt": "2025-11-03T00:00:00Z",
                    "updatedAt": "2025-11-03T00:00:00Z",
                    "labelsV2": [
                        {"id": 10, "name": "urgent", "color": "#FF0000"}
                    ],
                    "createdBy": 1,
                },
            )

            chore_create = ChoreCreate(
                name="Fix Leaky Faucet",
                description="Emergency plumbing repair",
                dueDate="2025-11-05",
                labelIds=[10],  # Use the label we created
            )
            chore = await client.create_chore(chore_create)

            assert chore.id == 5
            assert chore.name == "Fix Leaky Faucet"
            assert len(chore.labelsV2) == 1
            assert chore.labelsV2[0].id == 10
            assert chore.labelsV2[0].name == "urgent"

            # STEP 3: Verify label in chore
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/5",
                json={
                    "id": 5,
                    "name": "Fix Leaky Faucet",
                    "description": "Emergency plumbing repair",
                    "frequencyType": "once",
                    "frequency": 0,
                    "isActive": True,
                    "nextDueDate": "2025-11-05T00:00:00Z",
                    "circleId": 1,
                    "createdAt": "2025-11-03T00:00:00Z",
                    "updatedAt": "2025-11-03T00:00:00Z",
                    "labelsV2": [
                        {"id": 10, "name": "urgent", "color": "#FF0000"}
                    ],
                    "createdBy": 1,
                },
            )

            # Clear cache to force fresh fetch
            client.clear_cache()
            fetched_chore = await client.get_chore(5)

            assert fetched_chore is not None
            assert len(fetched_chore.labelsV2) == 1
            assert fetched_chore.labelsV2[0].name == "urgent"

            # STEP 4: Delete label
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/labels/10",
                json={},
                method="DELETE",
            )

            delete_result = await client.delete_label(10)
            assert delete_result is True

            # STEP 5: Verify chore handles orphaned label gracefully
            # In real API, the label would be removed from the chore
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/5",
                json={
                    "id": 5,
                    "name": "Fix Leaky Faucet",
                    "description": "Emergency plumbing repair",
                    "frequencyType": "once",
                    "frequency": 0,
                    "isActive": True,
                    "nextDueDate": "2025-11-05T00:00:00Z",
                    "circleId": 1,
                    "createdAt": "2025-11-03T00:00:00Z",
                    "updatedAt": "2025-11-03T00:00:00Z",
                    "labelsV2": [],  # Label removed after deletion
                    "createdBy": 1,
                },
            )

            # Clear cache to force fresh fetch
            client.clear_cache()
            chore_after_delete = await client.get_chore(5)

            assert chore_after_delete is not None
            assert len(chore_after_delete.labelsV2) == 0


class TestUserLookupAndAssignment:
    """Test user lookup and chore assignment workflows."""

    @pytest.mark.asyncio
    async def test_user_lookup_and_assignment(self, client, httpx_mock: HTTPXMock, mock_login):
        """
        Test user lookup and assignment: Lookup users -> Assign to chore -> Verify assignment.

        This workflow tests:
        1. Lookup users by username using circle members API
        2. Create a chore assigned to specific users
        3. Verify the assignment in the created chore
        4. Test rotation with assignment strategy

        Tests the integration between user management and chore assignment.
        """
        async with client:
            # STEP 1: Lookup users from circle
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/circles/members",
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
                        {
                            "id": 3,
                            "userId": 12,
                            "circleId": 5,
                            "role": "member",
                            "isActive": True,
                            "username": "charlie",
                            "displayName": "Charlie Brown",
                            "points": 75,
                        },
                    ]
                },
            )

            # Lookup user IDs by username
            user_map = await client.lookup_user_ids(["alice", "Bob Jones"])

            assert "alice" in user_map
            assert user_map["alice"] == 10
            assert "Bob Jones" in user_map
            assert user_map["Bob Jones"] == 11

            # STEP 2: Create chore with multiple assignees
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/",
                json={"res": 20},
                method="POST",
            )
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/20",
                json={
                    "id": 20,
                    "name": "Weekly Grocery Shopping",
                    "description": "Buy groceries for the week",
                    "frequencyType": "weekly",
                    "frequency": 1,
                    "isActive": True,
                    "nextDueDate": "2025-11-07T00:00:00Z",
                    "circleId": 5,
                    "createdAt": "2025-11-03T00:00:00Z",
                    "updatedAt": "2025-11-03T00:00:00Z",
                    "assignedTo": 10,  # Initially assigned to Alice
                    "assignees": [
                        {"userId": 10},
                        {"userId": 11},
                    ],
                    "assignStrategy": "round_robin",
                    "createdBy": 10,
                },
            )

            chore_create = ChoreCreate(
                name="Weekly Grocery Shopping",
                description="Buy groceries for the week",
                dueDate="2025-11-07",
                assignees=[
                    {"userId": 10},  # Alice
                    {"userId": 11},  # Bob
                ],
                assignStrategy="round_robin",
            )
            chore = await client.create_chore(chore_create)

            assert chore.id == 20
            assert chore.name == "Weekly Grocery Shopping"
            assert len(chore.assignees) == 2
            assert chore.assignees[0].userId == 10
            assert chore.assignees[1].userId == 11
            assert chore.assignStrategy == "round_robin"

            # STEP 3: Verify assignment after completion (should rotate to next user)
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/20/do",
                json={
                    "id": 20,
                    "name": "Weekly Grocery Shopping",
                    "description": "Buy groceries for the week",
                    "frequencyType": "weekly",
                    "frequency": 1,
                    "isActive": True,
                    "nextDueDate": "2025-11-14T00:00:00Z",
                    "circleId": 5,
                    "createdAt": "2025-11-03T00:00:00Z",
                    "updatedAt": "2025-11-03T00:00:00Z",
                    "assignedTo": 11,  # Rotated to Bob
                    "assignees": [
                        {"userId": 10},
                        {"userId": 11},
                    ],
                    "assignStrategy": "round_robin",
                    "createdBy": 10,
                },
                method="POST",
            )

            completed_chore = await client.complete_chore(20)

            # Verify rotation happened
            assert completed_chore.assignedTo == 11  # Now assigned to Bob
            assert completed_chore.nextDueDate == "2025-11-14T00:00:00Z"  # Next week

            # STEP 4: Test least_completed strategy
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/",
                json={"res": 21},
                method="POST",
            )
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/21",
                json={
                    "id": 21,
                    "name": "Take Out Trash",
                    "description": "Empty all trash bins",
                    "frequencyType": "daily",
                    "frequency": 1,
                    "isActive": True,
                    "nextDueDate": "2025-11-05T00:00:00Z",
                    "circleId": 5,
                    "createdAt": "2025-11-03T00:00:00Z",
                    "updatedAt": "2025-11-03T00:00:00Z",
                    "assignedTo": 11,  # Bob has fewer completions
                    "assignees": [
                        {"userId": 10},
                        {"userId": 11},
                    ],
                    "assignStrategy": "least_completed",
                    "createdBy": 10,
                },
            )

            chore_create_2 = ChoreCreate(
                name="Take Out Trash",
                description="Empty all trash bins",
                dueDate="2025-11-05",
                assignees=[
                    {"userId": 10},
                    {"userId": 11},
                ],
                assignStrategy="least_completed",
            )
            chore_2 = await client.create_chore(chore_create_2)

            assert chore_2.id == 21
            assert chore_2.assignStrategy == "least_completed"
            assert chore_2.assignedTo in [10, 11]  # Assigned to user with least completions
