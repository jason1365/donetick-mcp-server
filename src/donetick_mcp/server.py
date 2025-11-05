"""Donetick MCP server implementation."""

import asyncio
import json
import logging
import urllib.parse
from typing import Any, Optional

import httpx
from mcp.server import Server
from mcp.types import TextContent, Tool

from . import __version__
from .client import DonetickClient
from .config import config
from .models import ChoreCreate, ChoreUpdate

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
                "due dates, assignees, and status. "
                "Use detail_level to control response size: 'brief' for essential fields only, "
                "'full' for complete details (default)."
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
                    "detail_level": {
                        "type": "string",
                        "enum": ["brief", "full"],
                        "description": "Response format: 'brief' (id, name, status, assignee, dueDate) or 'full' (all fields). Default: 'full'",
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
                "Create a new chore in Donetick with easy natural language inputs. "
                "Use simple parameters like usernames, days_of_week, and time_of_day - "
                "they're automatically transformed to the correct API format.\n\n"
                "EXAMPLES:\n"
                "1. Simple recurring chore:\n"
                "   {name: 'Take out trash', days_of_week: ['Mon', 'Thu'], "
                "time_of_day: '19:00', usernames: ['Alice']}\n\n"
                "2. Weekly chore with reminders:\n"
                "   {name: 'Team meeting', days_of_week: ['Tue'], time_of_day: '14:00', "
                "remind_minutes_before: 15, usernames: ['Alice', 'Bob']}\n\n"
                "3. With subtasks and labels:\n"
                "   {name: 'Weekly review', days_of_week: ['Fri'], time_of_day: '17:00', "
                "subtask_names: ['Check email', 'Update notes'], label_names: ['work', 'weekly']}\n\n"
                "4. Daily chore with points:\n"
                "   {name: 'Exercise', frequency_type: 'daily', time_of_day: '07:00', "
                "points: 10, usernames: ['Bob']}\n\n"
                "5. One-time chore:\n"
                "   {name: 'Fix leaky faucet', due_date: '2025-11-10', "
                "priority: 5, usernames: ['Alice']}\n\n"
                "Returns the created chore with its assigned ID and all metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    # Basic Information
                    "name": {
                        "type": "string",
                        "description": "Chore name (required, 1-200 characters)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Chore description (optional, max 5000 characters)",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date in YYYY-MM-DD or RFC3339 format (optional)",
                    },
                    "created_by": {
                        "type": "integer",
                        "description": "User ID of the creator (optional)",
                    },

                    # Recurrence/Frequency
                    "frequency_type": {
                        "type": "string",
                        "enum": [
                            "once",           # One-time chore
                            "daily",          # Every day
                            "weekly",         # Every week
                            "monthly",        # Every month
                            "yearly",         # Every year
                            "interval_based", # Custom interval
                            "interval",       # Alias for interval_based
                            "days_of_the_week", # Specific days (Mon, Wed, Fri)
                            "day_of_the_month", # Specific day of month (e.g., 15th)
                            "adaptive",       # Smart scheduling based on completion patterns
                            "trigger",        # Triggered by events
                            "no_repeat"       # Alias for once
                        ],
                        "description": (
                            "How often the chore repeats (default: once).\n\n"
                            "FREQUENCY TYPES:\n"
                            "• once / no_repeat: One-time chore, no recurrence\n"
                            "• daily: Repeats every day at specified time\n"
                            "• weekly: Repeats every week (use with frequency for bi-weekly: frequency=2)\n"
                            "• days_of_the_week: Specific days (Mon, Wed, Fri) - BEST for multiple days/week\n"
                            "  → Use with days_of_week parameter: ['Mon', 'Wed', 'Fri']\n"
                            "• monthly: Repeats every month\n"
                            "• yearly: Repeats every year\n"
                            "• day_of_the_month: Specific day of month (e.g., 15th of each month)\n"
                            "• interval_based / interval: Custom interval (e.g., every N days)\n"
                            "• adaptive: Smart scheduling based on completion patterns\n"
                            "• trigger: Triggered by events or conditions\n\n"
                            "TIP: For chores on specific days (Mon/Wed/Fri), use frequency_type='days_of_the_week' "
                            "with days_of_week=['Mon', 'Wed', 'Fri'] instead of frequency_type='weekly'"
                        ),
                    },
                    "frequency": {
                        "type": "integer",
                        "description": "Frequency multiplier (e.g., 1=weekly, 2=biweekly, default: 1)",
                        "minimum": 1,
                    },
                    "frequency_metadata": {
                        "type": "object",
                        "description": "Additional frequency config (e.g., {\"days\": [1,3,5], \"time\": \"09:00\"})",
                    },
                    "is_rolling": {
                        "type": "boolean",
                        "description": "Rolling schedule (next due based on completion) vs fixed (default: false)",
                    },

                    # User Assignment
                    "assigned_to": {
                        "type": "integer",
                        "description": "Primary assigned user ID (optional)",
                    },
                    "assignees": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Multiple assignees as array of {\"userId\": int} objects",
                    },
                    "assign_strategy": {
                        "type": "string",
                        "enum": [
                            "least_completed",
                            "least_assigned",
                            "round_robin",
                            "random",
                            "keep_last_assigned",
                            "random_except_last_assigned",
                            "no_assignee"
                        ],
                        "description": "Assignment strategy: least_completed, least_assigned, round_robin, random, keep_last_assigned, random_except_last_assigned, no_assignee (default: least_completed)",
                    },

                    # Notifications
                    "notification": {
                        "type": "boolean",
                        "description": "Enable notifications for this chore (default: false)",
                    },
                    "nagging": {
                        "type": "boolean",
                        "description": "Enable nagging/reminder notifications (default: false)",
                    },
                    "predue": {
                        "type": "boolean",
                        "description": "Enable pre-due date notifications (default: false)",
                    },

                    # Organization
                    "priority": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 4,
                        "description": "Priority level: 0=unset, 1=lowest, 2=low, 3=medium, 4=highest (optional)",
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Label tags for categorization (e.g., [\"cleaning\", \"outdoor\"])",
                    },

                    # Status
                    "is_active": {
                        "type": "boolean",
                        "description": "Active status - inactive chores are hidden (default: true)",
                    },
                    "is_private": {
                        "type": "boolean",
                        "description": "Private chore visible only to creator (default: false)",
                    },

                    # Gamification
                    "points": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Points awarded for completion (optional)",
                    },

                    # Advanced
                    "sub_tasks": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Sub-tasks/checklist items (optional)",
                    },

                    # === NATURAL LANGUAGE INPUTS (Simplified) ===
                    # These are automatically transformed to the API format

                    "usernames": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "EASY: Assign by usernames instead of IDs (e.g., ['Alice', 'Bob']). First user becomes primary assignee.",
                    },
                    "label_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "EASY: Label by names instead of IDs (e.g., ['cleaning', 'urgent'])",
                    },
                    "days_of_week": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "EASY: Days as short names (e.g., ['Mon', 'Wed', 'Fri'] or ['monday', 'wednesday']). "
                            "Auto-sets frequency_type to days_of_the_week.\n\n"
                            "REQUIRED when frequency_type='days_of_the_week'.\n"
                            "Valid values: Mon/Monday, Tue/Tuesday, Wed/Wednesday, Thu/Thursday, Fri/Friday, Sat/Saturday, Sun/Sunday"
                        ),
                    },
                    "time_of_day": {
                        "type": "string",
                        "description": "EASY: Time in HH:MM format (e.g., '16:00' for 4pm)",
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone name (default: America/New_York). Used with days_of_week and time_of_day.",
                    },
                    "remind_minutes_before": {
                        "type": "integer",
                        "description": "EASY: Remind X minutes before due time (e.g., 15 for 15 minutes before)",
                    },
                    "remind_at_due_time": {
                        "type": "boolean",
                        "description": "EASY: Also remind exactly at due time (default: false)",
                    },
                    "enable_nagging": {
                        "type": "boolean",
                        "description": "EASY: Enable nagging notifications - repeated reminders if not completed (default: false)",
                    },
                    "enable_predue": {
                        "type": "boolean",
                        "description": "EASY: Enable pre-due notifications - reminders before due date arrives (default: false)",
                    },
                    "subtask_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "EASY: Subtask names as simple strings (e.g., ['Do homework', 'Check work'])",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="complete_chore",
            description=(
                "Mark a chore as complete. "
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
            name="update_chore",
            description=(
                "Update an existing chore with new values. "
                "Can modify any chore property including name, description, schedule, assignees, "
                "priority, points, labels, privacy settings, and more. "
                "Only provide fields you want to change - other fields remain unchanged."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chore_id": {
                        "type": "integer",
                        "description": "The ID of the chore to update",
                    },
                    "name": {
                        "type": "string",
                        "description": "New chore name",
                    },
                    "description": {
                        "type": "string",
                        "description": "New chore description",
                    },
                    "nextDueDate": {
                        "type": "string",
                        "description": "New due date (ISO 8601 format, e.g., '2025-11-17')",
                    },
                    "priority": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 4,
                        "description": "Priority level (0=unset, 1=lowest, 4=highest)",
                    },
                    "points": {
                        "type": "integer",
                        "description": "Points awarded for completion",
                    },
                    "isActive": {
                        "type": "boolean",
                        "description": "Enable/disable chore",
                    },
                    "isPrivate": {
                        "type": "boolean",
                        "description": "Hide from other circle members",
                    },
                    "requireApproval": {
                        "type": "boolean",
                        "description": "Requires approval to mark complete",
                    },
                    "frequencyType": {
                        "type": "string",
                        "description": "Frequency type (once, daily, weekly, monthly, yearly, days_of_the_week)",
                    },
                    "frequency": {
                        "type": "integer",
                        "description": "Frequency value (e.g., 2 for every 2 weeks)",
                    },
                    "frequencyMetadata": {
                        "type": "object",
                        "description": "Frequency metadata with days, time, timezone, weekPattern",
                    },
                    "isRolling": {
                        "type": "boolean",
                        "description": "Rolling schedule (based on completion) vs fixed schedule",
                    },
                    "assignStrategy": {
                        "type": "string",
                        "enum": [
                            "least_completed",
                            "least_assigned",
                            "round_robin",
                            "random",
                            "keep_last_assigned",
                            "random_except_last_assigned",
                            "no_assignee",
                        ],
                        "description": "Assignment rotation strategy",
                    },
                    "notification": {
                        "type": "boolean",
                        "description": "Enable notifications",
                    },
                    "notificationMetadata": {
                        "type": "object",
                        "description": "Notification settings (templates, nagging, predue)",
                    },
                    "completionWindow": {
                        "type": "integer",
                        "description": "SECONDS before due time when early completion is allowed",
                    },
                    "deadlineOffset": {
                        "type": "integer",
                        "description": "SECONDS after due time for grace period",
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
        Tool(
            name="update_chore_priority",
            description=(
                "Update a chore's priority level (0-4). "
                "Use this to adjust how urgent a chore is without editing other details. "
                "0=unset, 1=lowest, 2=low, 3=medium, 4=highest. "
                "Returns the updated chore."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chore_id": {
                        "type": "integer",
                        "description": "The ID of the chore to update",
                    },
                    "priority": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 4,
                        "description": "New priority level (0=unset, 1=lowest, 4=highest)",
                    },
                },
                "required": ["chore_id", "priority"],
            },
        ),
        Tool(
            name="update_chore_assignee",
            description=(
                "Reassign a chore to a different circle member. "
                "Use this to dynamically change who is responsible for a chore. "
                "Get member IDs from list_circle_members or get_circle_members. "
                "Returns the updated chore."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chore_id": {
                        "type": "integer",
                        "description": "The ID of the chore to update",
                    },
                    "user_id": {
                        "type": "integer",
                        "description": "User ID of the new assignee (from list_circle_members)",
                    },
                },
                "required": ["chore_id", "user_id"],
            },
        ),
        Tool(
            name="skip_chore",
            description=(
                "Skip a chore without marking it complete. "
                "For recurring chores, this schedules the next occurrence without "
                "completing the current one. Useful for chores that aren't needed this cycle. "
                "One-time chores will be marked as inactive. "
                "Returns the updated chore with the new due date."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chore_id": {
                        "type": "integer",
                        "description": "The ID of the chore to skip",
                    },
                },
                "required": ["chore_id"],
            },
        ),
        Tool(
            name="update_subtask_completion",
            description=(
                "Mark a subtask as complete or incomplete within a chore. "
                "This allows tracking progress on chores with multiple steps without "
                "completing the entire chore. Useful for checklists and multi-step tasks. "
                "Returns the updated chore with subtask progress."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chore_id": {
                        "type": "integer",
                        "description": "The ID of the chore containing the subtask",
                    },
                    "subtask_id": {
                        "type": "integer",
                        "description": "The ID of the subtask to update",
                    },
                    "completed": {
                        "type": "boolean",
                        "description": "True to mark complete, False to mark incomplete",
                    },
                },
                "required": ["chore_id", "subtask_id", "completed"],
            },
        ),
        Tool(
            name="list_labels",
            description=(
                "List all labels in the circle. "
                "Returns all available labels with their IDs, names, and colors. "
                "Use these labels to organize and categorize chores."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="create_label",
            description=(
                "Create a new label for organizing chores. "
                "Labels help categorize and filter chores by type, location, or any custom criteria. "
                "Optionally specify a color in hex format (e.g., '#FF5733')."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Label name (required)",
                    },
                    "color": {
                        "type": "string",
                        "description": "Label color in hex format (e.g., '#80d8ff'), optional",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="update_label",
            description=(
                "Update an existing label's name and/or color. "
                "Use this to rename labels or change their colors for better organization."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "label_id": {
                        "type": "integer",
                        "description": "The ID of the label to update",
                    },
                    "name": {
                        "type": "string",
                        "description": "New label name",
                    },
                    "color": {
                        "type": "string",
                        "description": "New label color in hex format (e.g., '#80d8ff'), optional",
                    },
                },
                "required": ["label_id", "name"],
            },
        ),
        Tool(
            name="delete_label",
            description=(
                "Delete a label permanently. "
                "This will remove the label from all chores that use it. "
                "Use with caution as this action cannot be undone."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "label_id": {
                        "type": "integer",
                        "description": "The ID of the label to delete",
                    },
                },
                "required": ["label_id"],
            },
        ),
        Tool(
            name="get_circle_members",
            description=(
                "Get all members in the circle (household/team). "
                "Returns user information including user IDs, usernames, display names, "
                "roles (admin/member), active status, and points. "
                "Use this to see who you can assign chores to."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="list_circle_users",
            description=(
                "List all users in the circle with basic information. "
                "Returns user IDs, usernames, display names, email addresses, "
                "roles, points earned, and active status. "
                "Similar to get_circle_members but may include additional user details."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_user_profile",
            description=(
                "Get the current user's detailed profile information. "
                "Returns comprehensive user data including notification preferences, "
                "webhook configuration, storage usage, points, and account metadata. "
                "Use this to view or manage personal settings and statistics."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_chore_history",
            description=(
                "Get completion history for a specific chore. "
                "Returns all completion records including when the chore was completed, "
                "by whom, completion notes, and points awarded. "
                "Useful for tracking chore completion patterns and accountability."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chore_id": {
                        "type": "integer",
                        "description": "The ID of the chore to fetch history for",
                    },
                },
                "required": ["chore_id"],
            },
        ),
        Tool(
            name="get_all_chores_history",
            description=(
                "Get completion history for all chores with pagination support. "
                "Returns completion records across all chores in the circle, "
                "showing who completed what and when. "
                "Use limit and offset for pagination through large result sets."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of history entries to return (default: 50, max: 200)",
                        "minimum": 1,
                        "maximum": 200,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of entries to skip for pagination (default: 0)",
                        "minimum": 0,
                    },
                },
            },
        ),
        Tool(
            name="get_chore_details",
            description=(
                "Get detailed chore information including completion statistics and analytics. "
                "Returns extended details not available in standard get_chore: "
                "total completion count, last completion date and user, average duration, "
                "and recent completion history. "
                "Useful for performance analysis and chore optimization."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chore_id": {
                        "type": "integer",
                        "description": "The ID of the chore to fetch detailed statistics for",
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
            detail_level = arguments.get("detail_level", "full")

            chores = await client.list_chores(
                filter_active=filter_active,
                assigned_to_user_id=assigned_to_user_id,
            )

            # Format response
            if not chores:
                return [TextContent(type="text", text="No chores found.")]

            # Apply detail level filter
            if detail_level == "brief":
                # Brief format: only essential fields
                brief_chores = []
                for chore in chores:
                    brief_chores.append({
                        "id": chore.id,
                        "name": chore.name,
                        "isActive": chore.isActive,
                        "assignedTo": chore.assignedTo,
                        "nextDueDate": chore.nextDueDate,
                    })
                result = {
                    "count": len(brief_chores),
                    "chores": brief_chores,
                }
            else:
                # Full format: all fields
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
            # ===== Handle User Assignment =====
            assigned_to = arguments.get("assigned_to")
            assignees = arguments.get("assignees", [])
            usernames = arguments.get("usernames", [])

            # If usernames provided, lookup IDs
            if usernames:
                username_map = await client.lookup_user_ids(usernames)

                # Check if all usernames were found
                if not username_map or len(username_map) != len(usernames):
                    # Find which usernames were not found
                    missing = [u for u in usernames if u not in (username_map or {})]
                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"Error: Could not find user(s) in circle: {', '.join(missing)}\n\n"
                                "💡 Hint: Use get_circle_members to see available users.\n"
                                "   Valid users must be members of your circle/household."
                            )
                        )
                    ]

                # Use first username as primary assignee
                assigned_to = username_map.get(usernames[0])
                # Build assignees list
                assignees = [{"userId": uid} for uid in username_map.values()]

            # ===== Handle Labels =====
            labels_v2 = arguments.get("labels_v2", [])
            label_names = arguments.get("label_names", [])

            # If label names provided, lookup IDs
            if label_names:
                label_map = await client.lookup_label_ids(label_names)

                # Check if all labels were found
                missing_labels = [name for name in label_names if name not in (label_map or {})]

                if missing_labels:
                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"Error: Label(s) not found: {', '.join(missing_labels)}\n\n"
                                "💡 Hint: Use list_labels to see available labels.\n"
                                "   You can create missing labels with create_label tool."
                            )
                        )
                    ]

                labels_v2 = [{"id": label_id} for label_id in label_map.values()]

            # ===== Handle Frequency Metadata =====
            frequency_type = arguments.get("frequency_type", "once")
            frequency_metadata = arguments.get("frequency_metadata", {})
            days_of_week = arguments.get("days_of_week", [])
            time_of_day = arguments.get("time_of_day")
            timezone = arguments.get("timezone", "America/New_York")

            # Validate days_of_week is provided for days_of_the_week frequency type
            if frequency_type == "days_of_the_week" and not days_of_week:
                return [
                    TextContent(
                        type="text",
                        text=(
                            "Error: days_of_week parameter is required when frequency_type='days_of_the_week'.\n\n"
                            "Please provide which days the chore should repeat on, for example:\n"
                            "  days_of_week: ['Mon', 'Wed', 'Fri']\n"
                            "  days_of_week: ['Monday', 'Tuesday', 'Thursday']\n\n"
                            "Valid day values: Mon/Monday, Tue/Tuesday, Wed/Wednesday, Thu/Thursday, "
                            "Fri/Friday, Sat/Saturday, Sun/Sunday"
                        ),
                    )
                ]

            # If simple day/time inputs provided, transform to API format
            if days_of_week or time_of_day:
                frequency_metadata = client.transform_frequency_metadata(
                    frequency_type=frequency_type,
                    days_of_week=days_of_week,
                    time=time_of_day,
                    timezone=timezone
                )
                # Auto-set frequency type if days are specified
                if days_of_week and frequency_type == "once":
                    frequency_type = "days_of_the_week"

            # ===== Handle Notification Metadata =====
            notification_metadata = arguments.get("notification_metadata", {})
            remind_minutes_before = arguments.get("remind_minutes_before")
            remind_at_due_time = arguments.get("remind_at_due_time", False)
            enable_nagging = arguments.get("enable_nagging", False)
            enable_predue = arguments.get("enable_predue", False)

            # If any notification inputs provided, transform to API format
            if remind_minutes_before is not None or remind_at_due_time or enable_nagging or enable_predue:
                offset_minutes = -abs(remind_minutes_before) if remind_minutes_before else None
                notification_metadata = client.transform_notification_metadata(
                    offset_minutes=offset_minutes,
                    remind_at_due_time=remind_at_due_time,
                    nagging=enable_nagging,
                    predue=enable_predue
                )

            # ===== Handle Subtasks =====
            sub_tasks = arguments.get("sub_tasks", [])
            subtask_names = arguments.get("subtask_names", [])

            # If simple subtask names provided, transform to API format
            if subtask_names:
                sub_tasks = client.transform_subtasks(subtask_names)

            # ===== Calculate Due Date =====
            due_date = arguments.get("due_date")
            if not due_date and frequency_type != "once":
                # Auto-calculate initial due date based on frequency
                due_date = client.calculate_due_date(
                    frequency_type=frequency_type,
                    frequency_metadata=frequency_metadata,
                    timezone=timezone
                )

            # ===== Build ChoreCreate Object =====
            chore_create = ChoreCreate(
                # Basic Information
                name=arguments["name"],
                description=arguments.get("description"),
                dueDate=due_date,
                createdBy=arguments.get("created_by"),

                # Recurrence/Frequency
                frequencyType=frequency_type,
                frequency=arguments.get("frequency", 1),
                frequencyMetadata=frequency_metadata,
                isRolling=arguments.get("is_rolling", False),

                # User Assignment
                assignedTo=assigned_to,
                assignees=assignees,
                assignStrategy=arguments.get("assign_strategy", "least_completed"),

                # Notifications
                notification=arguments.get("notification", bool(notification_metadata)),
                notificationMetadata=notification_metadata,

                # Organization & Priority
                priority=arguments.get("priority"),
                labels=arguments.get("labels", []),
                labelsV2=labels_v2,

                # Status & Visibility
                isActive=arguments.get("is_active", True),
                isPrivate=arguments.get("is_private", False),

                # Gamification
                points=arguments.get("points"),

                # Advanced Features
                subTasks=sub_tasks,
                thingChore=arguments.get("thing_chore"),

                # Completion Settings
                completionWindow=arguments.get("completion_window"),
                requireApproval=arguments.get("require_approval", False),

                # Advanced Scheduling
                deadlineOffset=arguments.get("deadline_offset"),
            )

            chore = await client.create_chore(chore_create)

            return [
                TextContent(
                    type="text",
                    text=f"Successfully created chore '{chore.name}' (ID: {chore.id})\n\n{json.dumps(chore.model_dump(), indent=2)}",
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

        elif name == "update_chore":
            chore_id = arguments.pop("chore_id")

            # Build ChoreUpdate model from provided arguments
            # Filter out None values to only include fields that should be updated
            update_data = {k: v for k, v in arguments.items() if v is not None}

            try:
                update = ChoreUpdate(**update_data)
                chore = await client.update_chore(chore_id, update)

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully updated chore '{chore.name}' (ID: {chore.id})\n\n"
                        + json.dumps(chore.model_dump(), indent=2),
                    )
                ]
            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"Validation error: {str(e)}",
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

        elif name == "update_chore_priority":
            chore_id = arguments["chore_id"]
            priority = arguments["priority"]

            chore = await client.update_chore_priority(chore_id, priority)

            return [
                TextContent(
                    type="text",
                    text=f"Successfully updated chore '{chore.name}' (ID: {chore.id}) priority to {priority}\n\n"
                    + json.dumps(chore.model_dump(), indent=2),
                )
            ]

        elif name == "update_chore_assignee":
            chore_id = arguments["chore_id"]
            user_id = arguments["user_id"]

            chore = await client.update_chore_assignee(chore_id, user_id)

            return [
                TextContent(
                    type="text",
                    text=f"Successfully reassigned chore '{chore.name}' (ID: {chore.id}) to user {user_id}\n\n"
                    + json.dumps(chore.model_dump(), indent=2),
                )
            ]

        elif name == "skip_chore":
            chore_id = arguments["chore_id"]

            chore = await client.skip_chore(chore_id)

            return [
                TextContent(
                    type="text",
                    text=f"Successfully skipped chore '{chore.name}' (ID: {chore.id}). "
                    f"Next due date: {chore.nextDueDate}\n\n"
                    + json.dumps(chore.model_dump(), indent=2),
                )
            ]

        elif name == "update_subtask_completion":
            chore_id = arguments["chore_id"]
            subtask_id = arguments["subtask_id"]
            completed = arguments["completed"]

            chore = await client.update_subtask_completion(chore_id, subtask_id, completed)

            # Calculate subtask progress
            total_subtasks = len(chore.subTasks)
            completed_subtasks = sum(1 for st in chore.subTasks if st.get('completedAt'))
            progress_pct = (completed_subtasks / total_subtasks * 100) if total_subtasks > 0 else 0

            # Format subtask list
            subtasks_text = "\n".join([
                f"  {'✅' if st.get('completedAt') else '⬜'} {st.get('name', 'Unnamed')} (ID: {st.get('id')})"
                for st in chore.subTasks
            ])

            return [
                TextContent(
                    type="text",
                    text=f"✅ Successfully updated subtask {subtask_id} on chore '{chore.name}' (ID: {chore.id})\n\n"
                    f"📊 Progress: {completed_subtasks}/{total_subtasks} subtasks complete ({progress_pct:.0f}%)\n\n"
                    f"Subtasks:\n{subtasks_text}",
                )
            ]

        elif name == "list_labels":
            labels = await client.get_labels()

            # Format labels for display
            labels_text = "Available Labels:\n\n"
            for label in labels:
                color_info = f" (Color: {label.color})" if label.color else ""
                labels_text += f"- ID {label.id}: {label.name}{color_info}\n"

            if not labels:
                labels_text = "No labels found in this circle."

            return [
                TextContent(
                    type="text",
                    text=labels_text,
                )
            ]

        elif name == "create_label":
            name_arg = arguments["name"]
            color = arguments.get("color")

            label = await client.create_label(name=name_arg, color=color)

            color_info = f" with color {label.color}" if label.color else ""
            return [
                TextContent(
                    type="text",
                    text=f"Successfully created label '{label.name}' (ID: {label.id}){color_info}.",
                )
            ]

        elif name == "update_label":
            label_id = arguments["label_id"]
            name_arg = arguments["name"]
            color = arguments.get("color")

            label = await client.update_label(label_id=label_id, name=name_arg, color=color)

            color_info = f" with color {label.color}" if label.color else ""
            return [
                TextContent(
                    type="text",
                    text=f"Successfully updated label ID {label.id} to '{label.name}'{color_info}.",
                )
            ]

        elif name == "delete_label":
            label_id = arguments["label_id"]

            await client.delete_label(label_id)

            return [
                TextContent(
                    type="text",
                    text=f"Successfully deleted label with ID {label_id}.",
                )
            ]

        elif name == "get_circle_members":
            members = await client.get_circle_members()

            # Format member information
            member_list = []
            for member in members:
                role_emoji = "👑" if member.role == "admin" else "👤"
                status_emoji = "✅" if member.isActive else "❌"
                display_name = member.displayName or "(no display name)"

                member_info = (
                    f"{role_emoji} {status_emoji} {member.username}\n"
                    f"  User ID: {member.userId}\n"
                    f"  Display Name: {display_name}\n"
                    f"  Role: {member.role}\n"
                    f"  Points: {member.points} (Redeemed: {member.pointsRedeemed})"
                )
                member_list.append(member_info)

            result_text = (
                f"Found {len(members)} member(s) in your circle:\n\n" +
                "\n\n".join(member_list)
            )

            return [
                TextContent(
                    type="text",
                    text=result_text,
                )
            ]

        elif name == "list_circle_users":
            users = await client.list_users()

            # Format user information
            user_list = []
            for user in users:
                status_emoji = "✅" if user.isActive else "❌"
                display_name = user.displayName or "(no display name)"
                email = user.email or "(no email)"
                role = user.role or "member"

                user_info = (
                    f"{status_emoji} {user.username}\n"
                    f"  User ID: {user.id}\n"
                    f"  Display Name: {display_name}\n"
                    f"  Email: {email}\n"
                    f"  Role: {role}\n"
                    f"  Points: {user.points} (Redeemed: {user.pointsRedeemed})"
                )
                user_list.append(user_info)

            result_text = (
                f"Found {len(users)} user(s) in your circle:\n\n" +
                "\n\n".join(user_list)
            )

            return [
                TextContent(
                    type="text",
                    text=result_text,
                )
            ]

        elif name == "get_user_profile":
            profile = await client.get_user_profile()

            # Format profile information
            display_name = profile.displayName or "(not set)"
            email = profile.email or "(not set)"
            webhook = profile.webhook or "(not configured)"
            storage_used_mb = (profile.storageUsed or 0) / (1024 * 1024)
            storage_limit_mb = (profile.storageLimit or 0) / (1024 * 1024)

            profile_info = (
                f"👤 User Profile for {profile.username}\n\n"
                f"📝 Basic Information:\n"
                f"  User ID: {profile.id}\n"
                f"  Username: {profile.username}\n"
                f"  Display Name: {display_name}\n"
                f"  Email: {email}\n"
                f"  Active: {'✅ Yes' if profile.isActive else '❌ No'}\n\n"
                f"🏆 Gamification:\n"
                f"  Points Earned: {profile.points}\n"
                f"  Points Redeemed: {profile.pointsRedeemed}\n"
                f"  Net Points: {profile.points - profile.pointsRedeemed}\n\n"
                f"💾 Storage:\n"
                f"  Used: {storage_used_mb:.2f} MB\n"
                f"  Limit: {storage_limit_mb:.2f} MB\n"
                f"  Available: {storage_limit_mb - storage_used_mb:.2f} MB\n\n"
                f"🔔 Notifications:\n"
                f"  Webhook: {webhook}\n\n"
                f"🕐 Account Dates:\n"
                f"  Created: {profile.createdAt or 'Unknown'}\n"
                f"  Updated: {profile.updatedAt or 'Unknown'}"
            )

            return [
                TextContent(
                    type="text",
                    text=profile_info,
                )
            ]

        elif name == "get_chore_history":
            chore_id = arguments["chore_id"]
            history = await client.get_chore_history(chore_id)

            if not history:
                return [
                    TextContent(
                        type="text",
                        text=f"No completion history found for chore {chore_id}",
                    )
                ]

            # Format history entries with emojis and clear structure
            entries = []
            for entry in history:
                status_emoji = "✅" if entry.completedAt else "⏳"
                completed_by = entry.completedBy or "Unknown"
                completed_at = entry.completedAt or "Unknown"
                notes = entry.note or "No notes"

                entry_text = (
                    f"{status_emoji} Completion ID: {entry.id}\n"
                    f"  👤 Completed by: {completed_by}\n"
                    f"  📅 Completed at: {completed_at}\n"
                    f"  📝 Notes: {notes}"
                )
                entries.append(entry_text)

            history_text = (
                f"📊 Completion History for Chore {chore_id}\n"
                f"Total completions: {len(history)}\n\n"
                + "\n\n".join(entries)
            )

            return [
                TextContent(
                    type="text",
                    text=history_text,
                )
            ]

        elif name == "get_all_chores_history":
            limit = arguments.get("limit", 50)
            offset = arguments.get("offset", 0)

            history = await client.get_all_chores_history(limit=limit, offset=offset)

            if not history:
                return [
                    TextContent(
                        type="text",
                        text="No completion history found",
                    )
                ]

            # Group entries by chore for better readability
            by_chore: dict[int, list] = {}
            for entry in history:
                chore_id = entry.choreId
                if chore_id not in by_chore:
                    by_chore[chore_id] = []
                by_chore[chore_id].append(entry)

            # Format grouped history
            chore_sections = []
            for chore_id, entries in by_chore.items():
                chore_name = entries[0].choreName if entries else "Unknown"
                entry_lines = []

                for entry in entries:
                    status_emoji = "✅"
                    completed_by = entry.completedBy or "Unknown"
                    completed_at = entry.completedAt or "Unknown"

                    entry_lines.append(
                        f"  {status_emoji} {completed_at} by {completed_by}"
                    )

                section = (
                    f"🏷️  {chore_name} (Chore ID: {chore_id})\n"
                    + "\n".join(entry_lines)
                )
                chore_sections.append(section)

            pagination_hint = ""
            if len(history) == limit:
                pagination_hint = f"\n\n💡 Showing {limit} entries (offset: {offset}). Use offset={offset + limit} to see more."

            history_text = (
                f"📊 Chore Completion History\n"
                f"Showing {len(history)} entries\n\n"
                + "\n\n".join(chore_sections)
                + pagination_hint
            )

            return [
                TextContent(
                    type="text",
                    text=history_text,
                )
            ]

        elif name == "get_chore_details":
            chore_id = arguments["chore_id"]
            details = await client.get_chore_details(chore_id)

            # Format detailed statistics
            total_count = details.totalCompletedCount or 0
            last_completed = details.lastCompletedDate or "Never"
            last_user = details.lastCompletedBy or "N/A"
            avg_duration = details.avgDuration or "N/A"

            # Format recent history
            recent_history = []
            if details.history:
                for entry in details.history[:5]:  # Show last 5
                    completed_at = entry.completedAt or "Unknown"
                    completed_by = entry.completedBy or "Unknown"
                    recent_history.append(f"  ✅ {completed_at} by {completed_by}")

            history_text = "\n".join(recent_history) if recent_history else "  No completions yet"

            details_text = (
                f"📊 Chore Details: {details.name}\n"
                f"ID: {details.id}\n\n"
                f"📈 Statistics:\n"
                f"  Total Completions: {total_count}\n"
                f"  Average Duration: {avg_duration}\n\n"
                f"🕐 Last Completion:\n"
                f"  Date: {last_completed}\n"
                f"  By: {last_user}\n\n"
                f"📜 Recent History (last 5):\n"
                f"{history_text}"
            )

            return [
                TextContent(
                    type="text",
                    text=details_text,
                )
            ]

        else:
            return [
                TextContent(
                    type="text",
                    text=f"Unknown tool: {name}",
                )
            ]

    except httpx.HTTPStatusError as e:
        # Log full error internally
        logger.error(f"HTTP error executing tool {name}: {e.response.status_code} - {e.response.text}", exc_info=True)

        # Return helpful error messages with hints
        status_code = e.response.status_code
        if status_code == 401:
            error_msg = (
                "Authentication failed. Please check your username and password.\n\n"
                "💡 Hint: Verify credentials in environment variables or .env file:\n"
                "   - DONETICK_BASE_URL\n"
                "   - DONETICK_USERNAME\n"
                "   - DONETICK_PASSWORD"
            )
        elif status_code == 403:
            error_msg = (
                "Permission denied. You may not have authorization for this operation.\n\n"
                "💡 Hint: Verify that:\n"
                "   - You have the correct credentials\n"
                "   - The resource exists and belongs to your circle\n"
                "   - You have the necessary permissions (e.g., only creators can delete chores)"
            )
        elif status_code == 404:
            if "chore" in name:
                error_msg = (
                    "Chore not found.\n\n"
                    "💡 Hint: Use list_chores to see available chores and their IDs.\n"
                    "   Chores may have been deleted or the ID may be incorrect."
                )
            elif "label" in name:
                error_msg = (
                    "Label not found.\n\n"
                    "💡 Hint: Use list_labels to see available labels and their IDs.\n"
                    "   Labels may have been deleted or the ID may be incorrect."
                )
            else:
                error_msg = "Resource not found."
        elif status_code == 422:
            error_msg = (
                "Validation error. The API rejected the request parameters.\n\n"
                "💡 Hint: Common issues:\n"
                "   - Invalid date format (use YYYY-MM-DD or RFC3339)\n"
                "   - Invalid frequency_type (use: once, daily, weekly, days_of_the_week, etc.)\n"
                "   - Missing required fields (name, due_date for some operations)\n"
                "   - Invalid user or label IDs (use get_circle_members or list_labels first)"
            )
        elif status_code == 429:
            error_msg = (
                "Rate limit exceeded. The server is receiving too many requests.\n\n"
                "💡 Hint: Wait a few seconds before retrying. The rate limit is\n"
                "   typically 10 requests per second."
            )
        elif 400 <= status_code < 500:
            error_msg = (
                f"Request failed with status {status_code}. Please check your input.\n\n"
                "💡 Hint: Review the tool's input parameters and ensure:\n"
                "   - Required fields are provided\n"
                "   - Data types match expectations (IDs are integers, names are strings)\n"
                "   - Values are in correct format (dates, colors, etc.)"
            )
        else:
            error_msg = (
                f"API request failed with status {status_code}.\n\n"
                "💡 Hint: This is likely a server-side issue. Try again in a moment.\n"
                "   If the problem persists, check the Donetick server status."
            )

        return [TextContent(type="text", text=f"Error: {error_msg}")]

    except httpx.TimeoutException as e:
        logger.error(f"Timeout executing tool {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=(
                "Error: Request timed out.\n\n"
                "💡 Hint: The Donetick server took too long to respond. This could mean:\n"
                "   - The server is under heavy load\n"
                "   - Network connectivity issues\n"
                "   - The server may be down\n"
                "Try again in a few moments."
            )
        )]

    except ValueError as e:
        # Validation errors (safe to expose)
        logger.warning(f"Validation error in tool {name}: {e}")
        return [TextContent(
            type="text",
            text=(
                f"Validation Error: {str(e)}\n\n"
                "💡 Hint: This is a data validation error. Check that:\n"
                "   - All required parameters are provided\n"
                "   - Data types are correct (numbers as integers, text as strings)\n"
                "   - Values are in expected format (dates, emails, URLs, etc.)"
            )
        )]

    except Exception as e:
        # Log full error internally
        logger.error(f"Unexpected error executing tool {name}: {e}", exc_info=True)

        # Return generic error to user (don't leak internals)
        return [TextContent(
            type="text",
            text=(
                "Error: An unexpected error occurred while processing your request.\n\n"
                "💡 Hint: This is an internal error. Please:\n"
                "   - Check the server logs for details\n"
                "   - Try the operation again\n"
                "   - If the problem persists, report it as a bug"
            )
        )]


async def cleanup():
    """Cleanup resources on shutdown."""
    global client
    if client:
        try:
            await client.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
        finally:
            client = None


def sanitize_url(url: str) -> str:
    """Sanitize URL for logging by removing sensitive parts."""
    try:
        parsed = urllib.parse.urlparse(url)
        # Only show scheme and path, hide host details
        return f"{parsed.scheme}://[SERVER]{parsed.path}"
    except Exception:
        return "[URL]"


async def main_async():
    """Async main entry point for the MCP server."""
    import sys
    from mcp.server.stdio import stdio_server

    logger.info(f"Starting Donetick MCP Server v{__version__}")
    logger.info(f"Connecting to: {sanitize_url(config.donetick_base_url)}")
    logger.info(f"Username: {config.donetick_username}")

    # Print to stderr for visibility in Claude Desktop
    print(f"Donetick MCP Server v{__version__} starting...", file=sys.stderr)

    # Run with stdio transport - this blocks until the server stops
    logger.info("Initializing stdio transport...")
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Server running and ready to accept requests")
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


def main():
    """Main entry point for the MCP server."""
    import sys
    import traceback

    try:
        # Run the async main function
        asyncio.run(main_async())

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        # Log to both logger and stderr to ensure visibility in Claude Desktop logs
        error_msg = f"Server error: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    finally:
        # Cleanup with proper async handling
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(cleanup())
            elif not loop.is_closed():
                loop.run_until_complete(cleanup())
            else:
                # Create new loop for cleanup
                asyncio.run(cleanup())
        except Exception as e:
            cleanup_error = f"Cleanup error: {e}\n{traceback.format_exc()}"
            logger.error(cleanup_error)
            print(cleanup_error, file=sys.stderr)


if __name__ == "__main__":
    import sys
    import traceback

    try:
        main()
    except Exception as e:
        # Catch any errors during initialization (e.g., config validation)
        error_msg = f"Failed to start server: {e}\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        sys.exit(1)
