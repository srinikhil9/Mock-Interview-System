from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Dict


class Telemetry:
    def __init__(self) -> None:
        self.counters: Dict[str, int] = {}
        self.timings_ms: Dict[str, float] = {}
        self._timing_samples_ms: Dict[str, list] = {}

    def incr(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value

    def observe_ms(self, name: str, ms: float) -> None:
        self.timings_ms[name] = self.timings_ms.get(name, 0.0) + ms
        self.counters[f"{name}:count"] = self.counters.get(f"{name}:count", 0) + 1
        self._timing_samples_ms.setdefault(name, []).append(ms)

    @contextmanager
    def timer(self, name: str):
        start = time.time()
        try:
            yield
        finally:
            elapsed_ms = (time.time() - start) * 1000.0
            self.observe_ms(name, elapsed_ms)

    def summary(self) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for name, total in self.timings_ms.items():
            count = self.counters.get(f"{name}:count", 0)
            samples = self._timing_samples_ms.get(name, [])
            avg = (total / count) if count else 0.0
            mn = min(samples) if samples else 0.0
            mx = max(samples) if samples else 0.0
            out[name] = {
                "count": float(count),
                "total_ms": float(total),
                "avg_ms": float(avg),
                "min_ms": float(mn),
                "max_ms": float(mx),
            }
        return out


