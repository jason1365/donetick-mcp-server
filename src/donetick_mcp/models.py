"""Pydantic models for Donetick API requests and responses."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Assignee(BaseModel):
    """Chore assignee model."""

    userId: int = Field(..., description="User ID of the assignee")


class Label(BaseModel):
    """Chore label model."""

    id: int = Field(..., description="Label ID")
    name: str = Field(..., description="Label name")
    color: Optional[str] = Field(None, description="Label color (hex code)")
    created_by: Optional[int] = Field(None, alias="createdBy", description="User ID who created the label")


class NotificationMetadata(BaseModel):
    """Notification configuration metadata."""

    nagging: bool = Field(default=False, description="Enable nagging notifications")
    predue: bool = Field(default=False, description="Enable pre-due notifications")


class ChoreCreate(BaseModel):
    """Enhanced model for creating a new chore with full feature support."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "name": "Take out the trash",
                "description": "Weekly trash collection on Monday mornings",
                "dueDate": "2025-11-10T09:00:00Z",
                "createdBy": 1,
                "frequencyType": "weekly",
                "frequency": 1,
                "frequencyMetadata": {"days": [1], "time": "09:00"},
                "isRolling": False,
                "assignedTo": 1,
                "assignees": [{"userId": 1}, {"userId": 2}],
                "assignStrategy": "least_completed",
                "notification": True,
                "notificationMetadata": {"nagging": True, "predue": True},
                "priority": 3,
                "labels": ["cleaning", "outdoor"],
                "isActive": True,
                "isPrivate": False,
                "points": 10,
                "completionWindow": 7,
                "requireApproval": False,
                "deadlineOffset": 0,
            }
        }
    )

    # Basic Information
    name: str = Field(
        ...,
        alias="Name",
        min_length=1,
        max_length=200,
        description="Chore name (required)"
    )
    description: Optional[str] = Field(
        None,
        alias="Description",
        max_length=5000,
        description="Chore description"
    )
    dueDate: Optional[str] = Field(
        None,
        alias="DueDate",
        description="Due date in RFC3339 or YYYY-MM-DD format",
    )
    createdBy: Optional[int] = Field(
        None,
        alias="CreatedBy",
        description="User ID of creator"
    )

    # Recurrence/Frequency Settings
    frequencyType: Optional[str] = Field(
        default="once",
        alias="FrequencyType",
        description="Frequency type: once, daily, weekly, monthly, yearly, interval_based",
    )
    frequency: Optional[int] = Field(
        default=1,
        alias="Frequency",
        ge=0,
        description="Frequency value (e.g., 0=once, 1=weekly, 2=biweekly)",
    )
    frequencyMetadata: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        alias="FrequencyMetadata",
        description="Additional frequency configuration (e.g., days of week, time)",
    )
    isRolling: Optional[bool] = Field(
        default=False,
        alias="IsRolling",
        description="Rolling schedule (next due date based on completion) vs fixed schedule",
    )

    # User Assignment
    assignedTo: Optional[int] = Field(
        None,
        alias="AssignedTo",
        description="Primary assigned user ID"
    )
    assignees: Optional[list[dict[str, int]]] = Field(
        default_factory=list,
        alias="Assignees",
        description="List of assignee objects with userId field",
    )
    assignStrategy: Optional[str] = Field(
        default="least_completed",
        alias="AssignStrategy",
        description="Assignment strategy: least_completed, round_robin, random",
    )

    # Notifications
    notification: Optional[bool] = Field(
        default=False,
        alias="Notification",
        description="Enable notifications for this chore"
    )
    notificationMetadata: Optional[dict[str, Any]] = Field(
        default=None,
        alias="NotificationMetadata",
        description="Notification settings with templates array: [{value: int, unit: str}]",
    )

    # Organization & Priority
    priority: Optional[int] = Field(
        None,
        alias="Priority",
        ge=0,
        le=4,
        description="Priority level (0=unset, 1=lowest, 4=highest)"
    )
    labels: Optional[list[str]] = Field(
        default_factory=list,
        alias="Labels",
        description="Label tags for categorization (legacy - use labelsV2)"
    )
    labelsV2: Optional[list[dict[str, int]]] = Field(
        default_factory=list,
        alias="LabelsV2",
        description="Label references - list of objects with 'id' field: [{'id': 1}, {'id': 2}]",
    )

    # Status & Visibility
    isActive: Optional[bool] = Field(
        default=True,
        alias="IsActive",
        description="Active status (inactive chores are hidden)"
    )
    isPrivate: Optional[bool] = Field(
        default=False,
        alias="IsPrivate",
        description="Private chore (visible only to creator)"
    )

    # Gamification
    points: Optional[int] = Field(
        None,
        alias="Points",
        ge=0,
        description="Points awarded for completion"
    )

    # Advanced Features
    subTasks: Optional[list[dict[str, Any]]] = Field(
        default_factory=list,
        alias="SubTasks",
        description="Sub-tasks/checklist items"
    )
    thingChore: Optional[dict[str, Any]] = Field(
        None,
        alias="ThingChore",
        description="Thing/device association metadata"
    )

    # Completion Settings (NEW)
    completionWindow: Optional[int] = Field(
        None,
        alias="CompletionWindow",
        ge=0,
        description="SECONDS before due time when chore can be completed early (e.g., 3600=1hr, 86400=1day)"
    )
    requireApproval: Optional[bool] = Field(
        default=False,
        alias="RequireApproval",
        description="Requires approval to mark complete"
    )

    # Advanced Scheduling (NEW)
    deadlineOffset: Optional[int] = Field(
        None,
        alias="DeadlineOffset",
        description="SECONDS after due time when deadline is reached (e.g., 3600=1hr grace, 86400=1day)"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and sanitize chore name."""
        if not v or not v.strip():
            raise ValueError('Chore name cannot be empty or whitespace only')
        # Remove control characters except newlines/tabs
        sanitized = ''.join(char for char in v if ord(char) >= 32 or char in '\n\r\t')
        return sanitized.strip()

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize description."""
        if v is None:
            return None
        # Remove control characters except newlines/tabs
        sanitized = ''.join(char for char in v if ord(char) >= 32 or char in '\n\r\t')
        return sanitized.strip() if sanitized.strip() else None

    @field_validator('dueDate')
    @classmethod
    def validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format (ISO 8601 or YYYY-MM-DD)."""
        if v is None:
            return v

        # Try parsing as ISO 8601 / RFC3339
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            pass

        # Try parsing as YYYY-MM-DD
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError(
                'dueDate must be in RFC3339 format (e.g., 2025-11-10T00:00:00Z) '
                'or YYYY-MM-DD format (e.g., 2025-11-10)'
            )

    @field_validator('frequencyType')
    @classmethod
    def validate_frequency_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate frequency type."""
        if v is None:
            return "once"
        valid_types = [
            "once",
            "daily",
            "weekly",
            "monthly",
            "yearly",
            "interval_based",
            "interval",
            "days_of_the_week",
            "day_of_the_month",
            "adaptive",
            "trigger",
            "no_repeat"
        ]
        if v.lower() not in valid_types:
            raise ValueError(
                f'frequencyType must be one of: {", ".join(valid_types)}'
            )
        return v.lower()

    @field_validator('assignStrategy')
    @classmethod
    def validate_assign_strategy(cls, v: Optional[str]) -> Optional[str]:
        """Validate assignment strategy."""
        if v is None:
            return "least_completed"
        valid_strategies = [
            "least_completed",
            "least_assigned",
            "round_robin",
            "random",
            "keep_last_assigned",
            "random_except_last_assigned",
            "no_assignee"
        ]
        if v.lower() not in valid_strategies:
            raise ValueError(
                f'assignStrategy must be one of: {", ".join(valid_strategies)}'
            )
        return v.lower()

    @field_validator('notificationMetadata')
    @classmethod
    def validate_notification_metadata(cls, v: Optional[dict]) -> Optional[dict]:
        """Validate notification metadata structure and template limit."""
        if v is None:
            return None

        # Check template limit (Donetick API enforces MAX_TEMPLATES=5)
        templates = v.get('templates', [])
        if len(templates) > 5:
            raise ValueError(
                f'notificationMetadata.templates cannot exceed 5 items (got {len(templates)}). '
                'The Donetick API enforces a maximum of 5 notification templates per chore.'
            )

        # Validate template structure
        for i, template in enumerate(templates):
            if not isinstance(template, dict):
                raise ValueError(
                    f'Template {i} must be an object with "value" and "unit" fields'
                )
            if 'value' not in template or 'unit' not in template:
                raise ValueError(
                    f'Template {i} missing required fields: value (int), unit (str)'
                )
            if template['unit'] not in ('m', 'h', 'd'):
                raise ValueError(
                    f'Template {i} has invalid unit "{template["unit"]}". '
                    'Valid units: "m" (minutes), "h" (hours), "d" (days)'
                )

        return v

    @field_validator('completionWindow')
    @classmethod
    def validate_completion_window(cls, v: Optional[int]) -> Optional[int]:
        """Validate completion window is reasonable."""
        if v is not None and v < 0:
            raise ValueError('completionWindow must be non-negative (in seconds)')
        if v is not None and v > 31536000:  # 1 year in seconds
            raise ValueError('completionWindow cannot exceed 1 year (31536000 seconds)')
        return v

    @field_validator('deadlineOffset')
    @classmethod
    def validate_deadline_offset(cls, v: Optional[int]) -> Optional[int]:
        """Validate deadline offset is reasonable."""
        if v is not None and v > 31536000:  # 1 year in seconds
            raise ValueError('deadlineOffset cannot exceed 1 year (31536000 seconds)')
        return v

    @field_validator('frequencyMetadata')
    @classmethod
    def validate_frequency_metadata(cls, v: Optional[dict]) -> Optional[dict]:
        """Validate frequency metadata structure."""
        if not v:
            return v

        # Validate days are lowercase full names
        if 'days' in v:
            if not isinstance(v['days'], list):
                raise ValueError('frequencyMetadata.days must be an array')
            valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            for day in v['days']:
                if not isinstance(day, str) or day.lower() not in valid_days:
                    raise ValueError(
                        f'Invalid day "{day}" in frequencyMetadata.days. '
                        f'Must be lowercase full names: {", ".join(valid_days)}'
                    )

        # Validate weekPattern
        if 'weekPattern' in v:
            valid_patterns = ['every_week', 'week_of_month', 'week_of_quarter']
            if v['weekPattern'] not in valid_patterns:
                raise ValueError(
                    f'Invalid weekPattern "{v["weekPattern"]}". '
                    f'Valid values: {", ".join(valid_patterns)}'
                )

        # Validate time format (should be ISO with timezone)
        if 'time' in v and v['time']:
            time_str = v['time']
            if 'T' not in time_str:
                raise ValueError(
                    f'frequencyMetadata.time must be ISO format with timezone '
                    f'(e.g., "2025-11-10T14:00:00-05:00"), got: "{time_str}"'
                )

        # Validate timezone is IANA format
        if 'timezone' in v and v['timezone']:
            try:
                import pytz
                pytz.timezone(v['timezone'])
            except Exception:
                raise ValueError(
                    f'Invalid timezone "{v["timezone"]}". '
                    'Use IANA timezone names like "America/New_York", "Europe/London", "UTC"'
                )

        return v


class ChoreUpdate(BaseModel):
    """Model for updating a chore."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Take out recycling",
                "description": "Biweekly recycling collection",
                "nextDueDate": "2025-11-17",
                "priority": 2,
                "points": 10,
                "isPrivate": False,
            }
        }
    )

    # Basic fields
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Chore name")
    description: Optional[str] = Field(None, description="Chore description")
    nextDueDate: Optional[str] = Field(None, description="Next due date (ISO 8601)")

    # Scheduling
    frequencyType: Optional[str] = Field(None, description="Frequency type (once, daily, weekly, etc)")
    frequency: Optional[int] = Field(None, ge=1, description="Frequency value")
    frequencyMetadata: Optional[dict[str, Any]] = Field(None, description="Frequency metadata (days, time, timezone, etc)")
    isRolling: Optional[bool] = Field(None, description="Is rolling schedule")

    # Assignment
    assignStrategy: Optional[str] = Field(None, description="Assignment strategy")
    assignees: Optional[list[dict[str, int]]] = Field(None, description="List of assignees with userId")

    # Notifications
    notification: Optional[bool] = Field(None, description="Enable notifications")
    notificationMetadata: Optional[dict[str, Any]] = Field(None, description="Notification metadata (templates, nagging, predue)")

    # Status & Priority
    isActive: Optional[bool] = Field(None, description="Is chore active")
    priority: Optional[int] = Field(None, ge=0, le=4, description="Priority (0=unset, 1=lowest, 4=highest)")

    # Gamification & Labels
    points: Optional[int] = Field(None, ge=0, description="Points awarded for completion")
    labelsV2: Optional[list[dict[str, int]]] = Field(None, description="List of labels with id")

    # Privacy & Approval
    isPrivate: Optional[bool] = Field(None, description="Hide from other circle members")
    requireApproval: Optional[bool] = Field(None, description="Requires approval to mark complete")

    # Completion & Deadline Settings
    completionWindow: Optional[int] = Field(None, ge=0, description="SECONDS before due time for early completion")
    deadlineOffset: Optional[int] = Field(None, ge=0, description="SECONDS after due time for grace period")

    # Subtasks (can be updated)
    subTasks: Optional[list[dict[str, Any]]] = Field(None, description="List of subtasks with name and orderId")


class Chore(BaseModel):
    """Complete chore model as returned by the API."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="Chore ID")
    name: str = Field(..., description="Chore name")
    description: Optional[str] = Field(None, description="Chore description")
    frequencyType: str = Field(..., description="Frequency type (once, daily, weekly, etc)")
    frequency: int = Field(..., description="Frequency value")
    frequencyMetadata: Optional[dict[str, Any]] = Field(None, description="Frequency metadata")
    nextDueDate: Optional[str] = Field(None, description="Next due date (ISO 8601)")
    isRolling: bool = Field(default=False, description="Is rolling schedule")
    assignedTo: Optional[int] = Field(None, description="User ID of assigned user")
    assignees: list[Assignee] = Field(default_factory=list, description="List of assignees")
    assignStrategy: str = Field(
        default="least_completed",
        description="Assignment strategy",
    )
    isActive: bool = Field(default=True, description="Is chore active")
    notification: bool = Field(default=False, description="Enable notifications")
    notificationMetadata: Optional[NotificationMetadata] = Field(
        None,
        description="Notification settings",
    )
    labels: Optional[list[str]] = Field(None, description="Legacy labels")
    labelsV2: list[Label] = Field(default_factory=list, description="Chore labels")
    circleId: int = Field(..., description="Circle/household ID")
    createdAt: str = Field(..., description="Creation timestamp (ISO 8601)")
    updatedAt: str = Field(..., description="Last update timestamp (ISO 8601)")
    createdBy: int = Field(..., description="Creator user ID")
    updatedBy: Optional[int] = Field(None, description="Last updater user ID")
    status: Optional[Any] = Field(None, description="Chore status (can be string or int)")
    priority: Optional[int] = Field(None, ge=0, le=4, description="Priority (0=unset, 1=lowest, 4=highest)")
    isPrivate: bool = Field(default=False, description="Is private chore")
    points: Optional[int] = Field(None, description="Points awarded")
    subTasks: list[Any] = Field(default_factory=list, description="Sub-tasks")
    thingChore: Optional[dict[str, Any]] = Field(None, description="Thing chore metadata")
    completionWindow: Optional[int] = Field(None, description="Days before/after due date for completion window")
    requireApproval: Optional[bool] = Field(None, description="Requires approval to mark complete")
    deadlineOffset: Optional[int] = Field(None, description="Offset in days for deadline calculation")


class CircleMember(BaseModel):
    """Circle member model."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="Circle member ID")
    userId: int = Field(..., description="User ID")
    circleId: int = Field(..., description="Circle ID")
    role: str = Field(..., description="Member role (admin, member)")
    isActive: bool = Field(..., description="Whether member is active")
    username: str = Field(..., description="Username")
    displayName: Optional[str] = Field(None, description="Display name")
    image: Optional[str] = Field(None, description="Profile image URL")
    points: Optional[int] = Field(0, description="Member points")
    pointsRedeemed: Optional[int] = Field(0, description="Points redeemed")


class User(BaseModel):
    """User model for circle members."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    displayName: Optional[str] = Field(None, description="Display name")
    email: Optional[str] = Field(None, description="Email address")
    role: Optional[str] = Field(None, description="User role in circle")
    circleId: Optional[int] = Field(None, description="Primary circle ID")
    image: Optional[str] = Field(None, description="Profile image URL")
    points: Optional[int] = Field(0, description="Total points earned")
    pointsRedeemed: Optional[int] = Field(0, description="Points redeemed")
    isActive: Optional[bool] = Field(True, description="Whether user is active")


class UserProfile(BaseModel):
    """Detailed user profile model."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    displayName: Optional[str] = Field(None, description="Display name")
    email: Optional[str] = Field(None, description="Email address")
    circleId: Optional[int] = Field(None, description="Primary circle ID")
    image: Optional[str] = Field(None, description="Profile image URL")
    points: Optional[int] = Field(0, description="Total points earned")
    pointsRedeemed: Optional[int] = Field(0, description="Points redeemed")
    isActive: Optional[bool] = Field(True, description="Whether user is active")
    createdAt: Optional[str] = Field(None, description="Account creation timestamp")
    updatedAt: Optional[str] = Field(None, description="Last update timestamp")
    # Notification preferences
    notificationTargets: Optional[dict[str, Any]] = Field(
        None,
        description="Notification target configuration"
    )
    webhook: Optional[str] = Field(None, description="Webhook URL for notifications")
    # Storage and limits
    storageUsed: Optional[int] = Field(0, description="Storage used in bytes")
    storageLimit: Optional[int] = Field(0, description="Storage limit in bytes")
    # Additional metadata
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional user metadata")


class APIError(BaseModel):
    """API error response model."""

    error: str = Field(..., description="Error message")
    code: Optional[int] = Field(None, description="Error code")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error details")
