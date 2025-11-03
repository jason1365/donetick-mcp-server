"""Donetick MCP server implementation."""

import asyncio
import json
import logging
from typing import Any, Optional

from mcp.server import Server
from mcp.types import TextContent, Tool

from .client import DonetickClient
from .config import config
from .models import ChoreCreate

# Configure logging
config.configure_logging()
logger = logging.getLogger(__name__)

# Initialize MCP server
app = Server("donetick-chores")

# Global client instance (initialized on startup)
client: Optional[DonetickClient] = None


async def get_client() -> DonetickClient:
    """Get or create the global Donetick client."""
    global client
    if client is None:
        client = DonetickClient()
    return client


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="list_chores",
            description=(
                "List all chores from Donetick. "
                "Optionally filter by active status or assigned user. "
                "Returns comprehensive chore details including name, description, "
                "due dates, assignees, and status."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filter_active": {
                        "type": "boolean",
                        "description": "Filter by active status (true=active only, false=inactive only, null=all)",
                    },
                    "assigned_to_user_id": {
                        "type": "integer",
                        "description": "Filter by assigned user ID (null=all users)",
                    },
                },
            },
        ),
        Tool(
            name="get_chore",
            description=(
                "Get details of a specific chore by its ID. "
                "Returns complete chore information including all metadata, "
                "assignees, labels, and scheduling details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chore_id": {
                        "type": "integer",
                        "description": "The ID of the chore to retrieve",
                    },
                },
                "required": ["chore_id"],
            },
        ),
        Tool(
            name="create_chore",
            description=(
                "Create a new chore in Donetick. "
                "Requires a name (required) and optionally accepts description, "
                "due date, and creator user ID. "
                "Returns the created chore with its assigned ID and metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Chore name (required, 1-200 characters)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Chore description (optional)",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date in YYYY-MM-DD or RFC3339 format (optional)",
                    },
                    "created_by": {
                        "type": "integer",
                        "description": "User ID of the creator (optional)",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="complete_chore",
            description=(
                "Mark a chore as complete. "
                "This is a Donetick Plus/Premium feature. "
                "Optionally specify which user completed the chore. "
                "Returns the updated chore with completion timestamp."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chore_id": {
                        "type": "integer",
                        "description": "The ID of the chore to mark complete",
                    },
                    "completed_by": {
                        "type": "integer",
                        "description": "User ID who completed the chore (optional)",
                    },
                },
                "required": ["chore_id"],
            },
        ),
        Tool(
            name="delete_chore",
            description=(
                "Delete a chore permanently. "
                "Note: Only the chore creator can delete a chore. "
                "Returns confirmation of deletion."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chore_id": {
                        "type": "integer",
                        "description": "The ID of the chore to delete",
                    },
                },
                "required": ["chore_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool execution."""
    try:
        client = await get_client()

        if name == "list_chores":
            filter_active = arguments.get("filter_active")
            assigned_to_user_id = arguments.get("assigned_to_user_id")

            chores = await client.list_chores(
                filter_active=filter_active,
                assigned_to_user_id=assigned_to_user_id,
            )

            # Format response
            if not chores:
                return [TextContent(type="text", text="No chores found.")]

            result = {
                "count": len(chores),
                "chores": [chore.model_dump() for chore in chores],
            }

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_chore":
            chore_id = arguments["chore_id"]
            chore = await client.get_chore(chore_id)

            if not chore:
                return [
                    TextContent(
                        type="text",
                        text=f"Chore with ID {chore_id} not found.",
                    )
                ]

            return [TextContent(type="text", text=json.dumps(chore.model_dump(), indent=2))]

        elif name == "create_chore":
            chore_create = ChoreCreate(
                Name=arguments["name"],
                Description=arguments.get("description"),
                DueDate=arguments.get("due_date"),
                CreatedBy=arguments.get("created_by"),
            )

            chore = await client.create_chore(chore_create)

            return [
                TextContent(
                    type="text",
                    text=f"Successfully created chore '{chore.name}' (ID: {chore.id})\n\n"
                    + json.dumps(chore.model_dump(), indent=2),
                )
            ]

        elif name == "complete_chore":
            chore_id = arguments["chore_id"]
            completed_by = arguments.get("completed_by")

            chore = await client.complete_chore(chore_id, completed_by=completed_by)

            return [
                TextContent(
                    type="text",
                    text=f"Successfully completed chore '{chore.name}' (ID: {chore.id})\n\n"
                    + json.dumps(chore.model_dump(), indent=2),
                )
            ]

        elif name == "delete_chore":
            chore_id = arguments["chore_id"]

            await client.delete_chore(chore_id)

            return [
                TextContent(
                    type="text",
                    text=f"Successfully deleted chore with ID {chore_id}.",
                )
            ]

        else:
            return [
                TextContent(
                    type="text",
                    text=f"Unknown tool: {name}",
                )
            ]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=f"Error: {str(e)}",
            )
        ]


async def cleanup():
    """Cleanup resources on shutdown."""
    global client
    if client:
        await client.close()
        client = None


def main():
    """Main entry point for the MCP server."""
    import sys

    try:
        # Run the MCP server with stdio transport
        import mcp.server.stdio

        logger.info("Starting Donetick MCP server...")
        logger.info(f"Connected to: {config.donetick_base_url}")

        # Run with stdio transport
        mcp.server.stdio.stdio_server()(app)

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        asyncio.run(cleanup())


if __name__ == "__main__":
    main()
