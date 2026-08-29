import re
from collections import defaultdict
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request


_RATE_LIMIT_PATTERN = re.compile(r"^(?P<count>[1-9][0-9]*)/(?P<unit>second|minute|hour)$")
_WINDOW_SECONDS = {"second": 1, "minute": 60, "hour": 60 * 60}


class SharedRateLimiter:
    def __init__(self, rate: str) -> None:
        self._lock = Lock()
        self._windows: dict[str, tuple[float, int]] = defaultdict(lambda: (0.0, 0))
        self.update_rate(rate)

    def update_rate(self, rate: str) -> None:
        match = _RATE_LIMIT_PATTERN.fullmatch(rate)
        if match is None:
            raise ValueError("RATE_LIMIT must use the form '<positive integer>/<second|minute|hour>'")
        self.limit = int(match.group("count"))
        self.window_seconds = _WINDOW_SECONDS[match.group("unit")]
        self.rate = rate
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()

    def allow(self, client_ip: str, now: float | None = None) -> bool:
        current_time = monotonic() if now is None else now
        with self._lock:
            window_start, count = self._windows[client_ip]
            if current_time - window_start >= self.window_seconds:
                window_start, count = current_time, 0
            if count >= self.limit:
                self._windows[client_ip] = (window_start, count)
                return False
            self._windows[client_ip] = (window_start, count + 1)
            return True


def client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def enforce_rate_limit(request: Request) -> None:
    limiter = request.app.state.rate_limiter
    if not limiter.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail="Demo request limit reached. Try again later.")
