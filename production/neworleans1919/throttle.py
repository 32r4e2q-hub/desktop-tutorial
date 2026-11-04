"""Shared creation spacing for the Agnes video pool.

The template inherited a 61-second gate because the *free* pool allows one video creation per
minute. A paid monthly key ("$XX/month, 500 video-seconds per day, 5 creations per minute") is
not subject to that: spacing creations 12 s apart (a deliberately conservative 5/min) is what
actually uses the plan. The floor below is a safety rail against misconfiguration, not a
licence bump: it is still well inside the documented 5/min.

Free-pool behaviour is preserved by constructing ``RequestGate(61)``.
"""
import threading
import time

# 5 creations per minute -> 12 s apart. 10 s leaves a small margin for clock jitter.
FAST_MINIMUM_INTERVAL = 10.0


class BudgetExhausted(RuntimeError):
    pass


class RequestGate:
    def __init__(self, minimum_interval=61.0, clock=None, sleep=None, allow_fast_plan=False):
        if minimum_interval < FAST_MINIMUM_INTERVAL and not allow_fast_plan:
            raise ValueError(
                f"Creation spacing must be >= {FAST_MINIMUM_INTERVAL:g}s (5/min plan limit); "
                "pass allow_fast_plan=True only for a paid key"
            )
        self.interval = float(minimum_interval)
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep
        self._next_create = 0.0
        self._blocked_until = 0.0
        self._lock = threading.Lock()

    def _wait_until_available(self, deadline, creation=False):
        while True:
            with self._lock:
                now = self.clock()
                ready = max(self._blocked_until, self._next_create if creation else 0.0)
                if now >= deadline or max(now, ready) >= deadline:
                    raise BudgetExhausted('Provider cooldown would exceed the generation budget; saved tasks can be resumed')
                delay = max(0.0, ready - now)
                if delay <= 0:
                    if creation:
                        self._next_create = now + self.interval
                    return
            # Short internal sleeps allow another worker's Retry-After to extend a cooldown.
            self.sleep(min(5.0, delay))

    def acquire_creation(self, deadline):
        self._wait_until_available(deadline, creation=True)

    def wait_unblocked(self, deadline):
        self._wait_until_available(deadline, creation=False)

    def defer(self, seconds):
        with self._lock:
            self._blocked_until = max(self._blocked_until, self.clock() + max(0, float(seconds)))
