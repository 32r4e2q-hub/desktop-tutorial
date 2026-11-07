"""Shared request gate with a conservative default for Agnes's free 1-RPM video pool.

Callers may opt into a lower configured-plan floor only when that plan explicitly allows it.
There is no key rotation or limit bypass; server-requested cooldowns remain shared across workers.
"""
import threading
import time


class BudgetExhausted(RuntimeError):
    pass


class RequestGate:
    def __init__(self, minimum_interval=61.0, clock=None, sleep=None, minimum_allowed_interval=60.0):
        if minimum_allowed_interval<=0 or minimum_interval<minimum_allowed_interval:
            raise ValueError(f'Request interval must be at least {minimum_allowed_interval:g} seconds')
        self.interval=float(minimum_interval)
        self.clock=clock or time.monotonic
        self.sleep=sleep or time.sleep
        self._next_create=0.0
        self._blocked_until=0.0
        self._lock=threading.Lock()

    def _wait_until_available(self, deadline, creation=False):
        while True:
            with self._lock:
                now=self.clock()
                ready=max(self._blocked_until,self._next_create if creation else 0.0)
                if now>=deadline or max(now,ready)>=deadline:
                    raise BudgetExhausted('Provider cooldown would exceed the generation budget; saved tasks can be resumed')
                delay=max(0.0,ready-now)
                if delay<=0:
                    if creation:self._next_create=now+self.interval
                    return
            # Short internal sleeps allow another worker's Retry-After to extend a cooldown.
            self.sleep(min(10.0,delay))

    def acquire_creation(self, deadline):
        self._wait_until_available(deadline,creation=True)

    def wait_unblocked(self, deadline):
        self._wait_until_available(deadline,creation=False)

    def defer(self,seconds):
        with self._lock:
            self._blocked_until=max(self._blocked_until,self.clock()+max(0,float(seconds)))
