"""Small best-effort in-memory limiter for sensitive endpoints."""

from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request


_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_LOCK = Lock()


def enforce_rate_limit(
    request: Request,
    name: str,
    limit: int,
    window_seconds: int,
) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = f"{name}:{client_host}"
    now = monotonic()

    with _LOCK:
        bucket = _BUCKETS[key]
        cutoff = now - window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas. Aguarde alguns instantes e tente novamente.",
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
