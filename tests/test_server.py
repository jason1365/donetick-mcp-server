"""Integration tests for MCP server."""

import json

import pytest
from pytest_httpx import HTTPXMock

from donetick_mcp.server import app, get_client, list_tools, call_tool


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


class TestMCPServer:
    """Integration tests for MCP server tools."""

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available tools."""
        tools = await list_tools()

        assert len(tools) == 20  # 10 chore tools + 4 label tools + 3 user/member tools + 3 history tools
        tool_names = [tool.name for tool in tools]
        # Chore tools (10 total)
        assert "list_chores" in tool_names
        assert "get_chore" in tool_names
        assert "create_chore" in tool_names
        assert "complete_chore" in tool_names
        assert "update_chore" in tool_names
        assert "delete_chore" in tool_names
        assert "update_chore_priority" in tool_names
        assert "update_chore_assignee" in tool_names
        assert "skip_chore" in tool_names
        assert "update_subtask_completion" in tool_names
        # Label tools (4 total)
        assert "list_labels" in tool_names
        assert "create_label" in tool_names
        assert "update_label" in tool_names
        assert "delete_label" in tool_names
        # Member/user tools (3 total)
        assert "get_circle_members" in tool_names
        assert "list_circle_users" in tool_names
        assert "get_user_profile" in tool_names
        # History tools (3 total)
        assert "get_chore_history" in tool_names
        assert "get_all_chores_history" in tool_names
        assert "get_chore_details" in tool_names

    @pytest.mark.asyncio
    async def test_list_chores_tool(self, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test list_chores tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
            json=[sample_chore_data],
        )

        result = await call_tool("list_chores", {})

        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 1
        assert len(response_data["chores"]) == 1
        assert response_data["chores"][0]["name"] == "Test Chore"

    @pytest.mark.asyncio
    async def test_list_chores_with_filters(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test list_chores tool with filters."""
        inactive_chore = sample_chore_data.copy()
        inactive_chore["id"] = 2
        inactive_chore["isActive"] = False

        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
            json=[sample_chore_data, inactive_chore],
        )

        result = await call_tool("list_chores", {"filter_active": True})

        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 1

    @pytest.mark.asyncio
    async def test_list_chores_empty(self, httpx_mock: HTTPXMock):
        """Test list_chores tool with no results."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
            json=[],
        )

        result = await call_tool("list_chores", {})

        assert len(result) == 1
        assert "No chores found" in result[0].text

    @pytest.mark.asyncio
    async def test_get_chore_tool(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test get_chore tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1",
            json=sample_chore_data,
        )

        result = await call_tool("get_chore", {"chore_id": 1})

        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 1
        assert response_data["name"] == "Test Chore"

    @pytest.mark.asyncio
    async def test_get_chore_not_found(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test get_chore tool with non-existent ID."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/999",
            status_code=404,
        )

        result = await call_tool("get_chore", {"chore_id": 999})

        assert len(result) == 1
        assert "not found" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_create_chore_tool(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test create_chore tool execution."""
        # Mock POST response (API returns {'res': chore_id})
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
            json={"res": 1},
            method="POST",
        )
        # Mock GET response for fetching created chore
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1",
            json=sample_chore_data,
            method="GET",
        )

        result = await call_tool(
            "create_chore",
            {
                "name": "Test Chore",
                "description": "Test description",
                "due_date": "2025-11-10",
            },
        )

        assert len(result) == 1
        assert "Successfully created" in result[0].text
        assert "Test Chore" in result[0].text

    @pytest.mark.asyncio
    async def test_create_chore_minimal(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test create_chore tool with only required fields."""
        # Mock POST response (API returns {'res': chore_id})
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
            json={"res": 1},
            method="POST",
        )
        # Mock GET response for fetching created chore
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1",
            json=sample_chore_data,
            method="GET",
        )

        result = await call_tool("create_chore", {"name": "Test Chore"})

        assert len(result) == 1
        assert "Successfully created" in result[0].text

    @pytest.mark.asyncio
    async def test_complete_chore_tool(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test complete_chore tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1/do",
            json=sample_chore_data,
            method="POST",
        )

        result = await call_tool("complete_chore", {"chore_id": 1})

        assert len(result) == 1
        assert "Successfully completed" in result[0].text
        assert "Test Chore" in result[0].text

    @pytest.mark.asyncio
    async def test_complete_chore_with_user(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test complete_chore tool with completed_by parameter."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1/do?completedBy=2",
            json=sample_chore_data,
            method="POST",
        )

        result = await call_tool("complete_chore", {"chore_id": 1, "completed_by": 2})

        assert len(result) == 1
        assert "Successfully completed" in result[0].text

    @pytest.mark.asyncio
    async def test_delete_chore_tool(self, httpx_mock: HTTPXMock):
        """Test delete_chore tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1",
            json={},
            method="DELETE",
        )

        result = await call_tool("delete_chore", {"chore_id": 1})

        assert len(result) == 1
        assert "Successfully deleted" in result[0].text

    @pytest.mark.asyncio
    async def test_update_chore_priority_tool(self, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test update_chore_priority tool execution."""
        updated_chore = {**sample_chore_data, "priority": 4}
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1/priority",
            json=updated_chore,
            method="PUT",
        )

        result = await call_tool("update_chore_priority", {"chore_id": 1, "priority": 4})

        assert len(result) == 1
        assert "Successfully updated" in result[0].text
        assert "priority to 4" in result[0].text

    @pytest.mark.asyncio
    async def test_update_chore_priority_validation(self, httpx_mock: HTTPXMock):
        """Test update_chore_priority with invalid priority."""
        result = await call_tool("update_chore_priority", {"chore_id": 1, "priority": 5})

        assert len(result) == 1
        assert "Error" in result[0].text or "must be 0-4" in result[0].text

    @pytest.mark.asyncio
    async def test_update_chore_assignee_tool(self, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test update_chore_assignee tool execution."""
        # Mock GET to fetch current chore (fetch-modify-send pattern)
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1",
            json={"res": sample_chore_data},
            method="GET",
        )
        # Mock PUT to update chore
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
            json={"message": "Chore added successfully"},
            method="PUT",
        )
        # Mock GET to fetch updated chore
        updated_chore = {**sample_chore_data, "assignedTo": 2, "assignees": [{"userId": 2}]}
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1",
            json={"res": updated_chore},
            method="GET",
        )

        result = await call_tool("update_chore_assignee", {"chore_id": 1, "user_id": 2})

        assert len(result) == 1
        assert "Successfully reassigned" in result[0].text
        assert "user 2" in result[0].text

    @pytest.mark.asyncio
    async def test_skip_chore_tool(self, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test skip_chore tool execution."""
        # For a recurring chore, skip schedules next occurrence
        updated_chore = {**sample_chore_data, "nextDueDate": "2025-11-17"}
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1/skip",
            json=updated_chore,
            method="POST",
        )

        result = await call_tool("skip_chore", {"chore_id": 1})

        assert len(result) == 1
        assert "Successfully skipped" in result[0].text
        assert "next due date" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, httpx_mock: HTTPXMock):
        """Test error handling in tools."""
        # Mock 3 retries for 500 error (client retries 3 times total)
        for _ in range(3):
            httpx_mock.add_response(
                url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
                status_code=500,
                json={"error": "Internal server error"},
                method="GET",
            )

        result = await call_tool("list_chores", {})

        assert len(result) == 1
        assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test calling an unknown tool."""
        result = await call_tool("unknown_tool", {})

        assert len(result) == 1
        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test handling concurrent tool calls."""
        import asyncio

        # Mock multiple responses
        for _ in range(3):
            httpx_mock.add_response(
                url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
                json=[sample_chore_data],
            )

        # Launch concurrent tool calls
        tasks = [call_tool("list_chores", {}) for _ in range(3)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 3
        assert all(len(r) == 1 for r in results)

    # ======================
    # LABEL TOOL TESTS (8 tests)
    # ======================

    @pytest.mark.asyncio
    async def test_list_labels_tool(self, httpx_mock: HTTPXMock, mock_login):
        """Test list_labels tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/labels",
            json=[
                {"id": 1, "name": "cleaning", "color": "#80d8ff"},
                {"id": 2, "name": "urgent", "color": "#ff5733"},
            ],
        )

        result = await call_tool("list_labels", {})

        assert len(result) == 1
        assert "Available Labels:" in result[0].text
        assert "cleaning" in result[0].text
        assert "urgent" in result[0].text
        assert "#80d8ff" in result[0].text

    @pytest.mark.asyncio
    async def test_list_labels_empty(self, httpx_mock: HTTPXMock, mock_login):
        """Test list_labels tool with no labels."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/labels",
            json=[],
        )

        result = await call_tool("list_labels", {})

        assert len(result) == 1
        assert "No labels found" in result[0].text

    @pytest.mark.asyncio
    async def test_create_label_tool(self, httpx_mock: HTTPXMock, mock_login):
        """Test create_label tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/labels",
            json={"id": 1, "name": "outdoor", "color": "#4caf50"},
            method="POST",
        )

        result = await call_tool("create_label", {"name": "outdoor", "color": "#4caf50"})

        assert len(result) == 1
        assert "Successfully created label 'outdoor'" in result[0].text
        assert "ID: 1" in result[0].text
        assert "#4caf50" in result[0].text

    @pytest.mark.asyncio
    async def test_create_label_invalid_color(self, httpx_mock: HTTPXMock, mock_login):
        """Test create_label tool with invalid color format."""
        # API rejects with 422 validation error
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/labels",
            status_code=422,
            json={"error": "Invalid color format"},
            method="POST",
        )

        result = await call_tool("create_label", {"name": "test", "color": "invalid"})

        assert len(result) == 1
        assert "Validation error" in result[0].text
        assert "422" not in result[0].text  # Should be user-friendly, not show status code

    @pytest.mark.asyncio
    async def test_update_label_tool(self, httpx_mock: HTTPXMock, mock_login):
        """Test update_label tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/labels",
            json={"res": {"id": 1, "name": "deep-cleaning", "color": "#00bcd4"}},
            method="PUT",
        )

        result = await call_tool("update_label", {"label_id": 1, "name": "deep-cleaning", "color": "#00bcd4"})

        assert len(result) == 1
        assert "Successfully updated label ID 1" in result[0].text
        assert "deep-cleaning" in result[0].text

    @pytest.mark.asyncio
    async def test_update_label_not_found(self, httpx_mock: HTTPXMock, mock_login):
        """Test update_label tool with non-existent label."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/labels",
            status_code=404,
            method="PUT",
        )

        result = await call_tool("update_label", {"label_id": 999, "name": "test"})

        assert len(result) == 1
        assert "Label not found" in result[0].text
        assert "list_labels" in result[0].text  # Helpful hint

    @pytest.mark.asyncio
    async def test_delete_label_tool(self, httpx_mock: HTTPXMock, mock_login):
        """Test delete_label tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/labels/1",
            json={},
            method="DELETE",
        )

        result = await call_tool("delete_label", {"label_id": 1})

        assert len(result) == 1
        assert "Successfully deleted label with ID 1" in result[0].text

    @pytest.mark.asyncio
    async def test_delete_label_not_found(self, httpx_mock: HTTPXMock, mock_login):
        """Test delete_label tool with non-existent label."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/labels/999",
            status_code=404,
            method="DELETE",
        )

        result = await call_tool("delete_label", {"label_id": 999})

        assert len(result) == 1
        assert "Label not found" in result[0].text

    # ======================
    # USER/MEMBER TOOL TESTS (6 tests)
    # ======================

    @pytest.mark.asyncio
    async def test_get_circle_members_tool(self, httpx_mock: HTTPXMock, mock_login):
        """Test get_circle_members tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/circles/members/",
            json=[
                {
                    "id": 1,
                    "userId": 1,
                    "circleId": 1,
                    "role": "admin",
                    "isActive": True,
                    "username": "alice",
                    "displayName": "Alice Smith",
                    "points": 150,
                    "pointsRedeemed": 50,
                },
                {
                    "id": 2,
                    "userId": 2,
                    "circleId": 1,
                    "role": "member",
                    "isActive": True,
                    "username": "bob",
                    "displayName": "Bob Jones",
                    "points": 80,
                    "pointsRedeemed": 20,
                },
            ],
        )

        result = await call_tool("get_circle_members", {})

        assert len(result) == 1
        assert "Found 2 member(s)" in result[0].text
        assert "alice" in result[0].text
        assert "bob" in result[0].text

    @pytest.mark.asyncio
    async def test_get_circle_members_formatting(self, httpx_mock: HTTPXMock, mock_login):
        """Test get_circle_members tool output formatting."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/circles/members/",
            json=[
                {
                    "id": 1,
                    "userId": 1,
                    "circleId": 1,
                    "role": "admin",
                    "isActive": True,
                    "username": "alice",
                    "displayName": "Alice Admin",
                    "points": 100,
                    "pointsRedeemed": 25,
                },
            ],
        )

        result = await call_tool("get_circle_members", {})

        assert len(result) == 1
        response = result[0].text
        # Check for formatted output elements
        assert "User ID: 1" in response
        assert "Display Name: Alice Admin" in response
        assert "Role: admin" in response
        assert "Points: 100" in response
        assert "Redeemed: 25" in response
        # Check for emojis indicating role and status
        assert "👑" in response  # Admin role emoji
        assert "✅" in response  # Active status emoji

    @pytest.mark.asyncio
    async def test_list_circle_users_tool(self, httpx_mock: HTTPXMock, mock_login):
        """Test list_circle_users tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/users/",
            json=[
                {
                    "id": 1,
                    "username": "alice",
                    "displayName": "Alice Smith",
                    "email": "alice@example.com",
                    "role": "admin",
                    "points": 200,
                    "pointsRedeemed": 50,
                    "isActive": True,
                },
                {
                    "id": 2,
                    "username": "bob",
                    "displayName": "Bob Jones",
                    "email": "bob@example.com",
                    "role": "member",
                    "points": 100,
                    "pointsRedeemed": 20,
                    "isActive": True,
                },
            ],
        )

        result = await call_tool("list_circle_users", {})

        assert len(result) == 1
        assert "Found 2 user(s)" in result[0].text
        assert "alice" in result[0].text
        assert "bob@example.com" in result[0].text

    @pytest.mark.asyncio
    async def test_list_circle_users_empty(self, httpx_mock: HTTPXMock, mock_login):
        """Test list_circle_users tool with no users."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/users/",
            json=[],
        )

        result = await call_tool("list_circle_users", {})

        assert len(result) == 1
        assert "Found 0 user(s)" in result[0].text

    @pytest.mark.asyncio
    async def test_get_user_profile_tool(self, httpx_mock: HTTPXMock, mock_login):
        """Test get_user_profile tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/users/profile",
            json={
                "id": 1,
                "username": "testuser",
                "displayName": "Test User",
                "email": "test@example.com",
                "isActive": True,
                "points": 250,
                "pointsRedeemed": 75,
                "storageUsed": 10485760,  # 10MB in bytes
                "storageLimit": 104857600,  # 100MB in bytes
                "webhook": "https://webhook.example.com",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-11-01T00:00:00Z",
            },
        )

        result = await call_tool("get_user_profile", {})

        assert len(result) == 1
        assert "testuser" in result[0].text
        assert "Test User" in result[0].text
        assert "test@example.com" in result[0].text

    @pytest.mark.asyncio
    async def test_get_user_profile_formatting(self, httpx_mock: HTTPXMock, mock_login):
        """Test get_user_profile tool output formatting."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/users/profile",
            json={
                "id": 1,
                "username": "alice",
                "displayName": "Alice Admin",
                "email": "alice@example.com",
                "isActive": True,
                "points": 300,
                "pointsRedeemed": 100,
                "storageUsed": 52428800,  # 50MB
                "storageLimit": 104857600,  # 100MB
                "webhook": "https://webhook.example.com",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-11-04T00:00:00Z",
            },
        )

        result = await call_tool("get_user_profile", {})

        assert len(result) == 1
        response = result[0].text
        # Check sections
        assert "User Profile for alice" in response
        assert "Basic Information:" in response
        assert "Gamification:" in response
        assert "Storage:" in response
        assert "Notifications:" in response
        # Check calculated values
        assert "Net Points: 200" in response  # 300 - 100
        assert "50.00 MB" in response  # Storage used
        assert "50.00 MB" in response  # Available storage (100-50)
        # Check emojis for better formatting
        assert "👤" in response
        assert "🏆" in response
        assert "💾" in response
        assert "🔔" in response

    # ======================
    # COMPLEX CHORE CREATION TESTS (5 tests)
    # ======================

    @pytest.mark.asyncio
    async def test_create_chore_with_invalid_usernames(self, httpx_mock: HTTPXMock, mock_login):
        """Test create_chore tool with non-existent usernames."""
        # Mock get_circle_members to return available users
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/circles/members/",
            json=[
                {"id": 1, "userId": 1, "circleId": 1, "role": "member", "isActive": True, "username": "alice", "displayName": "Alice", "points": 0, "pointsRedeemed": 0},
                {"id": 2, "userId": 2, "circleId": 1, "role": "member", "isActive": True, "username": "bob", "displayName": "Bob", "points": 0, "pointsRedeemed": 0},
            ],
        )

        result = await call_tool(
            "create_chore",
            {
                "name": "Test Chore",
                "usernames": ["alice", "charlie"],  # charlie doesn't exist
            }
        )

        assert len(result) == 1
        assert "Could not find user(s)" in result[0].text
        assert "charlie" in result[0].text
        assert "get_circle_members" in result[0].text  # Helpful hint

    @pytest.mark.asyncio
    async def test_create_chore_with_invalid_labels(self, httpx_mock: HTTPXMock, mock_login):
        """Test create_chore tool with non-existent labels."""
        # Mock get_labels to return available labels
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/labels",
            json=[
                {"id": 1, "name": "cleaning"},
                {"id": 2, "name": "urgent"},
            ],
        )

        result = await call_tool(
            "create_chore",
            {
                "name": "Test Chore",
                "label_names": ["cleaning", "outdoor"],  # outdoor doesn't exist
            }
        )

        assert len(result) == 1
        assert "Label(s) not found" in result[0].text
        assert "outdoor" in result[0].text
        assert "list_labels" in result[0].text  # Helpful hint
        assert "create_label" in result[0].text

    @pytest.mark.asyncio
    async def test_create_chore_all_assignstrategies(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test create_chore tool with all 7 assignment strategies."""
        strategies = [
            "least_completed",
            "least_assigned",
            "round_robin",
            "random",
            "keep_last_assigned",
            "random_except_last_assigned",
            "no_assignee"
        ]

        for strategy in strategies:
            # Mock POST response
            httpx_mock.add_response(
                url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
                json={"res": 1},
                method="POST",
            )
            # Mock GET response
            chore_response = sample_chore_data.copy()
            chore_response["assignStrategy"] = strategy
            httpx_mock.add_response(
                url="https://donetick.jason1365.duckdns.org/api/v1/chores/1",
                json=chore_response,
                method="GET",
            )

            result = await call_tool(
                "create_chore",
                {
                    "name": f"Test Chore {strategy}",
                    "assign_strategy": strategy,
                }
            )

            assert len(result) == 1
            assert "Successfully created" in result[0].text

    @pytest.mark.asyncio
    async def test_create_chore_priority_validation(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test create_chore tool with priority 0-4 validation."""
        # Valid priorities: 0, 1, 2, 3, 4
        for priority in [0, 1, 2, 3, 4]:
            httpx_mock.add_response(
                url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
                json={"res": 1},
                method="POST",
            )
            chore_response = sample_chore_data.copy()
            chore_response["priority"] = priority
            httpx_mock.add_response(
                url="https://donetick.jason1365.duckdns.org/api/v1/chores/1",
                json=chore_response,
                method="GET",
            )

            result = await call_tool(
                "create_chore",
                {
                    "name": f"Priority {priority} Chore",
                    "priority": priority,
                }
            )

            assert len(result) == 1
            assert "Successfully created" in result[0].text

        # Invalid priority: 5 (should fail validation at Pydantic level)
        result = await call_tool(
            "create_chore",
            {
                "name": "Invalid Priority Chore",
                "priority": 5,
            }
        )

        assert len(result) == 1
        assert "Validation Error" in result[0].text or "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_create_chore_frequency_transformation(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test create_chore tool frequency transformation from natural language to API format."""
        # Test days_of_week transformation
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
            json={"res": 1},
            method="POST",
        )
        chore_response = sample_chore_data.copy()
        chore_response["frequencyType"] = "days_of_the_week"
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1",
            json=chore_response,
            method="GET",
        )

        result = await call_tool(
            "create_chore",
            {
                "name": "Weekday Chore",
                "days_of_week": ["Mon", "Wed", "Fri"],
                "time_of_day": "09:00",
            }
        )

        assert len(result) == 1
        assert "Successfully created" in result[0].text

    # ======================
    # COMPREHENSIVE ERROR HANDLING (6 tests)
    # ======================

    @pytest.mark.asyncio
    async def test_http_401_authentication_error(self, httpx_mock: HTTPXMock, mock_login):
        """Test handling of 401 authentication errors."""
        # Client retries 3 times on 401, so we need 3 mock responses
        for _ in range(3):
            httpx_mock.add_response(
                url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
                status_code=401,
                json={"error": "Unauthorized"},
            )

        result = await call_tool("list_chores", {})

        assert len(result) == 1
        assert "Authentication failed" in result[0].text
        assert "DONETICK_USERNAME" in result[0].text
        assert "DONETICK_PASSWORD" in result[0].text
        # Should not expose raw error details
        assert "401" not in result[0].text

    @pytest.mark.asyncio
    async def test_http_403_forbidden_error(self, httpx_mock: HTTPXMock, mock_login):
        """Test handling of 403 forbidden errors."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1/do",
            status_code=403,
            json={"error": "Forbidden"},
            method="POST",
        )

        result = await call_tool("complete_chore", {"chore_id": 1})

        assert len(result) == 1
        assert "Permission denied" in result[0].text
        # Should not expose status code
        assert "403" not in result[0].text

    @pytest.mark.asyncio
    async def test_http_404_not_found_formatting(self, httpx_mock: HTTPXMock, mock_login):
        """Test user-friendly 404 error messages."""
        # Test for chore not found
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/999",
            status_code=404,
        )

        result = await call_tool("get_chore", {"chore_id": 999})

        assert len(result) == 1
        assert "not found" in result[0].text.lower()
        # Should not expose status code
        assert "404" not in result[0].text

    @pytest.mark.asyncio
    async def test_http_422_validation_error(self, httpx_mock: HTTPXMock, mock_login):
        """Test handling of 422 validation errors."""
        # Pydantic validation will catch invalid dates before API call
        # So test with a valid date format but API rejects it
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
            status_code=422,
            json={"error": "Validation error: invalid date"},
            method="POST",
        )

        result = await call_tool(
            "create_chore",
            {
                "name": "Test Chore",
                "due_date": "2020-01-01",  # Valid format but API rejects
            }
        )

        assert len(result) == 1
        assert "Validation error" in result[0].text
        # Should include helpful hints
        assert "YYYY-MM-DD" in result[0].text or "RFC3339" in result[0].text or "date" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_http_400_with_api_error_message(self, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test that 400 errors show the actual API error message."""
        # Mock GET for fetch-modify-send pattern
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/1",
            json={"res": sample_chore_data},
            method="GET",
        )
        # Mock PUT with specific API error
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
            status_code=400,
            json={"error": "Assigned to not found in assignees"},
            method="PUT",
        )

        result = await call_tool("update_chore", {"chore_id": 1, "name": "Updated"})

        assert len(result) == 1
        # Should show the actual API error message prominently
        assert "API Error: Assigned to not found in assignees" in result[0].text
        # Should still include helpful hints
        assert "💡 Hint" in result[0].text
        assert "list_circle_users" in result[0].text

    @pytest.mark.asyncio
    async def test_http_429_rate_limit(self, httpx_mock: HTTPXMock, mock_login):
        """Test handling of 429 rate limit errors."""
        # Mock retries (client retries 429 with backoff)
        # Provide 2 rate limit responses, then success
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
            status_code=429,
            json={"error": "Too many requests"},
            headers={"Retry-After": "0.1"},  # Short wait to prevent test timeout
        )
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
            status_code=429,
            json={"error": "Too many requests"},
            headers={"Retry-After": "0.1"},  # Short wait to prevent test timeout
        )
        # After retries, provide success response
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
            json=[],
        )

        result = await call_tool("list_chores", {})

        assert len(result) == 1
        # Should eventually succeed after rate limit retries
        assert "No chores found" in result[0].text

    @pytest.mark.asyncio
    async def test_http_500_server_error(self, httpx_mock: HTTPXMock, mock_login):
        """Test handling of 500 server errors."""
        # Mock 3 retry attempts (client retries 500 errors)
        for _ in range(3):
            httpx_mock.add_response(
                url="https://donetick.jason1365.duckdns.org/api/v1/chores/",
                status_code=500,
                json={"error": "Internal server error"},
            )

        result = await call_tool("list_chores", {})

        assert len(result) == 1
        assert "Error" in result[0].text
        # Should mention it's a server-side issue
        assert "server" in result[0].text.lower() or "try again" in result[0].text.lower()
        # Server errors are retried transparently to the user
        # Status code may or may not be exposed depending on implementation
        assert len(result[0].text) > 0

    @pytest.mark.asyncio
    async def test_get_chore_history_tool(self, httpx_mock: HTTPXMock, mock_login):
        """Test get_chore_history tool execution."""
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
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/123/history",
            json={"res": history_data},
        )

        result = await call_tool("get_chore_history", {"chore_id": 123})

        assert len(result) == 1
        assert "📊" in result[0].text
        assert "Completion History for Chore 123" in result[0].text
        assert "Total completions: 2" in result[0].text
        # completedBy is user ID (integer), displayed as "user 1"
        assert "user 1" in result[0].text
        assert "Completed successfully" in result[0].text
        assert "2025-11-05T10:00:00Z" in result[0].text

    @pytest.mark.asyncio
    async def test_get_all_chores_history_tool(self, httpx_mock: HTTPXMock, mock_login):
        """Test get_all_chores_history tool execution."""
        history_data = [
            {
                "id": 1,
                "choreId": 123,
                # Note: choreName doesn't exist in ChoreHistory model
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
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/history?limit=50&offset=0",
            json={"res": history_data},
        )

        result = await call_tool("get_all_chores_history", {})

        assert len(result) == 1
        assert "📊" in result[0].text
        assert "Chore Completion History" in result[0].text
        assert "Showing 2 entries" in result[0].text
        # Server displays "Chore #123" format (no chore names available in ChoreHistory)
        assert "Chore #123" in result[0].text
        assert "Chore #124" in result[0].text
        # Server displays "user 1" format (user IDs, not usernames)
        assert "user 1" in result[0].text
        assert "user 2" in result[0].text

    @pytest.mark.asyncio
    async def test_get_chore_details_tool(self, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """Test get_chore_details tool execution."""
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
            "averageDuration": 9000.5,  # Field is averageDuration (float seconds), not avgDuration
            "completionHistory": [history_entry],  # Field is completionHistory, not history
        }

        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/api/v1/chores/123/details",
            json={"res": details_data},
        )

        result = await call_tool("get_chore_details", {"chore_id": 123})

        assert len(result) == 1
        assert "📊" in result[0].text
        assert "Chore Details: Detailed Test Chore" in result[0].text
        assert "ID: 123" in result[0].text
        assert "Total Completions: 5" in result[0].text
        # Server displays duration as "9000.5s" (seconds), not "2h 30m"
        assert "9000.5s" in result[0].text
        assert "Last Completion" in result[0].text
        assert "2025-11-05T10:00:00Z" in result[0].text
        # Server displays "user 1" format (user ID, not username)
        assert "user 1" in result[0].text
