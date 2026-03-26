"""Benchmark helpers shared by tests and scripts."""

from __future__ import annotations

import asyncio
import json
import math
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


def now_stamp() -> str:
    """Return a UTC timestamp suitable for filenames."""
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def _percentile(samples: list[float], pct: float) -> float:
    if not samples:
        return 0.0
    if len(samples) == 1:
        return samples[0]

    ordered = sorted(samples)
    rank = (len(ordered) - 1) * pct
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    lower_value = ordered[lower]
    upper_value = ordered[upper]
    return lower_value + (upper_value - lower_value) * (rank - lower)


@dataclass(slots=True)
class BenchmarkStats:
    """Summary statistics for a timed benchmark case."""

    iterations: int
    mean_ms: float
    median_ms: float
    min_ms: float
    max_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    total_ms: float
    throughput_per_second: float
    error_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BenchmarkCase:
    """A benchmark case plus metadata and optional notes."""

    name: str
    category: str
    status: str
    stats: BenchmarkStats | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "metadata": self.metadata,
            "notes": self.notes,
        }
        if self.stats is not None:
            payload["stats"] = self.stats.to_dict()
        return payload


def summarize_samples(
    samples_ms: list[float],
    *,
    error_count: int = 0,
    operations_per_iteration: int = 1,
) -> BenchmarkStats:
    """Summarize a list of millisecond timings."""
    if not samples_ms:
        return BenchmarkStats(
            iterations=0,
            mean_ms=0.0,
            median_ms=0.0,
            min_ms=0.0,
            max_ms=0.0,
            p50_ms=0.0,
            p95_ms=0.0,
            p99_ms=0.0,
            total_ms=0.0,
            throughput_per_second=0.0,
            error_count=error_count,
        )

    total_ms = sum(samples_ms)
    total_operations = len(samples_ms) * max(operations_per_iteration, 1)
    throughput = 0.0 if total_ms <= 0 else total_operations / (total_ms / 1000.0)

    return BenchmarkStats(
        iterations=len(samples_ms),
        mean_ms=statistics.mean(samples_ms),
        median_ms=statistics.median(samples_ms),
        min_ms=min(samples_ms),
        max_ms=max(samples_ms),
        p50_ms=_percentile(samples_ms, 0.50),
        p95_ms=_percentile(samples_ms, 0.95),
        p99_ms=_percentile(samples_ms, 0.99),
        total_ms=total_ms,
        throughput_per_second=throughput,
        error_count=error_count,
    )


def benchmark_sync(
    name: str,
    category: str,
    func: Callable[[], T],
    *,
    iterations: int = 10,
    warmup: int = 1,
    operations_per_iteration: int = 1,
    metadata: dict[str, Any] | None = None,
) -> tuple[BenchmarkCase, list[T]]:
    """Run a synchronous callable and collect timing stats."""
    for _ in range(max(warmup, 0)):
        func()

    samples_ms: list[float] = []
    results: list[T] = []
    errors = 0

    for _ in range(max(iterations, 0)):
        start = time.perf_counter()
        try:
            results.append(func())
        except Exception:
            errors += 1
            continue
        samples_ms.append((time.perf_counter() - start) * 1000.0)

    case = BenchmarkCase(
        name=name,
        category=category,
        status="ok" if samples_ms else "error",
        stats=summarize_samples(
            samples_ms,
            error_count=errors,
            operations_per_iteration=operations_per_iteration,
        ),
        metadata=metadata or {},
    )
    _collect(case)
    return case, results


async def benchmark_async(
    name: str,
    category: str,
    func: Callable[[], Awaitable[T]],
    *,
    iterations: int = 10,
    warmup: int = 1,
    operations_per_iteration: int = 1,
    metadata: dict[str, Any] | None = None,
) -> tuple[BenchmarkCase, list[T]]:
    """Run an async callable and collect timing stats."""
    for _ in range(max(warmup, 0)):
        await func()

    samples_ms: list[float] = []
    results: list[T] = []
    errors = 0

    for _ in range(max(iterations, 0)):
        start = time.perf_counter()
        try:
            results.append(await func())
        except Exception:
            errors += 1
            continue
        samples_ms.append((time.perf_counter() - start) * 1000.0)
        await asyncio.sleep(0)

    case = BenchmarkCase(
        name=name,
        category=category,
        status="ok" if samples_ms else "error",
        stats=summarize_samples(
            samples_ms,
            error_count=errors,
            operations_per_iteration=operations_per_iteration,
        ),
        metadata=metadata or {},
    )
    _collect(case)
    return case, results


# ── Session collector for tabular display ────────────────────────────

_collected_cases: list[BenchmarkCase] = []


def _collect(case: BenchmarkCase) -> None:
    """Append a completed benchmark case to the session collector."""
    _collected_cases.append(case)


def get_collected_cases() -> list[BenchmarkCase]:
    """Return all cases collected during this session."""
    return list(_collected_cases)


def reset_collected_cases() -> None:
    """Clear the session collector (called at session start)."""
    _collected_cases.clear()


def format_table(cases: list[BenchmarkCase] | None = None) -> str:
    """Format collected benchmark cases as a fixed-width table.

    Produces output like pytest-benchmark's table: name, iterations,
    min, mean, median, p95, max, ops/s.
    """
    cases = cases or _collected_cases
    if not cases:
        return "(no benchmarks collected)"

    # Column definitions: (header, width, format_fn)
    rows: list[tuple[str, str, int, str, str, str, str, str, str]] = []
    for c in cases:
        s = c.stats
        if s is None:
            continue
        rows.append((
            c.category,
            c.name,
            s.iterations,
            f"{s.min_ms:.3f}",
            f"{s.mean_ms:.3f}",
            f"{s.median_ms:.3f}",
            f"{s.p95_ms:.3f}",
            f"{s.max_ms:.3f}",
            f"{s.throughput_per_second:.1f}",
        ))

    if not rows:
        return "(no benchmarks with stats)"

    headers = ("Category", "Name", "Rounds", "Min (ms)", "Mean (ms)", "Median (ms)", "P95 (ms)", "Max (ms)", "OPS")
    # Compute column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    sep = "  "
    header_line = sep.join(str(h).rjust(w) for h, w in zip(headers, widths))
    divider = sep.join("-" * w for w in widths)

    lines = [divider, header_line, divider]
    for row in rows:
        lines.append(sep.join(str(cell).rjust(w) for cell, w in zip(row, widths)))
    lines.append(divider)

    return "\n".join(lines)


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    """Write JSON with deterministic formatting."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output_path
