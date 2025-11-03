"""Donetick API client with rate limiting and retry logic."""

import asyncio
import logging
import random
import time
from typing import Any, Optional

import httpx

from .config import config
from .models import Chore, ChoreCreate, ChoreUpdate, CircleMember

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket.

        Args:
            rate: Tokens per second refill rate
            capacity: Maximum token capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1):
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire
        """
        async with self.lock:
            while True:
                now = time.time()
                elapsed = now - self.last_update

                # Refill tokens based on elapsed time
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                # Wait until enough tokens available
                wait_time = (tokens - self.tokens) / self.rate
                await asyncio.sleep(wait_time)


class DonetickClient:
    """Async client for Donetick external API (eAPI)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        rate_limit_per_second: Optional[float] = None,
        rate_limit_burst: Optional[int] = None,
    ):
        """
        Initialize Donetick API client.

        Args:
            base_url: Donetick instance URL (defaults to config)
            api_token: API token (defaults to config)
            rate_limit_per_second: Rate limit in requests per second (defaults to config)
            rate_limit_burst: Maximum burst size (defaults to config)
        """
        self.base_url = (base_url or config.donetick_base_url).rstrip("/")
        self.api_token = api_token or config.donetick_api_token
        self.rate_limiter = TokenBucket(
            rate=rate_limit_per_second or config.rate_limit_per_second,
            capacity=rate_limit_burst or config.rate_limit_burst,
        )

        # Configure httpx client with connection pooling and timeouts
        self.client = httpx.AsyncClient(
            headers={
                "secretkey": self.api_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=5.0,
            ),
            timeout=httpx.Timeout(
                connect=5.0,
                read=30.0,
                write=5.0,
                pool=2.0,
            ),
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()

    async def close(self):
        """Close the HTTP client and cleanup resources."""
        if self.client:
            await self.client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """
        Make HTTP request with rate limiting and retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API endpoint path
            max_retries: Maximum number of retry attempts
            **kwargs: Additional arguments for httpx request

        Returns:
            JSON response data

        Raises:
            httpx.HTTPError: On HTTP errors after all retries exhausted
        """
        url = f"{self.base_url}{path}"
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Wait for rate limit
                await self.rate_limiter.acquire()

                # Make request
                logger.debug(f"Request {method} {url} (attempt {attempt + 1}/{max_retries})")
                response = await self.client.request(method, url, **kwargs)

                # Handle rate limit responses
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    wait_time = float(retry_after)
                    logger.warning(f"Rate limited, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue

                # Raise for other HTTP errors
                response.raise_for_status()

                # Parse JSON response
                return response.json()

            except httpx.TimeoutException as e:
                if attempt == max_retries - 1:
                    logger.error(f"Request timeout after {max_retries} attempts: {e}")
                    raise

                # Exponential backoff with jitter
                delay = min(base_delay * (2**attempt), 60.0)
                jitter = delay * random.uniform(-0.25, 0.25)
                wait_time = delay + jitter

                logger.warning(f"Timeout on attempt {attempt + 1}, retrying in {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

            except httpx.HTTPStatusError as e:
                # Don't retry client errors (4xx) except 429
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    logger.error(f"Client error: {e.response.status_code} - {e.response.text}")
                    raise

                # Retry server errors (5xx)
                if attempt == max_retries - 1:
                    logger.error(f"Server error after {max_retries} attempts: {e}")
                    raise

                delay = min(base_delay * (2**attempt), 60.0)
                jitter = delay * random.uniform(-0.25, 0.25)
                wait_time = delay + jitter

                logger.warning(
                    f"Server error on attempt {attempt + 1}, retrying in {wait_time:.2f}s"
                )
                await asyncio.sleep(wait_time)

        raise Exception(f"Failed after {max_retries} retries")

    async def list_chores(
        self,
        filter_active: Optional[bool] = None,
        assigned_to_user_id: Optional[int] = None,
    ) -> list[Chore]:
        """
        List all chores with optional filtering.

        Args:
            filter_active: Filter by active status (None = all)
            assigned_to_user_id: Filter by assigned user ID (None = all)

        Returns:
            List of Chore objects
        """
        logger.info("Fetching chores list")
        data = await self._request("GET", "/eapi/v1/chore")

        # Parse response into Chore objects
        chores = [Chore(**chore_data) for chore_data in data]

        # Apply filters
        if filter_active is not None:
            chores = [c for c in chores if c.isActive == filter_active]
            logger.debug(f"Filtered to active={filter_active}: {len(chores)} chores")

        if assigned_to_user_id is not None:
            chores = [c for c in chores if c.assignedTo == assigned_to_user_id]
            logger.debug(f"Filtered to user {assigned_to_user_id}: {len(chores)} chores")

        logger.info(f"Retrieved {len(chores)} chores")
        return chores

    async def get_chore(self, chore_id: int) -> Optional[Chore]:
        """
        Get a specific chore by ID.

        Note: Since GET /chore/:id doesn't exist in the API,
        this fetches all chores and filters client-side.

        Args:
            chore_id: Chore ID

        Returns:
            Chore object if found, None otherwise
        """
        logger.info(f"Fetching chore {chore_id}")
        chores = await self.list_chores()

        for chore in chores:
            if chore.id == chore_id:
                logger.info(f"Found chore {chore_id}: {chore.name}")
                return chore

        logger.warning(f"Chore {chore_id} not found")
        return None

    async def create_chore(self, chore: ChoreCreate) -> Chore:
        """
        Create a new chore.

        Args:
            chore: ChoreCreate object with chore details

        Returns:
            Created Chore object
        """
        logger.info(f"Creating chore: {chore.Name}")
        data = await self._request("POST", "/eapi/v1/chore", json=chore.model_dump(exclude_none=True))

        created_chore = Chore(**data)
        logger.info(f"Created chore {created_chore.id}: {created_chore.name}")
        return created_chore

    async def update_chore(self, chore_id: int, update: ChoreUpdate) -> Chore:
        """
        Update an existing chore.

        Note: This is a Premium/Plus feature.

        Args:
            chore_id: Chore ID to update
            update: ChoreUpdate object with fields to update

        Returns:
            Updated Chore object
        """
        logger.info(f"Updating chore {chore_id}")
        data = await self._request(
            "PUT",
            f"/eapi/v1/chore/{chore_id}",
            json=update.model_dump(exclude_none=True),
        )

        updated_chore = Chore(**data)
        logger.info(f"Updated chore {chore_id}: {updated_chore.name}")
        return updated_chore

    async def delete_chore(self, chore_id: int) -> bool:
        """
        Delete a chore.

        Note: Only the chore creator can delete a chore.

        Args:
            chore_id: Chore ID to delete

        Returns:
            True if deletion successful
        """
        logger.info(f"Deleting chore {chore_id}")
        await self._request("DELETE", f"/eapi/v1/chore/{chore_id}")
        logger.info(f"Deleted chore {chore_id}")
        return True

    async def complete_chore(
        self,
        chore_id: int,
        completed_by: Optional[int] = None,
    ) -> Chore:
        """
        Mark a chore as complete.

        Note: This is a Premium/Plus feature.

        Args:
            chore_id: Chore ID to complete
            completed_by: User ID who completed the chore (optional)

        Returns:
            Updated Chore object
        """
        logger.info(f"Completing chore {chore_id}")

        params = {}
        if completed_by is not None:
            params["completedBy"] = completed_by

        data = await self._request(
            "POST",
            f"/eapi/v1/chore/{chore_id}/complete",
            params=params,
        )

        completed_chore = Chore(**data)
        logger.info(f"Completed chore {chore_id}: {completed_chore.name}")
        return completed_chore

    async def get_circle_members(self) -> list[CircleMember]:
        """
        Get all members in the user's circle.

        Note: This is a Premium/Plus feature.

        Returns:
            List of CircleMember objects
        """
        logger.info("Fetching circle members")
        data = await self._request("GET", "/eapi/v1/circle/members")

        members = [CircleMember(**member_data) for member_data in data]
        logger.info(f"Retrieved {len(members)} circle members")
        return members
