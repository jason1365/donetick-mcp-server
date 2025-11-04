# Donetick MCP Server

[![PyPI version](https://badge.fury.io/py/donetick-mcp-server.svg)](https://pypi.org/project/donetick-mcp-server/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/badge/github-jason1365%2Fdonetick--mcp--server-blue?logo=github)](https://github.com/jason1365/donetick-mcp-server)

A production-ready Model Context Protocol (MCP) server for [Donetick](https://donetick.com) chores management. Enables Claude and other MCP-compatible AI assistants to interact with your Donetick instance through a secure, rate-limited API.

## Features

- **13 MCP Tools**: Complete chore management (list, get, create, complete, delete), label organization (list, create, update, delete), circle member information, user management (list circle users, get user profile)
- **Full Chore Configuration**: All 26+ fields now working including frequency metadata, rolling schedules, multiple assignees, assignment strategies, notifications, labels, priority, points, sub-tasks, and more
- **JWT Authentication**: Automatic token management with transparent refresh
- **Smart Caching**: Intelligent caching for get_chore operations (60s TTL by default)
- **Rate Limiting**: Token bucket algorithm prevents API overload
- **Retry Logic**: Exponential backoff with jitter for resilient operations
- **Async/Await**: Non-blocking operations using httpx
- **Input Validation**: Pydantic field validators with sanitization
- **Security Hardened**: HTTPS enforcement, sanitized logging, secure error messages, JWT token security
- **Docker Support**: Containerized deployment with security best practices
- **Comprehensive Testing**: Unit and integration tests with pytest
- **Type Safety**: Pydantic models for request/response validation

## Quick Start

**Easiest installation (Claude Code CLI):**

```bash
claude mcp add donetick uvx donetick-mcp-server@latest
```

Then configure your Donetick credentials when prompted.

**Or install manually with uvx:**

```bash
# Install uv (one-time setup)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to Claude Desktop config
# ~/.config/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "donetick": {
      "command": "uvx",
      "args": ["--refresh", "donetick-mcp-server"],
      "env": {
        "DONETICK_BASE_URL": "https://your-instance.com",
        "DONETICK_USERNAME": "your_username",
        "DONETICK_PASSWORD": "your_password"
      }
    }
  }
}
```

**Benefits:**
- ✅ No installation required - runs directly from PyPI
- ✅ Auto-updates with `--refresh` flag
- ✅ Isolated environment - no conflicts
- ✅ Works on Windows, macOS, Linux

## Requirements

- Donetick instance (self-hosted or cloud)
- Donetick account credentials (username and password)
- **For uvx method:** `uv` installed (see Quick Start)
- **For other methods:** Python 3.11 or higher

## Installation

### Option 1: uvx (Recommended - No Installation Required)

See [Quick Start](#quick-start) above.

The `--refresh` flag ensures you always get the latest version when Claude Desktop restarts.

### Option 2: Docker

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jason1365/donetick-mcp-server.git
   cd donetick-mcp-server
   ```

2. **Create `.env` file**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Configure environment variables**:
   ```env
   DONETICK_BASE_URL=https://your-instance.com
   DONETICK_USERNAME=your_username
   DONETICK_PASSWORD=your_password
   LOG_LEVEL=INFO
   ```

4. **Build and run**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

### Option 3: pip install (For System Integration)

If you want to install globally or in a virtual environment:

```bash
# Install from PyPI
pip install donetick-mcp-server

# Or install for development
git clone https://github.com/jason1365/donetick-mcp-server.git
cd donetick-mcp-server
pip install -e .

# Run the server
donetick-mcp-server
# Or: python -m donetick_mcp.server
```

Then configure Claude Desktop to use the installed command:

```json
{
  "mcpServers": {
    "donetick": {
      "command": "donetick-mcp-server",
      "env": {
        "DONETICK_BASE_URL": "https://your-instance.com",
        "DONETICK_USERNAME": "your_username",
        "DONETICK_PASSWORD": "your_password"
      }
    }
  }
}
```

## Authentication

The MCP server uses JWT-based authentication with your Donetick credentials.

**What You Need**:
- Your Donetick username (same as web login)
- Your Donetick password (same as web login)

**How It Works**:
1. Server logs in with your credentials on startup
2. JWT token received and stored in memory
3. Token automatically refreshed before expiration
4. No manual token management required

**Security**:
- Credentials stored only in environment variables or `.env` file
- JWT tokens kept in memory only (never persisted to disk)
- Automatic token refresh prevents session expiration
- HTTPS required for all connections

## Claude Desktop Integration

**Easiest Method - Claude Code CLI:**

```bash
claude mcp add donetick uvx donetick-mcp-server@latest
```

**Or manually edit the configuration file:**

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

### uvx Configuration (Recommended)

```json
{
  "mcpServers": {
    "donetick": {
      "command": "uvx",
      "args": ["--refresh", "donetick-mcp-server"],
      "env": {
        "DONETICK_BASE_URL": "https://your-instance.com",
        "DONETICK_USERNAME": "your_username",
        "DONETICK_PASSWORD": "your_password"
      }
    }
  }
}
```

**Note:** The `--refresh` flag automatically updates to the latest version.

### Docker Configuration

```json
{
  "mcpServers": {
    "donetick": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "donetick-mcp-server",
        "python",
        "-m",
        "donetick_mcp.server"
      ]
    }
  }
}
```

### pip install Configuration

```json
{
  "mcpServers": {
    "donetick": {
      "command": "donetick-mcp-server",
      "env": {
        "DONETICK_BASE_URL": "https://your-instance.com",
        "DONETICK_USERNAME": "your_username",
        "DONETICK_PASSWORD": "your_password"
      }
    }
  }
}
```

After updating the configuration, restart Claude Desktop.

## Available Tools

### 1. list_chores

List all chores with optional filtering.

**Parameters**:
- `filter_active` (boolean, optional): Filter by active status
- `assigned_to_user_id` (integer, optional): Filter by assigned user ID

**Example**:
```
List all active chores assigned to me
```

### 2. get_chore

Get details of a specific chore by ID.

**Parameters**:
- `chore_id` (integer, required): The chore ID

**Example**:
```
Show me details of chore 123
```

### 3. create_chore

Create a new chore with full configuration support.

**Basic Parameters**:
- `name` (string, required): Chore name (1-200 characters)
- `description` (string, optional): Chore description (max 5000 characters)
- `due_date` (string, optional): Due date in YYYY-MM-DD or RFC3339 format
- `created_by` (integer, optional): Creator user ID

**Recurrence/Frequency Parameters**:
- `frequency_type` (string, optional): How often chore repeats - "once", "daily", "weekly", "monthly", "yearly", "interval_based" (default: "once")
- `frequency` (integer, optional): Frequency multiplier, e.g., 1=weekly, 2=biweekly (default: 1)
- `frequency_metadata` (object, optional): Additional frequency config like `{"days": [1,3,5], "time": "09:00"}`
- `is_rolling` (boolean, optional): Rolling schedule (next due based on completion) vs fixed (default: false)

**User Assignment Parameters**:
- `assigned_to` (integer, optional): Primary assigned user ID
- `assignees` (array, optional): Multiple assignees as `[{"userId": 1}, {"userId": 2}]`
- `assign_strategy` (string, optional): Assignment strategy - "least_completed", "round_robin", "random" (default: "least_completed")

**Notification Parameters**:
- `notification` (boolean, optional): Enable notifications (default: false)
- `nagging` (boolean, optional): Enable nagging/reminder notifications (default: false)
- `predue` (boolean, optional): Enable pre-due date notifications (default: false)

**Organization Parameters**:
- `priority` (integer, optional): Priority level 1-5 (1=lowest, 5=highest)
- `labels` (array, optional): Label tags like `["cleaning", "outdoor"]`

**Status Parameters**:
- `is_active` (boolean, optional): Active status - inactive chores are hidden (default: true)
- `is_private` (boolean, optional): Private chore visible only to creator (default: false)

**Gamification Parameters**:
- `points` (integer, optional): Points awarded for completion

**Advanced Parameters**:
- `sub_tasks` (array, optional): Sub-tasks/checklist items

**Examples**:
```
Create a simple one-time chore:
Create a chore called "Take out trash" due on 2025-11-10

Create a recurring chore with notifications:
Create a weekly chore "Clean kitchen" every Monday at 9am with priority 4,
enable nagging notifications, and assign it to user 1

Create an advanced chore:
Create a chore "Grocery shopping" that repeats weekly on Mondays and Wednesdays,
assign to users 1 and 2 using round robin strategy, with priority 3,
labels "shopping" and "outdoor", and award 10 points
```

### 4. complete_chore

Mark a chore as complete.

**Parameters**:
- `chore_id` (integer, required): The chore ID
- `completed_by` (integer, optional): User ID who completed it

**Example**:
```
Mark chore 123 as complete
```

### 5. delete_chore

Delete a chore permanently. **Only the creator can delete**.

**Parameters**:
- `chore_id` (integer, required): The chore ID

**Example**:
```
Delete chore 123
```

### 6. get_circle_members

Get all members in your circle (household/team). Shows who you can assign chores to.

**Parameters**: None

**Returns**:
- User ID
- Username
- Display name
- Role (admin/member)
- Active status
- Points and redeemed points

**Example**:
```
Show me who's in my household
Who can I assign chores to?
List all circle members
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DONETICK_BASE_URL` | Yes | - | Your Donetick instance URL (must use HTTPS) |
| `DONETICK_USERNAME` | Yes | - | Your Donetick username |
| `DONETICK_PASSWORD` | Yes | - | Your Donetick password |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `RATE_LIMIT_PER_SECOND` | No | 10.0 | Requests per second limit |
| `RATE_LIMIT_BURST` | No | 10 | Maximum burst size |

### Rate Limiting

The server implements a token bucket rate limiter to prevent API overload:

- **Default**: 10 requests per second with burst capacity of 10
- **Conservative**: Starts conservative and can be increased based on your Donetick instance
- **Respects 429**: Automatically backs off when rate limited by the API

### Retry Logic

- **Exponential backoff** with jitter for transient failures
- **Maximum 3 retries** for most operations
- **Smart retry**: Only retries on 5xx errors and 429 (rate limit)
- **No retry on 4xx**: Client errors fail immediately (except 429)

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=donetick_mcp --cov-report=html

# Run specific test file
pytest tests/test_client.py

# Run with verbose output
pytest -v
```

### Project Structure

```
donetick-mcp-server/
├── src/donetick_mcp/
│   ├── __init__.py
│   ├── server.py          # MCP server implementation
│   ├── client.py           # Donetick API client
│   ├── models.py           # Pydantic data models
│   └── config.py           # Configuration management
├── tests/
│   ├── test_client.py      # API client tests
│   └── test_server.py      # MCP server tests
├── tmp/                    # Temporary files (gitignored)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

**Note**: The `tmp/` directory is used for temporary test scripts and analysis files during development. It's gitignored and not included in releases.

## API Documentation

This server uses the Donetick Full API with JWT authentication. Official documentation:
- **API Docs**: https://docs.donetick.com/
- **GitHub**: https://github.com/donetick/donetick

### Important Notes

1. **Authentication**: Uses JWT Bearer tokens (automatically managed)
2. **Full Feature Support**: All 26+ chore creation fields now working
3. **Automatic Token Refresh**: JWT tokens refreshed transparently
4. **Circle Scoped**: All operations are scoped to your circle (household/team)
5. **No Premium Required**: Advanced features work with standard accounts

## Troubleshooting

### Common Issues

**"DONETICK_BASE_URL environment variable is required"**
- Make sure your `.env` file exists and is properly formatted
- For Docker: ensure environment variables are passed in docker-compose.yml

**"Rate limited, waiting..."**
- The server is respecting API rate limits
- Consider reducing `RATE_LIMIT_PER_SECOND` if this happens frequently

**"Connection refused" or timeout errors**
- Verify your Donetick instance URL is correct
- Check that your Donetick instance is accessible
- Ensure firewall rules allow outbound connections

**"401 Unauthorized" or "Invalid credentials"**
- Verify your username and password are correct
- Check that your account is not locked or disabled
- Ensure you can login to Donetick web interface with the same credentials
- Check for typos in environment variables

**Tools not showing in Claude**
- Restart Claude Desktop after configuration changes
- Check Claude Desktop logs for errors
- Verify the configuration file path is correct

### Debugging

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
```

Or in Docker:

```yaml
environment:
  - LOG_LEVEL=DEBUG
```

View Docker logs:

```bash
docker-compose logs -f donetick-mcp
```

## Security

- **Credentials**: Never commit credentials to version control (use `.env` file)
- **JWT Tokens**: Stored in memory only, never persisted to disk
- **Automatic Token Refresh**: Prevents session expiration without user intervention
- **Docker Isolation**: Runs as non-root user in container
- **Resource Limits**: Memory and CPU limits prevent resource exhaustion
- **Input Validation**: Pydantic models validate all inputs
- **HTTPS Required**: Server enforces HTTPS for all Donetick connections

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [Donetick](https://donetick.com) - Open source chores management
- [Model Context Protocol](https://modelcontextprotocol.io) - MCP specification
- [Anthropic](https://anthropic.com) - MCP SDK and Claude

## Support

- **Issues**: https://github.com/jason1365/donetick-mcp-server/issues
- **Donetick Docs**: https://docs.donetick.com
- **MCP Docs**: https://modelcontextprotocol.io

---

Built with ❤️ for the Donetick and MCP communities
