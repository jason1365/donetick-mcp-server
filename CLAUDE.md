# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server for Donetick chores management. It enables Claude and other MCP-compatible AI assistants to interact with a Donetick instance through a rate-limited API.

**Key Technologies:**
- Python 3.11+
- MCP SDK (>=1.20.0)
- httpx for async HTTP
- Pydantic for data validation
- Docker for containerization

## Project Structure

The project follows a clean directory structure:

```
donetick-mcp-server/
├── src/donetick_mcp/       # Source code
│   ├── server.py           # MCP server implementation
│   ├── client.py           # API client with rate limiting
│   ├── models.py           # Pydantic data models
│   └── config.py           # Configuration management
├── tests/                  # Formal test suite (pytest)
│   ├── test_client.py      # Unit tests for API client
│   └── test_server.py      # Integration tests for MCP server
├── tmp/                    # Temporary files (gitignored)
│   └── *.py                # Ad-hoc testing, analysis, verification scripts
├── .gitignore              # Excludes tmp/, venv/, build artifacts
└── pyproject.toml          # Project dependencies and metadata
```

**Important Conventions**:
- **Source code**: Always in `src/donetick_mcp/`
- **Formal tests**: Always in `tests/` (run via pytest)
- **Temporary files**: Always in `tmp/` for analysis, verification, one-off testing
- **Never commit**: Files in `tmp/` are gitignored - use for local experimentation only

When creating test scripts for verification or analysis, always place them in `tmp/` to keep the project root clean. The formal test suite in `tests/` should be reserved for permanent, repeatable tests that are part of CI/CD.

## Development Commands

### Setup & Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install for development
pip install -e ".[dev]"

# Install production only
pip install -e .
```

### Running the Server

```bash
# Run directly with Python
python -m donetick_mcp.server

# Or use entry point
donetick-mcp

# Run with Docker
docker-compose up -d

# View Docker logs
docker-compose logs -f donetick-mcp

# Stop Docker
docker-compose down
```

### Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_client.py
pytest tests/test_server.py

# Run with coverage
pytest --cov=donetick_mcp --cov-report=html

# Run single test
pytest tests/test_client.py::test_list_chores -v
```

### Linting & Formatting

```bash
# Check code with ruff
ruff check src/

# Format code with ruff
ruff format src/
```

## Architecture

### High-Level Structure

The codebase follows a clean separation of concerns:

```
┌─────────────────┐
│   MCP Server    │ ← server.py: Exposes 5 tools to Claude
│   (server.py)   │   Handles tool registration & execution
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Donetick API   │ ← client.py: HTTP client wrapper
│  Client         │   Rate limiting, retry logic, auth
│  (client.py)    │   Connection pooling
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Pydantic       │ ← models.py: Type-safe data models
│  Models         │   Request/response validation
│  (models.py)    │
└─────────────────┘
```

### Key Components

#### 1. MCP Server (server.py)

- **Purpose**: Exposes Donetick functionality as MCP tools
- **Transport**: stdio (for Claude Desktop integration)
- **Global State**: Maintains a single `DonetickClient` instance
- **Tools Exposed (20 tools)**:
  - **Chore Management (10 tools)**:
    - `list_chores`: List with filters (active status, assigned user), supports `detail_level` for brief/full responses
    - `get_chore`: Get by ID (uses direct GET endpoint, includes sub-tasks)
    - `create_chore`: Create new chore (supports sub-tasks)
    - `complete_chore`: Mark complete (Premium feature)
    - `update_chore`: Update basic fields (name, description, due date)
    - `update_chore_priority`: Update priority level (0-4)
    - `update_chore_assignee`: Reassign chore to different user
    - `delete_chore`: Delete chore (creator only)
    - `skip_chore`: Skip chore without marking complete (reschedule next occurrence)
    - `update_subtask_completion`: Mark individual subtasks complete/incomplete with progress tracking
  - **Label Management (4 tools)**:
    - `list_labels`: List all labels in the circle
    - `create_label`: Create new custom label
    - `update_label`: Modify existing label
    - `delete_label`: Remove label
  - **Circle/User Management (3 tools)**:
    - `get_circle_members`: Get circle members with roles and points
    - `list_circle_users`: List all users in the circle
    - `get_user_profile`: Get current user's detailed profile
  - **History/Analytics (3 tools)**:
    - `get_chore_history`: Get completion history for a specific chore
    - `get_all_chores_history`: Get completion history across all chores (with pagination)
    - `get_chore_details`: Get detailed statistics and analytics for a chore

**Important**: The server uses a global client instance for connection pooling. Call `cleanup()` on shutdown to properly close resources.

#### 2. API Client (client.py)

- **HTTP Client**: Uses `httpx.AsyncClient` with connection pooling
- **Rate Limiting**: Token bucket algorithm (default: 10 req/sec)
- **Retry Logic**: Exponential backoff with jitter for 5xx errors and 429
- **Authentication**: Uses JWT Bearer tokens (automatically managed)
- **Context Manager**: Supports async with for resource cleanup

**Key Implementation Details**:
- Connection pool: max 100 connections, 50 keepalive
- Timeouts: 5s connect, 30s read, 5s write
- No retry on 4xx errors (except 429 rate limits)
- Direct GET endpoint for `get_chore` (includes sub-tasks via API Preload)
- Caching for individual chore fetches (60s TTL)

#### 3. Data Models (models.py)

All API interactions use Pydantic models for type safety:

- **ChoreCreate**: For creating chores (uses camelCase field names: `name`, `description`, `dueDate`, `createdBy`)
- **ChoreUpdate**: For updating chores (uses camelCase: `name`, `description`, `nextDueDate`)
- **Chore**: Complete chore model with all metadata
- **CircleMember**: Circle/household member details

**Consistency Note**: All operations use consistent camelCase field naming. The API accepts both PascalCase and camelCase, but we standardize on camelCase for consistency.

#### 4. Configuration (config.py)

Loads from environment variables via `.env` file:
- `DONETICK_BASE_URL` (required): Instance URL (must use HTTPS)
- `DONETICK_USERNAME` (required): Donetick username
- `DONETICK_PASSWORD` (required): Donetick password
- `LOG_LEVEL` (optional): DEBUG, INFO, WARNING, ERROR
- `RATE_LIMIT_PER_SECOND` (optional): Default 10.0
- `RATE_LIMIT_BURST` (optional): Default 10

## Donetick API Quirks & Gotchas

### 1. JWT Token Management
Uses standard JWT Bearer authentication with automatic token management:
```python
headers = {"Authorization": f"Bearer {jwt_token}"}
```

**Token Lifecycle**:
- Initial login on server startup with username/password
- JWT token stored in memory (never persisted to disk)
- Automatic refresh before expiration (typically 24h lifetime)
- Transparent re-authentication on token expiry
- No manual token management required

**Security Considerations**:
- Credentials stored only in environment variables
- Tokens kept in memory only
- HTTPS required for all API calls
- Certificate verification enforced

### 2. API Endpoints (Full API)
Uses the Full API (not external API/eAPI):
- **List Chores**: `GET /api/v1/chores/` (does NOT include sub-tasks)
- **Get Chore**: `GET /api/v1/chores/{id}` (includes sub-tasks via Preload)
- **Create Chore**: `POST /api/v1/chores/` (supports sub-tasks)
- **Update Chore**: `PUT /api/v1/chores/` (IMPORTANT: ID in body, not URL! Returns message-only response)
- **Update Priority**: `PUT /api/v1/chores/{id}/priority` (change priority level)
- **Update Assignee**: `PUT /api/v1/chores/{id}/assignee` (reassign to different user)
- **Skip Chore**: `PUT /api/v1/chores/{id}/skip` (skip recurring without marking complete)
- **Complete Chore**: `POST /api/v1/chores/{id}/do` (mark as complete)
- **Delete Chore**: `DELETE /api/v1/chores/{id}`
- **Get Members**: `GET /api/v1/circles/members/` (get circle members with roles)

**Important**: Note the trailing slashes in list endpoints (`/api/v1/chores/`, `/api/v1/circles/members/`) and `/v1/` prefix - required for proper routing!

**Update Chore Implementation Details**:
The `update_chore` endpoint (`PUT /api/v1/chores/`) uses a non-RESTful pattern:
1. Chore ID is in the **request body**, not the URL path
2. Requires the **full chore object**, not just updated fields
3. Returns `{"message": "Chore added successfully"}` instead of the updated chore
4. Implementation uses fetch-modify-send pattern:
   - Fetch current chore with `GET /api/v1/chores/{id}`
   - Apply updates to the full chore object
   - Remove problematic metadata fields (createdAt, updatedAt, assignees, etc.)
   - Send complete object to `PUT /api/v1/chores/`
   - Fetch updated chore to return to caller
5. **Sub-tasks are preserved**: New sub-tasks use negative IDs (-1, -2, etc.) which the API converts to positive IDs

### 3. Assignee Constraint and Workflow

**IMPORTANT API CONSTRAINT**: If a chore has `assignedTo` set (not null), that user ID **MUST** be present in the `assignees` array. The API validates this and returns `400 Bad Request` with error `"Assigned to not found in assignees"` if violated.

**Why This Matters**:
- When updating chores, you might encounter chores with inconsistent assignee data
- The MCP server automatically fixes this by adding `assignedTo` to `assignees` if missing
- This prevents the `400 Bad Request` error during updates

**Getting Valid User IDs**:
Before assigning chores, you need to know which user IDs are valid for your circle. Use these tools:

1. **list_circle_users** - Get all users in the circle with their IDs
   ```python
   users = await client.list_circle_users()
   # Returns list of User objects with id, username, displayName
   ```

2. **get_circle_members** - Get detailed member information with roles and points
   ```python
   members = await client.get_circle_members()
   # Returns list of CircleMember objects with user info, role, points
   ```

**Assignment Workflow**:
```python
# 1. Get available users
users = await client.list_circle_users()
tyler_id = next(u.id for u in users if u.username == "tyler")

# 2. Create chore with assignment
chore = await client.create_chore(ChoreCreate(
    name="Homework",
    assignedTo=tyler_id,  # Single user assigned
    assignees=[tyler_id], # Must include assignedTo!
))

# 3. Update assignment
# The client automatically ensures assignedTo is in assignees
update = ChoreUpdate(assignedTo=tyler_id)
chore = await client.update_chore(chore.id, update)
```

**Common Errors**:
- `"Assigned to not found in assignees"` - assignedTo is set but not in assignees array
  - **Fix**: The MCP client handles this automatically for update_chore
  - **When creating**: Always include assignedTo in the assignees list
- `"User not found"` - Invalid user ID that doesn't exist in the circle
  - **Fix**: Use list_circle_users to get valid IDs

### 4. Field Name Consistency
All operations use camelCase consistently:
- **Create**: camelCase (`name`, `description`, `dueDate`, `createdBy`)
- **Update**: camelCase (`name`, `description`, `nextDueDate`)
- **Response**: camelCase for all fields

**API Flexibility**: The Donetick API accepts both PascalCase and camelCase in requests, but we standardize on camelCase for consistency and maintainability.

### 5. Date Format
Accepts both formats:
- ISO date: `2025-11-10`
- RFC3339: `2025-11-10T00:00:00Z`

### 6. All Features Supported
The Full API (/api/v1/) supports all Donetick features:
- Frequency metadata (specific days/times)
- Rolling schedules
- Multiple assignees
- Assignment strategies (7 strategies supported)
- Nagging notifications
- Pre-due notifications
- Private chores
- Points/gamification
- Priority levels (0-4 range)
- Completion window
- Require approval
- Labels (create, update, delete, assign)
- **Sub-tasks** (checklist items with ordering and completion tracking)

**Note**: All features are available through the full API. No Premium/Plus membership restrictions.

## Testing Strategy

The test suite uses multiple testing approaches:

### 1. Unit Tests (test_client.py)
Test each API method in isolation with mocked HTTP responses:
- Rate limiting behavior
- Retry logic with exponential backoff
- Error handling (4xx, 5xx, timeouts)
- Direct GET endpoint for get_chore with caching
- Field casing verification
- Endpoint routing with trailing slashes

**Running**: `pytest tests/test_client.py` (requires no Donetick instance)

### 2. Integration Tests (test_server.py)
Test MCP tool execution with mocked HTTP responses:
- Tool registration and discovery
- Tool invocation with various parameters
- Error responses and handling
- JSON serialization and response formatting

**Running**: `pytest tests/test_server.py` (requires no Donetick instance)

### 3. Live API Integration Tests (tests/integration/test_live_api.py)
Test against a real Donetick instance to verify:
- End-to-end chore operations (create, list, get, update, delete)
- API endpoint correctness and trailing slash requirements
- Field casing compatibility (both PascalCase and camelCase)
- Response formats match expected schemas
- Pagination and filtering functionality
- Error handling with real API responses

**Running Live Tests**:
```bash
# Requires .env file with Donetick credentials
pytest tests/integration/test_live_api.py -v

# Run only live tests
pytest -m live_api

# Run without live tests
pytest -m "not live_api"
```

**Live Test Markers**: Tests marked with `@pytest.mark.live_api` require a real Donetick instance and are skipped in CI/CD by default.

### Test Coverage

**Full Mocked Suite** (no Donetick needed):
- 85%+ code coverage
- Fast execution (~2 seconds)
- Safe to run in CI/CD

**With Live API** (requires Donetick instance):
- Additional coverage for API compatibility
- Verifies endpoint routing and field casing
- Validates response formats against real API
- Recommended after major changes

## Common Development Tasks

### Adding a New Tool

1. Add tool definition to `server.py:list_tools()`
2. Add handler in `server.py:call_tool()`
3. Add corresponding method to `client.py:DonetickClient`
4. Create Pydantic models if needed in `models.py`
5. Add tests in `tests/test_server.py` and `tests/test_client.py`

### Modifying Rate Limits

Rate limiting is configured in two places:
- **Default**: `config.py` (10 req/sec)
- **Override**: Environment variables or `DonetickClient` constructor

The token bucket refills continuously, so burst capacity = sustained rate.

### Debugging API Issues

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m donetick_mcp.server
```

This logs:
- Every HTTP request (method, URL, attempt number)
- Rate limiting waits
- Retry backoff delays
- Response status codes

### Understanding the Async Context

The client uses async/await throughout:
- Always use `await client.method()` for API calls
- The global client is created lazily on first `get_client()` call
- Call `await cleanup()` on server shutdown to close connections
- Tests use `pytest-asyncio` with `asyncio_mode = "auto"`

## Docker Deployment

The Dockerfile uses multi-stage builds:
1. **Base**: Python 3.11-slim with system dependencies
2. **Builder**: Installs Python packages
3. **Runtime**: Non-root user, minimal attack surface

Security features:
- Runs as non-root user (UID 1000)
- `no-new-privileges` security option
- Resource limits (1 CPU, 512MB RAM)
- Optional read-only filesystem

## Claude Desktop Integration

Add to `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "donetick": {
      "command": "docker",
      "args": [
        "exec", "-i", "donetick-mcp-server",
        "python", "-m", "donetick_mcp.server"
      ]
    }
  }
}
```

Or for Python direct:
```json
{
  "mcpServers": {
    "donetick": {
      "command": "python",
      "args": ["-m", "donetick_mcp.server"],
      "env": {
        "DONETICK_BASE_URL": "https://your-instance.com",
        "DONETICK_USERNAME": "your_username",
        "DONETICK_PASSWORD": "your_password"
      }
    }
  }
}
```

## Important File Locations

- `src/donetick_mcp/server.py:34-150` - Tool definitions
- `src/donetick_mcp/server.py:153-252` - Tool handlers
- `src/donetick_mcp/client.py:118-199` - HTTP retry logic
- `src/donetick_mcp/client.py:17-56` - Token bucket rate limiter
- `src/donetick_mcp/models.py:31-170` - ChoreCreate model (camelCase fields)
- `src/donetick_mcp/models.py:171-200` - ChoreUpdate model
- `src/donetick_mcp/models.py:201-280` - Complete Chore model
- `tests/test_client.py` - Client unit tests with mocked HTTP
- `tests/test_server.py` - MCP server integration tests
- `tests/integration/test_live_api.py` - Live API integration tests

## Recent Enhancements

### v0.3.4 - Update Chore Bug Fix

**Bug Fix (2025-11-04)**:
- **Fixed update_chore HTML response error**: The `update_chore` method was using the wrong API endpoint pattern, causing it to return HTML instead of JSON
- **Root cause**: Was using `PUT /api/v1/chores/{id}` which doesn't exist. The correct endpoint is `PUT /api/v1/chores/` with the ID in the request body
- **Implementation changes**:
  - Changed to fetch-modify-send pattern: fetch current chore, apply updates, send full object
  - Remove problematic metadata fields (createdAt, updatedAt, assignees, etc.) that cause validation errors
  - Handle message-only API response: `{"message": "Chore added successfully"}`
  - Fetch updated chore after API call to return to caller
- **Sub-task preservation**: New sub-tasks with negative IDs (-1, -2, etc.) are correctly handled by the API
- **Documentation**: Added comprehensive update_chore implementation details to CLAUDE.md
- **Testing**: Verified with live API test against real Donetick instance

**Technical Details**:
- File: [src/donetick_mcp/client.py:395-459](src/donetick_mcp/client.py#L395-L459)
- The Donetick API uses a non-RESTful pattern for updates: ID in body, not URL
- Full chore object required, not just updated fields
- API returns message confirmation instead of updated object

### v0.4.0 - Phase 1 Foundation Complete

**Phase 1 Migration Completed (2025-11-04)**:
- **Verified field casing**: API accepts both PascalCase and camelCase; we standardize on camelCase
- **Full API migration**: Migrated all endpoints from eAPI to /api/v1/ with proper trailing slashes
- **Trailing slash enforcement**: All list endpoints (`/api/v1/chores/`, `/api/v1/circles/members/`) now include trailing slashes
- **Removed unused aliases**: Removed 26 unused PascalCase field aliases from ChoreCreate model
- **Enhanced endpoint documentation**: Clarified endpoint routing with trailing slash requirements
- **Live API test framework**: Created comprehensive live API integration tests for validation
- **Updated documentation**: CLAUDE.md and README.md now reflect full API usage

**Key Changes**:
- All ChoreCreate fields use camelCase: `name`, `description`, `dueDate`, `createdBy`, etc.
- Endpoints use `/api/v1/` prefix consistently
- List endpoints require trailing slashes: `GET /api/v1/chores/`, `GET /api/v1/circles/members/`
- Update endpoints use specific paths: `/priority`, `/assignee`, `/skip`, `/do`
- Full API supports all features (no Premium restriction language)

### v0.3.2 - Chore Update & Skip Operations

**New in v0.3.2**:
- Added `update_chore` tool for editing basic chore details (name, description, due date)
- Added `update_chore_priority` tool for changing chore priority (0-4 range)
- Added `update_chore_assignee` tool for reassigning chores to different users
- Added `skip_chore` tool for skipping recurring chores without marking complete
- Comprehensive analysis and documentation of API design differences between create and update operations
- Full test coverage for all new tools (4 client + 4 server tests)
- Total tool count increased from 13 to 16 MCP tools

**Key Feature**: These tools expose the specialized Donetick API endpoints that follow domain-driven design principles:
- Generic `update_chore` for basic edits (name, description, due_date only)
- Specialized `update_chore_priority` for priority changes
- Specialized `update_chore_assignee` for assignment rotation
- `skip_chore` for recurring chore management without completion

### v0.3.1 - Validation Improvements

**New in v0.3.1** (Bug Fixes):
- **Fixed priority range**: Now correctly 0-4 (was incorrectly 1-5)
- **Added 4 missing assignStrategy values**: Now supports all 7 strategies (least_assigned, keep_last_assigned, random_except_last_assigned, no_assignee)
- **Enhanced error messages**: Username and label lookups now fail with helpful guidance instead of silent warnings
- **Stricter validation**: Invalid day names now raise errors instead of being silently ignored
- **Template limit enforcement**: notificationMetadata now validates max 5 templates
- **Units clarification**: completionWindow and deadlineOffset documented as SECONDS (not days)
- **Comprehensive validators**: Added validation for frequencyMetadata structure (days, weekPattern, time, timezone)

### v0.3.0 - User Management Tools

**New in v0.3.0**:
- Added `list_circle_users` tool for viewing all circle members
- Added `get_user_profile` tool for detailed user profile information
- Enhanced user data models (User and UserProfile)
- Total tool count increased from 11 to 13 MCP tools

### Core Features (Full API)

**Authentication**:
1. **JWT Authentication**: Username/password authentication with automatic JWT token management
2. **Automatic Token Refresh**: Transparent re-authentication when tokens expire
3. **Secure Credential Storage**: Environment variables only, tokens never persisted to disk

**Chore Management Features**:
1. **Frequency Metadata**: Configure specific days and times for recurring chores
2. **Rolling Schedules**: Next due date based on completion vs fixed schedule
3. **Multiple Assignees**: Assign chores to multiple users simultaneously
4. **Assignment Strategies**: Control rotation (least_completed, round_robin, random)
5. **Nagging Notifications**: Send reminder notifications
6. **Pre-due Notifications**: Notify before due date
7. **Private Chores**: Hide chores from other circle members
8. **Points/Gamification**: Award points for chore completion
9. **Sub-tasks**: Add checklist items to chores
10. **Labels**: Custom color-coded tags for organization
11. **Priority Levels**: 0-4 priority system for task management

### Previous Enhancements

#### v0.2.0 - Security & Performance

**Security Improvements**:
1. **HTTPS Enforcement**: Config validation ensures all connections use HTTPS
2. **Sanitized Logging**: URLs and sensitive data are redacted from logs
3. **Secure Error Messages**: Error responses to users don't leak internal details
4. **Input Validation**: All user inputs are validated and sanitized
5. **Certificate Verification**: HTTPS certificates are verified by default
6. **Proper Cleanup**: Fixed resource leak in server shutdown

**Performance Improvements**:
1. **Smart Caching**: `get_chore` now caches results for 60 seconds (configurable)
2. **Optimized Connections**: Increased keepalive connections from 20 to 50
3. **Extended Keepalive**: Connection expiry increased from 5s to 30s

**Feature Completeness**:
1. **100% API Coverage**: All 26+ chore creation parameters now supported
2. **Field Validation**: Pydantic validators for dates, frequency types, strategies
3. **Input Sanitization**: Control character removal, length limits
4. **Enhanced Error Handling**: Specific error messages for different HTTP status codes

## Known Limitations

1. **Circle Scoped**: All operations are scoped to the user's circle/household
2. **Credential Storage**: Username/password required in environment (consider using secrets management for production)
