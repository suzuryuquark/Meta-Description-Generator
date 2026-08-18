import asyncio

from models.bulk import BulkItemState, BulkItemStatus
from services.rate_limiter import AsyncRateLimiter


def test_bulk_item_tracks_status_and_message() -> None:
    item = BulkItemState("https://example.com")

    item.update(BulkItemStatus.FAILED, "取得に失敗")

    assert item.status is BulkItemStatus.FAILED
    assert item.message == "取得に失敗"


def test_rate_limiter_waits_only_until_next_slot() -> None:
    now = [0.0]
    waits: list[float] = []

    async def sleep(seconds: float) -> None:
        waits.append(seconds)
        now[0] += seconds

    async def exercise() -> None:
        limiter = AsyncRateLimiter(
            minimum_interval_seconds=1.0,
            clock=lambda: now[0],
            sleeper=sleep,
        )
        await limiter.acquire()
        await limiter.acquire()
        await limiter.defer(5.0)
        await limiter.acquire()

    asyncio.run(exercise())

    assert waits == [1.0, 5.0]
