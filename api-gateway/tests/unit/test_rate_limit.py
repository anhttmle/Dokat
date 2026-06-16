"""Unit tests for rate limiting (T-08, TDD)."""

import fakeredis.aioredis
import pytest

from app.middleware.rate_limit import check_limit, compute_retry_after


class TestComputeRetryAfter:
    def test_minimum_is_one_second(self):
        assert compute_retry_after(0) == 1
        assert compute_retry_after(-1) == 1

    def test_returns_ttl_when_positive(self):
        assert compute_retry_after(30) == 30
        assert compute_retry_after(60) == 60


class TestCheckLimit:
    @pytest.fixture()
    async def redis(self):
        client = fakeredis.aioredis.FakeRedis()
        yield client
        await client.aclose()

    @pytest.mark.asyncio
    async def test_allows_requests_up_to_limit(self, redis):
        for _ in range(5):
            allowed, retry_after = await check_limit(redis, "rl:test", 5)
            assert allowed is True
            assert retry_after == 0

    @pytest.mark.asyncio
    async def test_rejects_request_over_limit(self, redis):
        for _ in range(5):
            await check_limit(redis, "rl:test-over", 5)

        allowed, retry_after = await check_limit(redis, "rl:test-over", 5)
        assert allowed is False
        assert retry_after >= 1
