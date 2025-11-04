"""
Performance and reliability tests for Donetick MCP server.

Tests performance characteristics and reliability features:
- Rate limiting enforcement (token bucket)
- Concurrent request handling
- Cache performance and hit rates
- JWT token refresh transparency
- Retry with exponential backoff
- Connection pooling
- Large payload handling
"""

import asyncio
import time

import pytest
from pytest_httpx import HTTPXMock

from donetick_mcp.client import DonetickClient, TokenBucket


@pytest.fixture
def client():
    """Create a test client instance."""
    return DonetickClient(
        base_url="https://test.donetick.com",
        username="test_user",
        password="test_password",
        rate_limit_per_second=10.0,  # Lower limit for testing rate limiter
        rate_limit_burst=10,
    )


@pytest.fixture
def fast_client():
    """Create a test client with high rate limit for performance tests."""
    return DonetickClient(
        base_url="https://test.donetick.com",
        username="test_user",
        password="test_password",
        rate_limit_per_second=100.0,
        rate_limit_burst=100,
    )


@pytest.fixture
def mock_login(httpx_mock: HTTPXMock):
    """Mock the login endpoint for authentication."""
    httpx_mock.add_response(
        url="https://test.donetick.com/api/v1/auth/login",
        json={"token": "test_jwt_token"},
        method="POST",
    )


@pytest.fixture
def sample_chore_data():
    """Sample chore data for testing."""
    return {
        "id": 1,
        "name": "Test Chore",
        "description": "Test description",
        "frequencyType": "once",
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


class TestRateLimiting:
    """Test rate limiting enforcement and token bucket behavior."""

    @pytest.mark.asyncio
    async def test_rate_limiting_respected(self, client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """
        Verify rate limiter enforces configured limit (10 req/sec).

        This test:
        1. Configures client with 10 req/sec limit
        2. Makes 20 requests in rapid succession
        3. Measures total time taken
        4. Verifies requests are spaced according to rate limit

        Expected: 20 requests at 10 req/sec should take ~2 seconds (with some tolerance).
        """
        # Mock 20 responses
        for _ in range(20):
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/",
                json=[sample_chore_data],
            )

        async with client:
            start_time = time.perf_counter()

            # Make 20 requests
            tasks = [client.list_chores() for _ in range(20)]
            results = await asyncio.gather(*tasks)

            end_time = time.perf_counter()
            elapsed = end_time - start_time

            # All requests should succeed
            assert len(results) == 20
            assert all(len(r) == 1 for r in results)

            # Verify rate limiting: 20 requests at 10 req/sec = ~2 seconds
            # Allow some tolerance for test overhead and concurrent execution
            # The token bucket allows burst capacity, so first 10 requests are immediate
            # Next 10 requests need to wait for refill at 10/sec = 1 second minimum
            assert elapsed >= 0.8, f"Requests completed too fast ({elapsed:.2f}s), rate limiting not enforced"
            assert elapsed <= 3.0, f"Requests took too long ({elapsed:.2f}s), rate limiter may be too strict"

    @pytest.mark.asyncio
    async def test_token_bucket_refill(self):
        """
        Test that token bucket refills over time at correct rate.

        This test:
        1. Creates a bucket with 10 tokens at 10/sec refill rate
        2. Exhausts all tokens
        3. Waits for refill
        4. Verifies correct number of tokens refilled
        """
        bucket = TokenBucket(rate=10.0, capacity=10)

        # Exhaust all tokens
        await bucket.acquire(10)
        assert bucket.tokens == 0.0

        # Wait for 0.5 seconds (should refill 5 tokens at 10/sec)
        await asyncio.sleep(0.5)

        # Should be able to acquire 1 token now
        await bucket.acquire(1)

        # Should have ~4 tokens left (5 refilled - 1 acquired)
        assert bucket.tokens >= 3.0  # Allow for timing variance
        assert bucket.tokens <= 5.0


class TestConcurrentRequests:
    """Test handling of concurrent API requests."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, fast_client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """
        Verify multiple concurrent API calls are handled correctly.

        This test:
        1. Launches 10 concurrent requests to different endpoints
        2. Verifies all complete successfully
        3. Checks no errors from connection pool exhaustion
        4. Measures completion time for performance baseline

        Tests connection pooling and async request handling.
        """
        # Mock responses for different endpoints
        for _ in range(5):
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/",
                json=[sample_chore_data],
            )

        for i in range(1, 6):
            httpx_mock.add_response(
                url=f"https://test.donetick.com/api/v1/chores/{i}",
                json={**sample_chore_data, "id": i},
            )

        async with fast_client:
            start_time = time.perf_counter()

            # Launch 10 concurrent requests (5 list, 5 get)
            tasks = []
            for _ in range(5):
                tasks.append(fast_client.list_chores())
            for i in range(1, 6):
                tasks.append(fast_client.get_chore(i))

            results = await asyncio.gather(*tasks)

            end_time = time.perf_counter()
            elapsed = end_time - start_time

            # All should succeed
            assert len(results) == 10

            # First 5 are lists
            for i in range(5):
                assert isinstance(results[i], list)
                assert len(results[i]) == 1

            # Last 5 are individual chores
            for i in range(5, 10):
                assert results[i] is not None
                assert results[i].id == i - 4

            # Should complete quickly with concurrent execution
            assert elapsed < 2.0, f"Concurrent requests took too long ({elapsed:.2f}s)"

    @pytest.mark.asyncio
    async def test_connection_pooling(self, fast_client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """
        Verify connection reuse in pool (max 100 connections).

        This test:
        1. Makes 50+ requests in batches
        2. Verifies all complete without connection errors
        3. Tests that connection pooling prevents exhaustion
        4. Validates no "too many connections" errors

        Connection pool configured with:
        - max_connections: 100
        - max_keepalive_connections: 50
        """
        # Mock 60 responses
        for _ in range(60):
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/chores/",
                json=[sample_chore_data],
            )

        async with fast_client:
            # Make 60 requests in 3 batches of 20
            all_results = []

            for batch in range(3):
                tasks = [fast_client.list_chores() for _ in range(20)]
                batch_results = await asyncio.gather(*tasks)
                all_results.extend(batch_results)

            # All should succeed (no connection exhaustion)
            assert len(all_results) == 60
            assert all(len(r) == 1 for r in all_results)


class TestCachePerformance:
    """Test caching behavior and performance."""

    @pytest.mark.asyncio
    async def test_cache_performance(self, fast_client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """
        Verify get_chore cache hit performance.

        This test:
        1. Fetches a chore (cache miss - hits API)
        2. Fetches same chore again (cache hit - no API call)
        3. Verifies second call doesn't hit API (check mock call count)
        4. Measures performance improvement from caching

        Cache TTL is 60 seconds by default.
        """
        # Mock only ONE response (second call should hit cache)
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json=sample_chore_data,
        )

        async with fast_client:
            # Clear cache to ensure clean state
            fast_client.clear_cache()

            # First fetch - cache miss
            start_miss = time.perf_counter()
            chore1 = await fast_client.get_chore(1)
            time_miss = time.perf_counter() - start_miss

            assert chore1 is not None
            assert chore1.id == 1

            # Second fetch - should be cache hit
            start_hit = time.perf_counter()
            chore2 = await fast_client.get_chore(1)
            time_hit = time.perf_counter() - start_hit

            assert chore2 is not None
            assert chore2.id == 1

            # Verify data is the same
            assert chore1.name == chore2.name

            # Cache hit should be faster (no network call)
            assert time_hit < time_miss, "Cache hit should be faster than cache miss"

            # Verify only 1 API call was made (second was cached)
            # If httpx_mock received 2 requests, the cache didn't work
            # We only mocked 1 response, so if cache worked, we won't get an error

    @pytest.mark.asyncio
    async def test_cache_expiry(self, sample_chore_data, httpx_mock: HTTPXMock):
        """
        Test cache expiration after TTL.

        This test:
        1. Creates client with short cache TTL (0.5 seconds)
        2. Fetches chore (cache miss)
        3. Waits for TTL to expire
        4. Fetches again (should be cache miss again)
        5. Verifies API was called twice
        """
        # Mock login
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/auth/login",
            json={"token": "test_jwt_token"},
            method="POST",
        )

        # Create client with short cache TTL
        short_ttl_client = DonetickClient(
            base_url="https://test.donetick.com",
            username="test_user",
            password="test_password",
            rate_limit_per_second=100.0,
            cache_ttl=0.5,  # 0.5 second TTL
        )

        # Mock TWO responses (both should hit API after cache expires)
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json=sample_chore_data,
        )
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/1",
            json={**sample_chore_data, "description": "Updated description"},
        )

        async with short_ttl_client:
            # First fetch
            chore1 = await short_ttl_client.get_chore(1)
            assert chore1 is not None
            assert chore1.description == "Test description"

            # Wait for cache to expire
            await asyncio.sleep(0.6)

            # Second fetch - cache expired, should hit API again
            chore2 = await short_ttl_client.get_chore(1)
            assert chore2 is not None
            assert chore2.description == "Updated description"


class TestTokenRefresh:
    """Test JWT token refresh and authentication handling."""

    @pytest.mark.asyncio
    async def test_token_refresh_transparent(self, fast_client, sample_chore_data, httpx_mock: HTTPXMock):
        """
        Verify JWT auto-refresh happens transparently without user awareness.

        This test:
        1. Initial login returns token
        2. API request returns 401 (token expired)
        3. Client automatically refreshes token
        4. Retries original request successfully
        5. User never sees authentication error

        Tests transparent authentication handling.
        """
        # Initial login
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/auth/login",
            json={"token": "initial_token"},
            method="POST",
        )

        # First API request returns 401 (expired token)
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            status_code=401,
        )

        # Token refresh (automatic)
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/auth/login",
            json={"token": "refreshed_token"},
            method="POST",
        )

        # Retry succeeds
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json=[sample_chore_data],
        )

        async with fast_client:
            # User makes normal API call
            chores = await fast_client.list_chores()

            # Should succeed transparently (token refresh happened automatically)
            assert len(chores) == 1
            assert chores[0].name == "Test Chore"

            # Verify token was refreshed
            assert fast_client._jwt_token == "refreshed_token"


class TestRetryBackoff:
    """Test retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self, fast_client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """
        Verify exponential backoff on 5xx errors.

        This test:
        1. First request returns 500 (server error)
        2. Second request returns 500 (still failing)
        3. Third request succeeds
        4. Verifies retry attempts with increasing delays
        5. Measures timing to confirm exponential backoff (1s, 2s, 4s...)

        Retry logic:
        - Attempt 1: immediate
        - Attempt 2: ~1 second delay
        - Attempt 3: ~2 second delay
        """
        # First two attempts return 500
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            status_code=500,
            json={"error": "Internal server error"},
        )
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            status_code=500,
            json={"error": "Internal server error"},
        )

        # Third attempt succeeds
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json=[sample_chore_data],
        )

        async with fast_client:
            start_time = time.perf_counter()

            # This should succeed after 2 retries
            chores = await fast_client.list_chores()

            end_time = time.perf_counter()
            elapsed = end_time - start_time

            # Should succeed after retries
            assert len(chores) == 1

            # Verify exponential backoff timing
            # First retry: ~1s, second retry: ~2s, total: ~3s
            # Allow tolerance for test overhead and jitter
            assert elapsed >= 2.0, f"Retries completed too fast ({elapsed:.2f}s), backoff not working"
            assert elapsed <= 5.0, f"Retries took too long ({elapsed:.2f}s), backoff may be too aggressive"

    @pytest.mark.asyncio
    async def test_retry_timeout_with_backoff(self, fast_client, sample_chore_data, httpx_mock: HTTPXMock, mock_login):
        """
        Test timeout retry with exponential backoff.

        This test:
        1. First request times out
        2. Second request times out
        3. Third request succeeds
        4. Verifies timeouts are retried with backoff
        """
        import httpx

        # First two attempts timeout
        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))
        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))

        # Third attempt succeeds
        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json=[sample_chore_data],
        )

        async with fast_client:
            start_time = time.perf_counter()

            # Should succeed after retries
            chores = await fast_client.list_chores()

            end_time = time.perf_counter()
            elapsed = end_time - start_time

            # Should succeed
            assert len(chores) == 1

            # Verify backoff timing (similar to 5xx test)
            assert elapsed >= 2.0, "Timeout retries too fast"
            assert elapsed <= 5.0, "Timeout retries too slow"


class TestLargePayloads:
    """Test handling of large API responses."""

    @pytest.mark.asyncio
    async def test_large_payload_handling(self, fast_client, httpx_mock: HTTPXMock, mock_login):
        """
        Verify large API responses are handled correctly.

        This test:
        1. Mocks API response with 100+ chores
        2. Fetches and parses large response
        3. Verifies all data is correctly parsed
        4. Tests memory handling of large JSON payloads

        Simulates real-world scenarios with many chores.
        """
        # Create large response with 100 chores
        large_response = []
        for i in range(100):
            large_response.append({
                "id": i + 1,
                "name": f"Chore {i + 1}",
                "description": f"Description for chore {i + 1}",
                "frequencyType": "weekly",
                "frequency": 1,
                "frequencyMetadata": {},
                "nextDueDate": "2025-11-10T00:00:00Z",
                "isRolling": False,
                "assignedTo": (i % 5) + 1,  # Rotate through 5 users
                "assignees": [{"userId": (i % 5) + 1}],
                "assignStrategy": "least_completed",
                "isActive": True,
                "notification": False,
                "notificationMetadata": {},
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
            })

        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/chores/",
            json=large_response,
        )

        async with fast_client:
            start_time = time.perf_counter()

            # Fetch large response
            chores = await fast_client.list_chores()

            end_time = time.perf_counter()
            elapsed = end_time - start_time

            # Verify all chores parsed correctly
            assert len(chores) == 100
            assert chores[0].id == 1
            assert chores[0].name == "Chore 1"
            assert chores[99].id == 100
            assert chores[99].name == "Chore 100"

            # Should complete reasonably quickly
            assert elapsed < 1.0, f"Large payload took too long to process ({elapsed:.2f}s)"

    @pytest.mark.asyncio
    async def test_large_label_response(self, fast_client, httpx_mock: HTTPXMock, mock_login):
        """
        Test handling of large label lists.

        This test:
        1. Mocks response with 50+ labels
        2. Verifies all labels are parsed correctly
        3. Tests lookup performance with large label sets
        """
        # Create large label response
        large_labels = []
        for i in range(50):
            large_labels.append({
                "id": i + 1,
                "name": f"label_{i + 1}",
                "color": f"#{(i * 5121) % 256:02x}{(i * 7919) % 256:02x}{(i * 3571) % 256:02x}",
            })

        httpx_mock.add_response(
            url="https://test.donetick.com/api/v1/labels",
            json={"res": large_labels},
        )

        async with fast_client:
            # Fetch labels
            labels = await fast_client.get_labels()

            # Verify all labels parsed
            assert len(labels) == 50
            assert labels[0].name == "label_1"
            assert labels[49].name == "label_50"

            # Test lookup with large set
            httpx_mock.add_response(
                url="https://test.donetick.com/api/v1/labels",
                json={"res": large_labels},
            )

            label_map = await fast_client.lookup_label_ids(["label_1", "label_25", "label_50"])

            assert len(label_map) == 3
            assert label_map["label_1"] == 1
            assert label_map["label_25"] == 25
            assert label_map["label_50"] == 50
