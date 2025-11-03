"""Integration tests for MCP server."""

import json

import pytest
from pytest_httpx import HTTPXMock

from donetick_mcp.server import app, get_client


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
        tools = await app.list_tools()

        assert len(tools) == 5
        tool_names = [tool.name for tool in tools]
        assert "list_chores" in tool_names
        assert "get_chore" in tool_names
        assert "create_chore" in tool_names
        assert "complete_chore" in tool_names
        assert "delete_chore" in tool_names

    @pytest.mark.asyncio
    async def test_list_chores_tool(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test list_chores tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/eapi/v1/chore",
            json=[sample_chore_data],
        )

        result = await app.call_tool("list_chores", {})

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
            url="https://donetick.jason1365.duckdns.org/eapi/v1/chore",
            json=[sample_chore_data, inactive_chore],
        )

        result = await app.call_tool("list_chores", {"filter_active": True})

        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 1

    @pytest.mark.asyncio
    async def test_list_chores_empty(self, httpx_mock: HTTPXMock):
        """Test list_chores tool with no results."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/eapi/v1/chore",
            json=[],
        )

        result = await app.call_tool("list_chores", {})

        assert len(result) == 1
        assert "No chores found" in result[0].text

    @pytest.mark.asyncio
    async def test_get_chore_tool(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test get_chore tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/eapi/v1/chore",
            json=[sample_chore_data],
        )

        result = await app.call_tool("get_chore", {"chore_id": 1})

        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 1
        assert response_data["name"] == "Test Chore"

    @pytest.mark.asyncio
    async def test_get_chore_not_found(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test get_chore tool with non-existent ID."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/eapi/v1/chore",
            json=[sample_chore_data],
        )

        result = await app.call_tool("get_chore", {"chore_id": 999})

        assert len(result) == 1
        assert "not found" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_create_chore_tool(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test create_chore tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/eapi/v1/chore",
            json=sample_chore_data,
            method="POST",
        )

        result = await app.call_tool(
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
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/eapi/v1/chore",
            json=sample_chore_data,
            method="POST",
        )

        result = await app.call_tool("create_chore", {"name": "Test Chore"})

        assert len(result) == 1
        assert "Successfully created" in result[0].text

    @pytest.mark.asyncio
    async def test_complete_chore_tool(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test complete_chore tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/eapi/v1/chore/1/complete",
            json=sample_chore_data,
            method="POST",
        )

        result = await app.call_tool("complete_chore", {"chore_id": 1})

        assert len(result) == 1
        assert "Successfully completed" in result[0].text
        assert "Test Chore" in result[0].text

    @pytest.mark.asyncio
    async def test_complete_chore_with_user(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test complete_chore tool with completed_by parameter."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/eapi/v1/chore/1/complete?completedBy=2",
            json=sample_chore_data,
            method="POST",
        )

        result = await app.call_tool("complete_chore", {"chore_id": 1, "completed_by": 2})

        assert len(result) == 1
        assert "Successfully completed" in result[0].text

    @pytest.mark.asyncio
    async def test_delete_chore_tool(self, httpx_mock: HTTPXMock):
        """Test delete_chore tool execution."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/eapi/v1/chore/1",
            json={},
            method="DELETE",
        )

        result = await app.call_tool("delete_chore", {"chore_id": 1})

        assert len(result) == 1
        assert "Successfully deleted" in result[0].text

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, httpx_mock: HTTPXMock):
        """Test error handling in tools."""
        httpx_mock.add_response(
            url="https://donetick.jason1365.duckdns.org/eapi/v1/chore",
            status_code=500,
            json={"error": "Internal server error"},
        )

        result = await app.call_tool("list_chores", {})

        assert len(result) == 1
        assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test calling an unknown tool."""
        result = await app.call_tool("unknown_tool", {})

        assert len(result) == 1
        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, sample_chore_data, httpx_mock: HTTPXMock):
        """Test handling concurrent tool calls."""
        import asyncio

        # Mock multiple responses
        for _ in range(3):
            httpx_mock.add_response(
                url="https://donetick.jason1365.duckdns.org/eapi/v1/chore",
                json=[sample_chore_data],
            )

        # Launch concurrent tool calls
        tasks = [app.call_tool("list_chores", {}) for _ in range(3)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 3
        assert all(len(r) == 1 for r in results)
