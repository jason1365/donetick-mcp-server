"""Unit tests for Pydantic models validation."""

import pytest
from pydantic import ValidationError

from donetick_mcp.models import ChoreCreate, ChoreUpdate, Chore


class TestChoreCreatePriorityValidation:
    """Test priority field validation (must be 0-4)."""

    def test_priority_validation_valid_range(self):
        """Test that valid priority values (0-4) are accepted."""
        for priority in [0, 1, 2, 3, 4]:
            chore = ChoreCreate(
                name="Test Chore",
                priority=priority
            )
            assert chore.priority == priority

    def test_priority_validation_negative_fails(self):
        """Test that negative priority values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(
                name="Test Chore",
                priority=-1
            )
        error = exc_info.value
        assert "priority" in str(error).lower()
        assert "greater than or equal to 0" in str(error).lower()

    def test_priority_validation_above_max_fails(self):
        """Test that priority values above 4 are rejected."""
        for invalid_priority in [5, 10, 100]:
            with pytest.raises(ValidationError) as exc_info:
                ChoreCreate(
                    name="Test Chore",
                    priority=invalid_priority
                )
            error = exc_info.value
            assert "priority" in str(error).lower()
            assert "less than or equal to 4" in str(error).lower()

    def test_priority_validation_none_allowed(self):
        """Test that None is accepted for priority (optional field)."""
        chore = ChoreCreate(name="Test Chore", priority=None)
        assert chore.priority is None


class TestChoreCreateAssignStrategyValidation:
    """Test assignment strategy validation."""

    @pytest.mark.parametrize("strategy", [
        "least_completed",
        "round_robin",
        "random",
        "least_assigned",
        "keep_last_assigned",
        "random_except_last_assigned",
        "no_assignee"
    ])
    def test_assignstrategy_validation_all_values(self, strategy):
        """Test that all 7 valid assignment strategies are accepted."""
        chore = ChoreCreate(
            name="Test Chore",
            assignStrategy=strategy
        )
        assert chore.assignStrategy == strategy.lower()

    def test_assignstrategy_validation_case_insensitive(self):
        """Test that assignment strategy validation is case-insensitive."""
        chore = ChoreCreate(
            name="Test Chore",
            assignStrategy="LEAST_COMPLETED"
        )
        assert chore.assignStrategy == "least_completed"

    def test_assignstrategy_validation_invalid(self):
        """Test that invalid assignment strategies are rejected."""
        invalid_strategies = [
            "invalid_strategy",
            "first_come_first_served",
            "alphabetical"
        ]
        for invalid_strategy in invalid_strategies:
            with pytest.raises(ValidationError) as exc_info:
                ChoreCreate(
                    name="Test Chore",
                    assignStrategy=invalid_strategy
                )
            error = exc_info.value
            assert "assignstrategy" in str(error).lower() or "must be one of" in str(error).lower()


class TestChoreCreateNotificationMetadataValidation:
    """Test notification metadata validation."""

    def test_notification_metadata_template_limit(self):
        """Test that max 5 notification templates are allowed."""
        # 5 templates should pass
        valid_templates = [
            {"value": 1, "unit": "h"},
            {"value": 2, "unit": "h"},
            {"value": 1, "unit": "d"},
            {"value": 2, "unit": "d"},
            {"value": 30, "unit": "m"}
        ]
        chore = ChoreCreate(
            name="Test Chore",
            notificationMetadata={"templates": valid_templates}
        )
        assert len(chore.notificationMetadata["templates"]) == 5

        # 6 templates should fail
        invalid_templates = valid_templates + [{"value": 3, "unit": "d"}]
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(
                name="Test Chore",
                notificationMetadata={"templates": invalid_templates}
            )
        error = exc_info.value
        assert "cannot exceed 5" in str(error)
        assert "got 6" in str(error)

    def test_notification_metadata_template_structure(self):
        """Test that notification templates require 'value' and 'unit' fields."""
        # Missing 'value' field
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(
                name="Test Chore",
                notificationMetadata={"templates": [{"unit": "h"}]}
            )
        error = exc_info.value
        assert "missing required fields" in str(error).lower() or "value" in str(error).lower()

        # Missing 'unit' field
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(
                name="Test Chore",
                notificationMetadata={"templates": [{"value": 1}]}
            )
        error = exc_info.value
        assert "missing required fields" in str(error).lower() or "unit" in str(error).lower()

        # Non-dict template
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(
                name="Test Chore",
                notificationMetadata={"templates": ["not_a_dict"]}
            )
        error = exc_info.value
        assert "must be an object" in str(error).lower()

    def test_notification_metadata_unit_validation(self):
        """Test that notification template unit must be 'm', 'h', or 'd'."""
        # Valid units
        for unit in ['m', 'h', 'd']:
            chore = ChoreCreate(
                name="Test Chore",
                notificationMetadata={"templates": [{"value": 1, "unit": unit}]}
            )
            assert chore.notificationMetadata["templates"][0]["unit"] == unit

        # Invalid units
        for invalid_unit in ['s', 'w', 'M', 'y', 'minute', 'hour', 'day']:
            with pytest.raises(ValidationError) as exc_info:
                ChoreCreate(
                    name="Test Chore",
                    notificationMetadata={"templates": [{"value": 1, "unit": invalid_unit}]}
                )
            error = exc_info.value
            assert "invalid unit" in str(error).lower() or invalid_unit in str(error)


class TestChoreCreateFrequencyMetadataValidation:
    """Test frequency metadata validation."""

    def test_frequency_metadata_days_validation(self):
        """Test that days must be lowercase full names."""
        # Valid days
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        chore = ChoreCreate(
            name="Test Chore",
            frequencyMetadata={"days": valid_days}
        )
        assert chore.frequencyMetadata["days"] == valid_days

        # Invalid day - abbreviated
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(
                name="Test Chore",
                frequencyMetadata={"days": ["mon"]}
            )
        error = exc_info.value
        assert "invalid day" in str(error).lower() or "lowercase full names" in str(error).lower()

        # Invalid day - not a day
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(
                name="Test Chore",
                frequencyMetadata={"days": ["notaday"]}
            )
        error = exc_info.value
        assert "invalid day" in str(error).lower()

    def test_frequency_metadata_weekpattern_validation(self):
        """Test that weekPattern must be one of the valid enum values."""
        # Valid patterns
        valid_patterns = ['every_week', 'week_of_month', 'week_of_quarter']
        for pattern in valid_patterns:
            chore = ChoreCreate(
                name="Test Chore",
                frequencyMetadata={"weekPattern": pattern}
            )
            assert chore.frequencyMetadata["weekPattern"] == pattern

        # Invalid patterns
        invalid_patterns = ['every_2_weeks', 'biweekly', 'monthly', 'week_of_year']
        for invalid_pattern in invalid_patterns:
            with pytest.raises(ValidationError) as exc_info:
                ChoreCreate(
                    name="Test Chore",
                    frequencyMetadata={"weekPattern": invalid_pattern}
                )
            error = exc_info.value
            assert "invalid weekpattern" in str(error).lower() or invalid_pattern in str(error)

    def test_frequency_metadata_timezone_validation(self):
        """Test that timezone must be a valid IANA timezone name."""
        # Valid timezones
        valid_timezones = [
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
            "UTC"
        ]
        for tz in valid_timezones:
            chore = ChoreCreate(
                name="Test Chore",
                frequencyMetadata={"timezone": tz}
            )
            assert chore.frequencyMetadata["timezone"] == tz

        # Invalid timezones (use completely invalid names)
        invalid_timezones = ["Invalid/Timezone", "Not_A_Real_Zone", "Fake/City"]
        for invalid_tz in invalid_timezones:
            with pytest.raises(ValidationError) as exc_info:
                ChoreCreate(
                    name="Test Chore",
                    frequencyMetadata={"timezone": invalid_tz}
                )
            error = exc_info.value
            assert "invalid timezone" in str(error).lower() or "iana" in str(error).lower()

    def test_frequency_metadata_time_format_validation(self):
        """Test that time must be in ISO format with timezone."""
        # Valid time format
        chore = ChoreCreate(
            name="Test Chore",
            frequencyMetadata={"time": "2025-11-10T14:00:00-05:00"}
        )
        assert "T" in chore.frequencyMetadata["time"]

        # Invalid time format (no 'T' separator)
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(
                name="Test Chore",
                frequencyMetadata={"time": "14:00:00"}
            )
        error = exc_info.value
        assert "iso format" in str(error).lower() or "must be iso" in str(error).lower()


class TestChoreCreateCompletionWindowValidation:
    """Test completion window validation."""

    def test_completion_window_validation_valid_range(self):
        """Test that valid completion window values are accepted."""
        valid_values = [0, 3600, 86400, 604800, 2592000]  # 0s, 1h, 1d, 1w, 30d in seconds
        for value in valid_values:
            chore = ChoreCreate(
                name="Test Chore",
                completionWindow=value
            )
            assert chore.completionWindow == value

    def test_completion_window_validation_negative_fails(self):
        """Test that negative completion window values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(
                name="Test Chore",
                completionWindow=-1
            )
        error = exc_info.value
        assert "completionwindow" in str(error).lower()
        assert ("greater than or equal to 0" in str(error).lower() or
                "non-negative" in str(error).lower())

    def test_completion_window_validation_exceeds_max_fails(self):
        """Test that completion window cannot exceed 1 year."""
        # 1 year in seconds = 31536000
        max_allowed = 31536000

        # At the limit should work
        chore = ChoreCreate(
            name="Test Chore",
            completionWindow=max_allowed
        )
        assert chore.completionWindow == max_allowed

        # Above the limit should fail
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(
                name="Test Chore",
                completionWindow=max_allowed + 1
            )
        error = exc_info.value
        assert "completionwindow" in str(error).lower()
        assert "cannot exceed" in str(error).lower() or "1 year" in str(error).lower()

    def test_completion_window_validation_none_allowed(self):
        """Test that None is accepted for completion window (optional field)."""
        chore = ChoreCreate(name="Test Chore", completionWindow=None)
        assert chore.completionWindow is None


class TestChoreCreateDeadlineOffsetValidation:
    """Test deadline offset validation."""

    def test_deadline_offset_validation_valid_range(self):
        """Test that valid deadline offset values are accepted."""
        valid_values = [0, 3600, 86400, 604800, 31536000]  # Including 1 year
        for value in valid_values:
            chore = ChoreCreate(
                name="Test Chore",
                deadlineOffset=value
            )
            assert chore.deadlineOffset == value

    def test_deadline_offset_validation_negative_allowed(self):
        """Test that negative deadline offset values are allowed (unlike completionWindow)."""
        # Negative values should be allowed for deadlineOffset
        chore = ChoreCreate(
            name="Test Chore",
            deadlineOffset=-3600
        )
        assert chore.deadlineOffset == -3600

    def test_deadline_offset_validation_exceeds_max_fails(self):
        """Test that deadline offset cannot exceed 1 year."""
        max_allowed = 31536000  # 1 year in seconds

        # At the limit should work
        chore = ChoreCreate(
            name="Test Chore",
            deadlineOffset=max_allowed
        )
        assert chore.deadlineOffset == max_allowed

        # Above the limit should fail
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(
                name="Test Chore",
                deadlineOffset=max_allowed + 1
            )
        error = exc_info.value
        assert "deadlineoffset" in str(error).lower()
        assert "cannot exceed" in str(error).lower() or "1 year" in str(error).lower()


class TestChoreCreateNameValidation:
    """Test name field validation and sanitization."""

    def test_name_validation_empty_fails(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(name="")
        error = exc_info.value
        assert "name" in str(error).lower()

    def test_name_validation_whitespace_only_fails(self):
        """Test that whitespace-only name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(name="   ")
        error = exc_info.value
        assert "cannot be empty" in str(error).lower() or "whitespace" in str(error).lower()

    def test_name_validation_control_characters_removed(self):
        """Test that control characters are removed from name."""
        # Control character (ASCII 1-31 except tab/newline)
        name_with_control = "Test\x01Chore\x02Name"
        chore = ChoreCreate(name=name_with_control)
        # Control characters should be stripped
        assert "\x01" not in chore.name
        assert "\x02" not in chore.name
        assert "Test" in chore.name and "Chore" in chore.name

    def test_name_validation_max_length(self):
        """Test that name cannot exceed 200 characters."""
        # 200 characters should pass
        chore = ChoreCreate(name="A" * 200)
        assert len(chore.name) == 200

        # 201 characters should fail
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(name="A" * 201)
        error = exc_info.value
        assert "name" in str(error).lower()
        assert "200" in str(error)


class TestChoreCreateDueDateValidation:
    """Test due date validation."""

    def test_duedate_validation_rfc3339_format(self):
        """Test that RFC3339 format is accepted."""
        valid_dates = [
            "2025-11-10T00:00:00Z",
            "2025-11-10T14:30:00-05:00",
            "2025-12-25T23:59:59+00:00"
        ]
        for date_str in valid_dates:
            chore = ChoreCreate(name="Test Chore", dueDate=date_str)
            assert chore.dueDate == date_str

    def test_duedate_validation_iso_date_format(self):
        """Test that simple YYYY-MM-DD format is accepted."""
        chore = ChoreCreate(name="Test Chore", dueDate="2025-11-10")
        assert chore.dueDate == "2025-11-10"

    def test_duedate_validation_invalid_format_fails(self):
        """Test that invalid date formats are rejected."""
        invalid_dates = [
            "11/10/2025",  # US format
            "10-11-2025",  # Wrong separator
            "2025/11/10",  # Wrong separator
            "Nov 10, 2025",  # Text format
            "invalid"
        ]
        for invalid_date in invalid_dates:
            with pytest.raises(ValidationError) as exc_info:
                ChoreCreate(name="Test Chore", dueDate=invalid_date)
            error = exc_info.value
            assert "duedate" in str(error).lower() or "date" in str(error).lower()


class TestChoreCreateFrequencyTypeValidation:
    """Test frequency type validation."""

    @pytest.mark.parametrize("freq_type", [
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
    ])
    def test_frequency_type_validation_all_valid_types(self, freq_type):
        """Test that all valid frequency types are accepted."""
        chore = ChoreCreate(
            name="Test Chore",
            frequencyType=freq_type
        )
        assert chore.frequencyType == freq_type.lower()

    def test_frequency_type_validation_case_insensitive(self):
        """Test that frequency type validation is case-insensitive."""
        chore = ChoreCreate(
            name="Test Chore",
            frequencyType="WEEKLY"
        )
        assert chore.frequencyType == "weekly"

    def test_frequency_type_validation_invalid_fails(self):
        """Test that invalid frequency types are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChoreCreate(
                name="Test Chore",
                frequencyType="invalid_type"
            )
        error = exc_info.value
        assert "frequencytype" in str(error).lower() or "frequency type" in str(error).lower()
