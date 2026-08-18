from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

AsyncSleeper = Callable[[float], Awaitable[None]]
Clock = Callable[[], float]


class AsyncRateLimiter:
    """Serializes requests while allowing the next allowed time to be deferred."""

    def __init__(
        self,
        minimum_interval_seconds: float = 1.0,
        *,
        clock: Clock = time.monotonic,
        sleeper: AsyncSleeper = asyncio.sleep,
    ) -> None:
        self.minimum_interval_seconds = max(0.0, minimum_interval_seconds)
        self.clock = clock
        self.sleeper = sleeper
        self._next_allowed_at = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            delay = max(0.0, self._next_allowed_at - self.clock())
            if delay:
                await self.sleeper(delay)
            self._next_allowed_at = self.clock() + self.minimum_interval_seconds

    async def defer(self, seconds: float) -> None:
        async with self._lock:
            self._next_allowed_at = max(self._next_allowed_at, self.clock() + max(0.0, seconds))
