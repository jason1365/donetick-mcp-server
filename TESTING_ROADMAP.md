# Testing Roadmap for Donetick MCP Server

## Current Status (v0.3.1)

**Test Coverage**: 57% (859 statements, 370 missing)
**Tests Passing**: 41/41 ✅
**Target Coverage**: 85-90%

### Coverage Breakdown
- `client.py`: 50% (349 statements, 176 missing) ⚠️ **CRITICAL GAPS**
- `server.py`: 42% (243 statements, 140 missing) ⚠️ **CRITICAL GAPS**
- `models.py`: 80% (226 statements, 45 missing) ✅ Good
- `config.py`: 78% (40 statements, 9 missing) ✅ Good
- `__init__.py`: 100% ✅ Full coverage

---

## Phase 2: Expand test_client.py (~30 new tests)

### Priority: HIGH
**Estimated Time**: 3-4 hours
**Target Coverage**: client.py 50% → 85%

### 2.1 User Management Tests (6 tests)
**New in v0.3.0 - Currently 0% coverage**

```python
# tests/test_client.py

async def test_list_users_success(httpx_mock):
    """Test listing all circle users."""
    httpx_mock.add_response(
        method="GET",
        url="https://test.com/api/v1/users/",
        json=[
            {"id": 1, "username": "alice", "displayName": "Alice Smith"},
            {"id": 2, "username": "bob", "displayName": "Bob Jones"}
        ]
    )
    # Assert 2 users returned with correct data

async def test_list_users_empty(httpx_mock):
    """Test listing users when circle is empty."""
    # Return empty array, assert no errors

async def test_list_users_wrapped_response(httpx_mock):
    """Test handling wrapped response format."""
    # Return {"users": [...]} or {"res": [...]}

async def test_get_user_profile_success(httpx_mock):
    """Test getting current user profile."""
    # Mock profile response with all fields

async def test_get_user_profile_wrapped(httpx_mock):
    """Test profile with wrapped response."""
    # Return {"res": {profile}}

async def test_get_user_profile_401_refresh(httpx_mock):
    """Test automatic JWT refresh on 401."""
    # First call 401, refresh token, retry success
```

### 2.2 Label Management Tests (12 tests)
**Currently 0% coverage**

```python
async def test_get_labels_success(httpx_mock):
    """Test fetching all labels."""

async def test_create_label_success(httpx_mock):
    """Test creating new label."""

async def test_create_label_duplicate_name(httpx_mock):
    """Test creating label with duplicate name."""
    # Should handle 409 Conflict

async def test_update_label_success(httpx_mock):
    """Test updating existing label."""

async def test_update_label_not_found(httpx_mock):
    """Test updating non-existent label."""
    # Should handle 404

async def test_delete_label_success(httpx_mock):
    """Test deleting label."""

async def test_delete_label_in_use(httpx_mock):
    """Test deleting label that's in use."""
    # May return error or succeed with warning

async def test_lookup_label_ids_all_found(httpx_mock):
    """Test label lookup when all labels exist."""

async def test_lookup_label_ids_partial_match(httpx_mock):
    """Test label lookup with some missing."""

async def test_lookup_label_ids_none_found(httpx_mock):
    """Test label lookup when no labels exist."""

async def test_lookup_label_ids_empty_input(httpx_mock):
    """Test label lookup with empty array."""

async def test_lookup_label_ids_case_insensitive(httpx_mock):
    """Test label lookup is case-insensitive."""
```

### 2.3 Circle Members Tests (3 tests)

```python
async def test_get_circle_members_success(httpx_mock):
    """Test fetching circle members."""

async def test_get_circle_members_empty(httpx_mock):
    """Test handling empty circle."""

async def test_lookup_user_ids_validation(httpx_mock):
    """Test username lookup with validation."""
```

### 2.4 Transformation Function Tests (5 tests)

```python
def test_transform_frequency_metadata_invalid_days():
    """Test frequency transform with invalid day names."""
    # Should raise ValueError with clear message

def test_transform_frequency_metadata_empty_days():
    """Test frequency transform with empty days array."""
    # Should raise ValueError

def test_transform_frequency_metadata_mixed_case():
    """Test day name normalization (Mon, monday, MONDAY)."""

def test_transform_notification_metadata_max_templates():
    """Test notification with >5 templates."""
    # Should handle gracefully or warn

def test_calculate_due_date_edge_cases():
    """Test due date calculation with edge cases."""
```

### 2.5 Additional Error Handling Tests (4 tests)

```python
async def test_json_decode_error_handling(httpx_mock):
    """Test handling malformed JSON response."""
    # Return invalid JSON, assert ValueError

async def test_timeout_with_retry(httpx_mock):
    """Test timeout retry with exponential backoff."""

async def test_5xx_error_retry(httpx_mock):
    """Test retry on 500/502/503 errors."""

async def test_cache_clear(client):
    """Test cache clearing functionality."""
```

---

## Phase 3: Expand test_server.py (~25 new tests)

### Priority: HIGH
**Estimated Time**: 3-4 hours
**Target Coverage**: server.py 42% → 80%

### 3.1 Label Tool Tests (8 tests)

```python
async def test_list_labels_tool(mcp_server, httpx_mock):
    """Test list_labels MCP tool."""

async def test_list_labels_empty(mcp_server, httpx_mock):
    """Test list_labels with no labels."""

async def test_create_label_tool(mcp_server, httpx_mock):
    """Test create_label MCP tool."""

async def test_create_label_invalid_color(mcp_server, httpx_mock):
    """Test create_label with invalid color format."""

async def test_update_label_tool(mcp_server, httpx_mock):
    """Test update_label MCP tool."""

async def test_update_label_not_found(mcp_server, httpx_mock):
    """Test update_label with non-existent ID."""

async def test_delete_label_tool(mcp_server, httpx_mock):
    """Test delete_label MCP tool."""

async def test_delete_label_not_found(mcp_server, httpx_mock):
    """Test delete_label with non-existent ID."""
```

### 3.2 User/Member Tool Tests (6 tests)

```python
async def test_get_circle_members_tool(mcp_server, httpx_mock):
    """Test get_circle_members MCP tool."""

async def test_get_circle_members_formatting(mcp_server, httpx_mock):
    """Test formatted output with points and roles."""

async def test_list_circle_users_tool(mcp_server, httpx_mock):
    """Test list_circle_users MCP tool."""

async def test_list_circle_users_empty(mcp_server, httpx_mock):
    """Test list_circle_users with no users."""

async def test_get_user_profile_tool(mcp_server, httpx_mock):
    """Test get_user_profile MCP tool."""

async def test_get_user_profile_formatting(mcp_server, httpx_mock):
    """Test profile output formatting."""
```

### 3.3 Complex Chore Creation Tests (5 tests)

```python
async def test_create_chore_with_invalid_usernames(mcp_server, httpx_mock):
    """Test chore creation with non-existent usernames."""
    # Should return error message with hint

async def test_create_chore_with_invalid_labels(mcp_server, httpx_mock):
    """Test chore creation with non-existent labels."""
    # Should return error message with hint

async def test_create_chore_all_assignstrategies(mcp_server, httpx_mock):
    """Test chore creation with all 7 assignStrategy values."""
    # Iterate through all strategies

async def test_create_chore_priority_validation(mcp_server, httpx_mock):
    """Test priority validation (0-4 only)."""
    # Try priority=5, should fail validation

async def test_create_chore_frequency_transformation(mcp_server, httpx_mock):
    """Test natural language frequency → API format."""
    # Test "Mon, Wed, Fri" → days_of_the_week
```

### 3.4 Comprehensive Error Handling (6 tests)

```python
async def test_http_401_authentication_error(mcp_server, httpx_mock):
    """Test handling 401 authentication errors."""

async def test_http_403_forbidden_error(mcp_server, httpx_mock):
    """Test handling 403 forbidden errors."""

async def test_http_404_not_found_formatting(mcp_server, httpx_mock):
    """Test user-friendly 404 error messages."""

async def test_http_422_validation_error(mcp_server, httpx_mock):
    """Test handling 422 validation errors."""

async def test_http_429_rate_limit(mcp_server, httpx_mock):
    """Test handling 429 rate limit errors."""

async def test_http_500_server_error(mcp_server, httpx_mock):
    """Test handling 500 server errors."""
```

---

## Phase 4: Create test_models.py (~10 new tests)

### Priority: MEDIUM
**Estimated Time**: 1-2 hours
**Target Coverage**: models.py 80% → 95%

### 4.1 ChoreCreate Validation Tests

```python
def test_priority_validation_range():
    """Test priority must be 0-4."""
    # Try -1, 5, 100 - should raise ValueError

def test_assignstrategy_validation_all_values():
    """Test all 7 assignStrategy values validate."""

def test_assignstrategy_validation_invalid():
    """Test invalid strategy raises ValueError."""

def test_notification_metadata_template_limit():
    """Test notificationMetadata max 5 templates."""

def test_notification_metadata_template_structure():
    """Test template structure validation (value, unit)."""

def test_notification_metadata_unit_validation():
    """Test unit must be 'm', 'h', or 'd'."""

def test_frequency_metadata_days_validation():
    """Test days must be lowercase full names."""

def test_frequency_metadata_weekpattern_validation():
    """Test weekPattern enum validation."""

def test_frequency_metadata_timezone_validation():
    """Test timezone IANA format validation."""

def test_completion_window_validation():
    """Test completionWindow range validation."""
```

---

## Phase 5: Create test_transformations.py (~15 new tests)

### Priority: MEDIUM
**Estimated Time**: 2-3 hours
**Target Coverage**: client.py transformation functions

### 5.1 Frequency Transformation Edge Cases

```python
def test_frequency_transform_days_of_week_all_days():
    """Test with all 7 days specified."""

def test_frequency_transform_invalid_day_raises_error():
    """Test invalid day name raises ValueError (not warning)."""

def test_frequency_transform_empty_days_raises_error():
    """Test empty days array raises ValueError."""

def test_frequency_transform_timezone_handling():
    """Test timezone offset in time field."""

def test_frequency_transform_unit_and_weekpattern():
    """Test unit='days' and weekPattern='every_week' added."""
```

### 5.2 Subtask Transformation

```python
def test_transform_subtasks_ordering():
    """Test subtasks get orderId field."""

def test_transform_subtasks_empty_array():
    """Test empty subtasks array."""

def test_transform_subtasks_name_sanitization():
    """Test subtask names are sanitized."""
```

### 5.3 Due Date Calculation

```python
def test_calculate_due_date_today():
    """Test due date calculation for 'today'."""

def test_calculate_due_date_tomorrow():
    """Test due date calculation for 'tomorrow'."""

def test_calculate_due_date_specific_date():
    """Test due date with specific date."""

def test_calculate_due_date_with_time():
    """Test due date with time component."""
```

### 5.4 Notification Transformation

```python
def test_notification_transform_multiple_reminders():
    """Test combining offset, due time, and nagging."""

def test_notification_transform_edge_cases():
    """Test zero offset, negative offset."""

def test_notification_transform_units():
    """Test 'm', 'h', 'd' units."""
```

---

## Phase 6: Integration & Performance Tests

### Priority: LOW
**Estimated Time**: 2-3 hours

### 6.1 End-to-End Workflows

```python
async def test_full_chore_lifecycle():
    """Test create → get → update → complete → delete."""

async def test_label_workflow():
    """Test create label → use in chore → delete label."""

async def test_user_lookup_and_assignment():
    """Test username lookup → assign → rotate."""
```

### 6.2 Performance Tests

```python
async def test_rate_limiting_respected():
    """Test rate limiter enforces 10 req/sec."""

async def test_concurrent_requests_handling():
    """Test multiple concurrent API calls."""

async def test_cache_performance():
    """Test get_chore cache hit performance."""
```

---

## Implementation Strategy

### Recommended Order:
1. **Phase 2** (test_client.py) - Highest impact on coverage
2. **Phase 3** (test_server.py) - Critical MCP tool coverage
3. **Phase 4** (test_models.py) - Validation edge cases
4. **Phase 5** (test_transformations.py) - Transformation logic
5. **Phase 6** (Integration) - Nice to have

### Test Writing Guidelines:
- Follow existing test patterns in test_client.py and test_server.py
- Use `httpx_mock` for all HTTP mocking
- Use descriptive test names: `test_<component>_<scenario>_<expected_result>`
- Include docstrings explaining what's being tested
- Test both success and error paths
- Use parameterized tests for multiple similar scenarios

### Expected Coverage After All Phases:
- **client.py**: 50% → 85% (+35%)
- **server.py**: 42% → 80% (+38%)
- **models.py**: 80% → 95% (+15%)
- **Overall**: 57% → 88% (+31%)

### Total Tests After All Phases:
- **Current**: 41 tests
- **After Phases 2-5**: ~121 tests (+80)
- **After Phase 6**: ~130 tests (+89)

---

## Quick Wins (1-2 hours, +10% coverage)

If time is limited, prioritize these high-impact tests:

1. **User management** (list_users, get_user_profile) - 6 tests, +5% coverage
2. **Label validation** (missing label error handling) - 3 tests, +2% coverage
3. **AssignStrategy validation** (all 7 values) - 2 tests, +1% coverage
4. **Priority range** (0-4 validation) - 2 tests, +1% coverage
5. **Notification template limit** (max 5) - 2 tests, +1% coverage

**Total Quick Wins**: 15 tests in 1-2 hours → +10% coverage (57% → 67%)

---

## Notes for Future Contributors

### Test File Organization:
- `tests/test_client.py` - API client unit tests (HTTP mocking)
- `tests/test_server.py` - MCP server integration tests
- `tests/test_models.py` - Pydantic validation tests (NEW)
- `tests/test_transformations.py` - Transformation logic tests (NEW)
- `tests/test_notification_transform.py` - Already exists ✅

### Common Patterns:

**Mocking HTTP responses:**
```python
httpx_mock.add_response(
    method="GET",
    url="https://test.com/api/v1/endpoint",
    json={"key": "value"}
)
```

**Testing MCP tools:**
```python
result = await mcp_server.call_tool("tool_name", {"param": "value"})
assert isinstance(result, list)
assert result[0].type == "text"
```

**Testing validators:**
```python
with pytest.raises(ValueError, match="must be one of"):
    ChoreCreate(assignStrategy="invalid")
```

### Running Tests:
```bash
# All tests
pytest tests/ -v

# Specific file
pytest tests/test_client.py -v

# With coverage
pytest --cov=donetick_mcp --cov-report=html tests/

# Coverage report
open htmlcov/index.html
```

---

## Continuous Improvement

### Ongoing Maintenance:
- Run tests before every commit: `pytest tests/`
- Check coverage quarterly: Target >85%
- Add tests for every bug fix
- Add tests for every new feature
- Review test failures in CI/CD

### Future Enhancements:
- Add performance benchmarks
- Add load testing for rate limiter
- Add fuzzing tests for input validation
- Add property-based testing with Hypothesis
- Add mutation testing with mutmut

---

**Last Updated**: v0.3.1 (2025-11-04)
**Baseline Coverage**: 57% (41 tests)
**Target Coverage**: 85-90% (120-130 tests)
