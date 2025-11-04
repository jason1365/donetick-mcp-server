"""Unit tests for transformation helper methods in DonetickClient."""

import pytest
from datetime import datetime, timedelta
import pytz

from donetick_mcp.client import DonetickClient


@pytest.fixture
def client():
    """Create a test client instance for transformation testing."""
    return DonetickClient(
        base_url="https://test.donetick.com",
        username="test_user",
        password="test_password",
        rate_limit_per_second=100.0,
        rate_limit_burst=100,
    )


# ==================== FREQUENCY TRANSFORMATION TESTS ====================

class TestFrequencyTransformation:
    """Tests for transform_frequency_metadata() method."""

    def test_transform_frequency_metadata_all_days(self, client):
        """Test frequency transformation with all 7 days specified."""
        result = client.transform_frequency_metadata(
            frequency_type="days_of_the_week",
            days_of_week=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            time="14:30",
            timezone="America/New_York"
        )

        assert "days" in result
        assert len(result["days"]) == 7
        assert result["days"] == ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        assert result["unit"] == "days"
        assert result["weekPattern"] == "every_week"
        assert result["timezone"] == "America/New_York"
        assert "time" in result
        assert "T" in result["time"]  # Should be ISO format

    def test_transform_frequency_metadata_invalid_day_raises_error(self, client):
        """Test that invalid day names raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            client.transform_frequency_metadata(
                frequency_type="days_of_the_week",
                days_of_week=["Monday", "Moonday", "Friday"],
                timezone="America/New_York"
            )

        error_message = str(exc_info.value)
        assert "Invalid day name(s): Moonday" in error_message
        assert "Valid values:" in error_message

    def test_transform_frequency_metadata_empty_days_raises_error(self, client):
        """Test that empty days array raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            client.transform_frequency_metadata(
                frequency_type="days_of_the_week",
                days_of_week=[],
                timezone="America/New_York"
            )

        error_message = str(exc_info.value)
        assert "days_of_week parameter is required" in error_message
        assert "days_of_the_week" in error_message

    def test_transform_frequency_metadata_none_days_raises_error(self, client):
        """Test that None days raises ValueError for days_of_the_week frequency."""
        with pytest.raises(ValueError) as exc_info:
            client.transform_frequency_metadata(
                frequency_type="days_of_the_week",
                days_of_week=None,
                timezone="America/New_York"
            )

        error_message = str(exc_info.value)
        assert "days_of_week parameter is required" in error_message

    def test_transform_frequency_metadata_timezone_handling(self, client):
        """Test that timezone is properly included in metadata."""
        result = client.transform_frequency_metadata(
            frequency_type="days_of_the_week",
            days_of_week=["Wed"],
            time="09:00",
            timezone="Europe/London"
        )

        assert result["timezone"] == "Europe/London"
        assert "time" in result
        # Time should be in ISO format with timezone info
        assert "T" in result["time"]

    def test_transform_frequency_metadata_unit_and_weekpattern(self, client):
        """Test that unit='days' and weekPattern='every_week' are always added."""
        result = client.transform_frequency_metadata(
            frequency_type="days_of_the_week",
            days_of_week=["Fri"],
            timezone="America/Los_Angeles"
        )

        assert result["unit"] == "days"
        assert result["weekPattern"] == "every_week"

    def test_transform_frequency_metadata_mixed_case_days(self, client):
        """Test that mixed case day names are normalized correctly."""
        result = client.transform_frequency_metadata(
            frequency_type="days_of_the_week",
            days_of_week=["MONDAY", "WeDnEsDaY", "friday"],
            timezone="America/New_York"
        )

        assert result["days"] == ["monday", "wednesday", "friday"]

    def test_transform_frequency_metadata_short_abbreviations(self, client):
        """Test that 3-letter abbreviations work correctly."""
        result = client.transform_frequency_metadata(
            frequency_type="weekly",
            days_of_week=["Mon", "Wed", "Fri"],
            timezone="UTC"
        )

        assert result["days"] == ["monday", "wednesday", "friday"]

    def test_transform_frequency_metadata_time_without_days(self, client):
        """Test time transformation for non-days_of_the_week frequencies."""
        result = client.transform_frequency_metadata(
            frequency_type="daily",
            time="16:00",
            timezone="America/Chicago"
        )

        assert "time" in result
        assert "T" in result["time"]
        # Should NOT have days, unit, weekPattern for non-days_of_the_week
        assert "days" not in result

    def test_transform_frequency_metadata_iso_time_passthrough(self, client):
        """Test that ISO format times are passed through unchanged."""
        iso_time = "2025-11-10T14:00:00-05:00"
        result = client.transform_frequency_metadata(
            frequency_type="once",
            time=iso_time,
            timezone="America/New_York"
        )

        assert result["time"] == iso_time


# ==================== SUBTASK TRANSFORMATION TESTS ====================

class TestSubtaskTransformation:
    """Tests for transform_subtasks() method."""

    def test_transform_subtasks_ordering(self, client):
        """Test that subtasks get proper orderId field."""
        subtask_names = ["First task", "Second task", "Third task"]
        result = client.transform_subtasks(subtask_names)

        assert len(result) == 3
        for i, subtask in enumerate(result):
            assert subtask["orderId"] == i
            assert subtask["name"] == subtask_names[i]
            assert subtask["completedAt"] is None
            assert subtask["completedBy"] == 0
            assert subtask["parentId"] is None

    def test_transform_subtasks_empty_array(self, client):
        """Test that empty subtasks array returns empty list."""
        result = client.transform_subtasks([])
        assert result == []

    def test_transform_subtasks_single_item(self, client):
        """Test transformation of a single subtask."""
        result = client.transform_subtasks(["Only task"])

        assert len(result) == 1
        assert result[0]["orderId"] == 0
        assert result[0]["name"] == "Only task"

    def test_transform_subtasks_structure(self, client):
        """Test that all required fields are present in subtask structure."""
        result = client.transform_subtasks(["Test subtask"])

        assert len(result) == 1
        subtask = result[0]
        assert "orderId" in subtask
        assert "name" in subtask
        assert "completedAt" in subtask
        assert "completedBy" in subtask
        assert "parentId" in subtask

    def test_transform_subtasks_name_preservation(self, client):
        """Test that subtask names with special characters are preserved."""
        special_names = [
            "Task with emoji 🎯",
            "Task with numbers 123",
            "Task with symbols @#$",
            "Task with\nnewline"
        ]
        result = client.transform_subtasks(special_names)

        assert len(result) == len(special_names)
        for i, subtask in enumerate(result):
            assert subtask["name"] == special_names[i]


# ==================== DUE DATE CALCULATION TESTS ====================

class TestDueDateCalculation:
    """Tests for calculate_due_date() method."""

    def test_calculate_due_date_once_frequency(self, client):
        """Test due date calculation for 'once' frequency type."""
        result = client.calculate_due_date(
            frequency_type="once",
            frequency_metadata={},
            timezone="America/New_York"
        )

        # Should return tomorrow at noon
        tz = pytz.timezone("America/New_York")
        now = datetime.now(tz)
        tomorrow = now + timedelta(days=1)

        # Parse the result
        result_dt = datetime.fromisoformat(result.replace('Z', '+00:00'))
        result_tz = result_dt.astimezone(tz)

        assert result_tz.hour == 12
        assert result_tz.minute == 0
        assert result_tz.day == tomorrow.day

    def test_calculate_due_date_daily_with_time(self, client):
        """Test due date calculation for daily frequency with specific time."""
        tz = pytz.timezone("America/New_York")
        now = datetime.now(tz)
        test_time = now.replace(hour=9, minute=30)

        frequency_metadata = {
            "time": test_time.isoformat()
        }

        result = client.calculate_due_date(
            frequency_type="daily",
            frequency_metadata=frequency_metadata,
            timezone="America/New_York"
        )

        result_dt = datetime.fromisoformat(result.replace('Z', '+00:00'))
        result_tz = result_dt.astimezone(tz)

        assert result_tz.hour == 9
        assert result_tz.minute == 30

    def test_calculate_due_date_days_of_week_next_occurrence(self, client):
        """Test due date calculation for specific day of week."""
        tz = pytz.timezone("America/New_York")
        now = datetime.now(tz)

        # Set metadata for Wednesday at 2 PM
        frequency_metadata = {
            "days": ["wednesday"],
            "time": "2025-11-05T14:00:00-05:00"
        }

        result = client.calculate_due_date(
            frequency_type="days_of_the_week",
            frequency_metadata=frequency_metadata,
            timezone="America/New_York"
        )

        result_dt = datetime.fromisoformat(result.replace('Z', '+00:00'))
        result_tz = result_dt.astimezone(tz)

        # Should be a Wednesday
        assert result_tz.weekday() == 2  # Wednesday is 2
        assert result_tz.hour == 14
        assert result_tz.minute == 0

    def test_calculate_due_date_with_time_component(self, client):
        """Test due date calculation preserves time component."""
        frequency_metadata = {
            "time": "2025-11-10T16:45:00-05:00"
        }

        result = client.calculate_due_date(
            frequency_type="daily",
            frequency_metadata=frequency_metadata,
            timezone="America/New_York"
        )

        result_dt = datetime.fromisoformat(result.replace('Z', '+00:00'))
        tz = pytz.timezone("America/New_York")
        result_tz = result_dt.astimezone(tz)

        assert result_tz.hour == 16
        assert result_tz.minute == 45

    def test_calculate_due_date_default_time(self, client):
        """Test that default time is noon when no time specified."""
        result = client.calculate_due_date(
            frequency_type="daily",
            frequency_metadata={},
            timezone="America/New_York"
        )

        result_dt = datetime.fromisoformat(result.replace('Z', '+00:00'))
        tz = pytz.timezone("America/New_York")
        result_tz = result_dt.astimezone(tz)

        assert result_tz.hour == 12
        assert result_tz.minute == 0

    def test_calculate_due_date_returns_rfc3339(self, client):
        """Test that returned date is in RFC3339 format (ends with Z)."""
        result = client.calculate_due_date(
            frequency_type="once",
            frequency_metadata={},
            timezone="UTC"
        )

        # Should end with 'Z' for UTC
        assert result.endswith('Z')
        # Should contain 'T' separator
        assert 'T' in result
        # Should be parseable as ISO format
        datetime.fromisoformat(result.replace('Z', '+00:00'))


# ==================== NOTIFICATION TRANSFORMATION TESTS ====================

class TestNotificationTransformation:
    """Tests for transform_notification_metadata() method."""

    def test_notification_transform_multiple_reminders(self, client):
        """Test combining offset, due time, and nagging notifications."""
        result = client.transform_notification_metadata(
            offset_minutes=-30,
            remind_at_due_time=True,
            nagging=True,
            predue=True
        )

        assert result["nagging"] is True
        assert result["predue"] is True
        assert "templates" in result
        assert len(result["templates"]) == 2

        # Should have -30 minute offset and 0 (due time)
        values = [t["value"] for t in result["templates"]]
        assert -30 in values
        assert 0 in values

    def test_notification_transform_edge_cases(self, client):
        """Test edge cases: zero offset, no offset."""
        # Zero offset should not create a template (0 is handled by remind_at_due_time)
        result = client.transform_notification_metadata(
            offset_minutes=0,
            remind_at_due_time=False,
            nagging=False,
            predue=False
        )

        assert result["nagging"] is False
        assert result["predue"] is False
        # Zero offset should NOT add a template
        assert "templates" not in result or len(result.get("templates", [])) == 0

    def test_notification_transform_negative_offset(self, client):
        """Test negative offset (before due time)."""
        result = client.transform_notification_metadata(
            offset_minutes=-60,
            remind_at_due_time=False,
            nagging=False,
            predue=True
        )

        assert result["predue"] is True
        assert "templates" in result
        assert len(result["templates"]) == 1
        assert result["templates"][0]["value"] == -60
        assert result["templates"][0]["unit"] == "m"

    def test_notification_transform_positive_offset(self, client):
        """Test positive offset (after due time)."""
        result = client.transform_notification_metadata(
            offset_minutes=120,
            remind_at_due_time=False,
            nagging=True,
            predue=False
        )

        assert result["nagging"] is True
        assert "templates" in result
        assert len(result["templates"]) == 1
        assert result["templates"][0]["value"] == 120
        assert result["templates"][0]["unit"] == "m"

    def test_notification_transform_units(self, client):
        """Test that unit is always 'm' (minutes) for offset_minutes."""
        test_cases = [
            (-15, "m"),   # 15 minutes before
            (-60, "m"),   # 1 hour before
            (30, "m"),    # 30 minutes after
        ]

        for offset, expected_unit in test_cases:
            result = client.transform_notification_metadata(
                offset_minutes=offset,
                remind_at_due_time=False,
                nagging=False,
                predue=False
            )

            assert "templates" in result
            assert len(result["templates"]) == 1
            assert result["templates"][0]["unit"] == expected_unit

    def test_notification_transform_no_reminders(self, client):
        """Test notification metadata with no reminders enabled."""
        result = client.transform_notification_metadata(
            offset_minutes=None,
            remind_at_due_time=False,
            nagging=False,
            predue=False
        )

        assert result["nagging"] is False
        assert result["predue"] is False
        assert "templates" not in result or len(result.get("templates", [])) == 0

    def test_notification_transform_only_due_time_reminder(self, client):
        """Test only remind at due time (no offset)."""
        result = client.transform_notification_metadata(
            offset_minutes=None,
            remind_at_due_time=True,
            nagging=False,
            predue=False
        )

        assert "templates" in result
        assert len(result["templates"]) == 1
        assert result["templates"][0]["value"] == 0
        assert result["templates"][0]["unit"] == "m"

    def test_notification_transform_structure(self, client):
        """Test that notification metadata has required structure."""
        result = client.transform_notification_metadata(
            offset_minutes=-45,
            remind_at_due_time=True,
            nagging=True,
            predue=True
        )

        # Required top-level fields
        assert "nagging" in result
        assert "predue" in result
        assert isinstance(result["nagging"], bool)
        assert isinstance(result["predue"], bool)

        # Templates structure
        assert "templates" in result
        assert isinstance(result["templates"], list)
        for template in result["templates"]:
            assert "value" in template
            assert "unit" in template
            assert isinstance(template["value"], int)
            assert isinstance(template["unit"], str)
