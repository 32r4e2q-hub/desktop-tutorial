"""Thread-safe Agnes creation pacing with paid-plan opt-in and Retry-After support."""
from __future__ import annotations
import threading
import time

class BudgetExhausted(RuntimeError):
    pass

class RequestGate:
    def __init__(self, minimum_interval=12.0, allow_fast_plan=False, clock=None, sleep=None):
        interval=float(minimum_interval)
        if interval<=0: raise ValueError('minimum_interval must be positive')
        if interval<60 and not allow_fast_plan:
            raise ValueError('sub-60-second cadence requires explicit paid-plan opt-in')
        self.interval=interval; self.clock=clock or time.monotonic; self.sleep=sleep or time.sleep
        self._next_create=0.0; self._blocked_until=0.0; self._lock=threading.Lock()
    def _wait_until_available(self,deadline,creation=False):
        while True:
            with self._lock:
                now=self.clock(); ready=max(self._blocked_until,self._next_create if creation else 0.0)
                if now>=deadline or ready>=deadline:
                    raise BudgetExhausted('Provider cooldown exceeds generation budget; resume saved tasks later')
                delay=max(0.0,ready-now)
                if delay<=0:
                    if creation:self._next_create=now+self.interval
                    return
            self.sleep(min(10.0,delay))
    def acquire_creation(self,deadline): self._wait_until_available(deadline,creation=True)
    def wait_unblocked(self,deadline): self._wait_until_available(deadline,creation=False)
    def defer(self,seconds):
        with self._lock:self._blocked_until=max(self._blocked_until,self.clock()+max(0.0,float(seconds)))
