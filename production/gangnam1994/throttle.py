"""One shared request gate for paid Agnes 2.5 Flash monthly membership traffic (max 5 requests/minute).

A call reserves a slot immediately before any POST or status-poll GET. Keeping both
methods on the same gate caps aggregate API traffic at <= 5/min (12.1s spacing) and honors
Retry-After/capacity cooldowns across the producer and poll workers.
"""
import threading
import time


class BudgetExhausted(RuntimeError):
    pass


class RequestGate:
    def __init__(self, minimum_interval=12.1, clock=None, sleep=None):
        if minimum_interval < 12.1:
            raise ValueError("Agnes requests must be spaced at least 12.1 seconds apart (<= 5/min)")
        self.interval = float(minimum_interval)
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep
        self._next_request = 0.0
        self._blocked_until = 0.0
        self._lock = threading.Lock()

    def acquire(self, deadline=float("inf")):
        """Wait for and reserve one shared POST/GET request slot."""
        while True:
            with self._lock:
                now = self.clock()
                ready = max(self._blocked_until, self._next_request)
                if now >= deadline or max(now, ready) >= deadline:
                    raise BudgetExhausted(
                        "Provider cooldown would exceed the generation budget; saved tasks can be resumed"
                    )
                delay = max(0.0, ready - now)
                if delay <= 0:
                    self._next_request = now + self.interval
                    return
            self.sleep(min(10.0, delay))

    def acquire_creation(self, deadline):
        """Compatibility alias; creates and polls reserve from the same request timeline."""
        self.acquire(deadline)

    def wait_unblocked(self, deadline):
        """Compatibility callback for poll_task; reserve one GET on the shared timeline."""
        self.acquire(deadline)

    def defer(self, seconds):
        with self._lock:
            self._blocked_until = max(
                self._blocked_until, self.clock() + max(0.0, float(seconds))
            )
