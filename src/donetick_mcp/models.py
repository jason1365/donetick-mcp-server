"""Pydantic models for Donetick API requests and responses."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Assignee(BaseModel):
    """Chore assignee model."""

    userId: int = Field(..., description="User ID of the assignee")


class Label(BaseModel):
    """Chore label model."""

    id: int = Field(..., description="Label ID")
    name: str = Field(..., description="Label name")


class NotificationMetadata(BaseModel):
    """Notification configuration metadata."""

    nagging: bool = Field(default=False, description="Enable nagging notifications")
    predue: bool = Field(default=False, description="Enable pre-due notifications")


class ChoreCreate(BaseModel):
    """Model for creating a new chore (simplified for eAPI)."""

    Name: str = Field(..., min_length=1, max_length=200, description="Chore name (required)")
    Description: Optional[str] = Field(None, description="Chore description")
    DueDate: Optional[str] = Field(
        None,
        description="Due date in RFC3339 or YYYY-MM-DD format",
    )
    CreatedBy: Optional[int] = Field(None, description="User ID of creator")

    class Config:
        json_schema_extra = {
            "example": {
                "Name": "Take out the trash",
                "Description": "Weekly trash collection",
                "DueDate": "2025-11-10",
                "CreatedBy": 1,
            }
        }


class ChoreUpdate(BaseModel):
    """Model for updating a chore (Premium feature)."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None)
    nextDueDate: Optional[str] = Field(None)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Take out recycling",
                "description": "Biweekly recycling collection",
                "nextDueDate": "2025-11-17",
            }
        }


class Chore(BaseModel):
    """Complete chore model as returned by the API."""

    id: int = Field(..., description="Chore ID")
    name: str = Field(..., description="Chore name")
    description: Optional[str] = Field(None, description="Chore description")
    frequencyType: str = Field(..., description="Frequency type (once, daily, weekly, etc)")
    frequency: int = Field(..., description="Frequency value")
    frequencyMetadata: dict[str, Any] = Field(default_factory=dict)
    nextDueDate: Optional[str] = Field(None, description="Next due date (ISO 8601)")
    isRolling: bool = Field(default=False, description="Is rolling schedule")
    assignedTo: int = Field(..., description="User ID of assigned user")
    assignees: list[Assignee] = Field(default_factory=list, description="List of assignees")
    assignStrategy: str = Field(
        default="least_completed",
        description="Assignment strategy",
    )
    isActive: bool = Field(default=True, description="Is chore active")
    notification: bool = Field(default=False, description="Enable notifications")
    notificationMetadata: NotificationMetadata = Field(
        default_factory=NotificationMetadata,
        description="Notification settings",
    )
    labels: Optional[list[str]] = Field(None, description="Legacy labels")
    labelsV2: list[Label] = Field(default_factory=list, description="Chore labels")
    circleId: int = Field(..., description="Circle/household ID")
    createdAt: str = Field(..., description="Creation timestamp (ISO 8601)")
    updatedAt: str = Field(..., description="Last update timestamp (ISO 8601)")
    createdBy: int = Field(..., description="Creator user ID")
    updatedBy: Optional[int] = Field(None, description="Last updater user ID")
    status: Optional[str] = Field(None, description="Chore status")
    priority: Optional[int] = Field(None, ge=1, le=5, description="Priority (1-5)")
    isPrivate: bool = Field(default=False, description="Is private chore")
    points: Optional[int] = Field(None, description="Points awarded")
    subTasks: list[Any] = Field(default_factory=list, description="Sub-tasks")
    thingChore: Optional[dict[str, Any]] = Field(None, description="Thing chore metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Take out the trash",
                "description": "Weekly trash collection",
                "frequencyType": "weekly",
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
        }


class CircleMember(BaseModel):
    """Circle member model."""

    userId: int = Field(..., description="User ID")
    userName: str = Field(..., description="User name")
    userEmail: str = Field(..., description="User email")
    role: str = Field(..., description="User role in circle")


class APIError(BaseModel):
    """API error response model."""

    error: str = Field(..., description="Error message")
    code: Optional[int] = Field(None, description="Error code")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error details")
