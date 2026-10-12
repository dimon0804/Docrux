"""Защита API: ограничение частоты запросов и заголовки безопасности."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from starlette.types import ASGIApp, Message, Receive, Scope, Send

SECURITY_HEADERS = {
    b"x-content-type-options": b"nosniff",
    b"x-frame-options": b"DENY",
    b"referrer-policy": b"no-referrer",
    b"cross-origin-opener-policy": b"same-origin",
    b"cross-origin-resource-policy": b"same-origin",
    b"permissions-policy": b"camera=(), microphone=(), geolocation=(), payment=()",
    b"cache-control": b"no-store",
    b"content-security-policy": b"default-src 'none'; frame-ancestors 'none'",
}


class SecurityHeaders:
    """Добавляет заголовки безопасности и идентификатор запроса ко всем ответам."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex[:16]
        scope.setdefault("state", {})["request_id"] = request_id
        docs = scope["path"].startswith(("/api/docs", "/api/openapi"))

        async def wrapped(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers", [])]
                present = {key.lower() for key, _ in headers}
                for key, value in SECURITY_HEADERS.items():
                    if docs and key == b"content-security-policy":
                        continue
                    if key not in present:
                        headers.append((key, value))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, wrapped)


class RateLimiter:
    """Скользящее окно в памяти процесса: не больше N запросов в минуту с одного адреса."""

    def __init__(self, per_minute: int, window: float = 60.0, max_clients: int = 10_000):
        self.per_minute = per_minute
        self.window = window
        self.max_clients = max_clients
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, client: str, now: float | None = None) -> tuple[bool, int]:
        """Возвращает разрешение и число секунд до следующей попытки."""
        now = time.monotonic() if now is None else now
        if len(self._hits) > self.max_clients:
            self._evict(now)
        hits = self._hits[client]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.per_minute:
            return False, max(1, int(self.window - (now - hits[0])) + 1)
        hits.append(now)
        return True, 0

    def _evict(self, now: float) -> None:
        stale = [
            key for key, hits in self._hits.items() if not hits or now - hits[-1] > self.window
        ]
        for key in stale:
            del self._hits[key]
        if len(self._hits) > self.max_clients:
            self._hits.clear()
