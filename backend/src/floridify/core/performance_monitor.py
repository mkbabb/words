"""Real-time performance monitoring with automatic optimization triggers."""

import time
from collections import deque
from collections.abc import Callable
from typing import Any

from ..utils.logging import get_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """Real-time performance tracking with auto-optimization."""

    def __init__(self) -> None:
        # Performance metrics storage (last 100 operations)
        self.metrics: dict[str, deque[float]] = {
            "exact": deque(maxlen=100),
            "fuzzy": deque(maxlen=100),
            "semantic": deque(maxlen=100),
            "combined": deque(maxlen=100),
        }

        # Performance targets (in milliseconds)
        self.targets = {"exact": 1.0, "fuzzy": 5.0, "semantic": 10.0, "combined": 10.0}

        # Optimization states
        self.optimization_states = {
            "fuzzy_max_candidates": 1000,
            "semantic_lazy_load": True,
            "cache_promotion_threshold": 3,
        }

        # Alert thresholds (2x target = warning, 5x = critical)
        self.warning_thresholds = {k: v * 2 for k, v in self.targets.items()}
        self.critical_thresholds = {k: v * 5 for k, v in self.targets.items()}

        # Statistics
        self.stats = {"total_searches": 0, "auto_optimizations": 0, "performance_alerts": 0}

    async def track_search(
        self, method: str, query: str, search_fn: Callable[[], Any], **kwargs: Any
    ) -> Any:
        """Track search performance and trigger optimizations if needed."""
        start_time = time.perf_counter()

        try:
            result = await search_fn()
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Record metrics
            self.metrics[method].append(elapsed_ms)
            self.stats["total_searches"] += 1

            # Check for performance issues
            await self._check_performance_alerts(method, query, elapsed_ms)

            return result

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Search failed after {elapsed_ms:.1f}ms: {e}")
            raise

    async def _check_performance_alerts(self, method: str, query: str, elapsed_ms: float) -> None:
        """Check for performance degradation and trigger optimizations."""
        target = self.targets.get(method, 10.0)
        warning_threshold = self.warning_thresholds.get(method, 20.0)
        critical_threshold = self.critical_thresholds.get(method, 50.0)

        if elapsed_ms > critical_threshold:
            logger.error(
                f"CRITICAL: {method} search took {elapsed_ms:.1f}ms "
                f"(target: {target:.1f}ms, query: '{query}')"
            )
            self.stats["performance_alerts"] += 1
            await self._trigger_emergency_optimization(method)

        elif elapsed_ms > warning_threshold:
            logger.warning(
                f"SLOW: {method} search took {elapsed_ms:.1f}ms "
                f"(target: {target:.1f}ms, query: '{query}')"
            )
            self.stats["performance_alerts"] += 1
            await self._trigger_optimization(method)

    async def _trigger_optimization(self, method: str) -> None:
        """Trigger automatic optimization for performance issues."""
        if method == "fuzzy":
            # Reduce candidate set size
            current_candidates = self.optimization_states["fuzzy_max_candidates"]
            new_candidates = max(100, current_candidates // 2)
            self.optimization_states["fuzzy_max_candidates"] = new_candidates

            logger.info(
                f"AUTO-OPTIMIZATION: Reduced fuzzy candidates from {current_candidates} to {new_candidates}"
            )

        elif method == "semantic":
            # Enable lazy loading if not already enabled
            if not self.optimization_states["semantic_lazy_load"]:
                self.optimization_states["semantic_lazy_load"] = True
                logger.info("AUTO-OPTIMIZATION: Enabled semantic lazy loading")

        elif method == "exact":
            # Increase cache promotion threshold
            current_threshold = self.optimization_states["cache_promotion_threshold"]
            new_threshold = max(2, current_threshold - 1)
            self.optimization_states["cache_promotion_threshold"] = new_threshold

            logger.info(
                f"AUTO-OPTIMIZATION: Reduced cache promotion threshold from {current_threshold} to {new_threshold}"
            )

        self.stats["auto_optimizations"] += 1

    async def _trigger_emergency_optimization(self, method: str) -> None:
        """Trigger emergency optimization for critical performance issues."""
        logger.critical(f"EMERGENCY OPTIMIZATION triggered for {method}")

        if method == "fuzzy":
            # Drastically reduce candidate set
            self.optimization_states["fuzzy_max_candidates"] = 50
            logger.critical("EMERGENCY: Set fuzzy candidates to 50")

        elif method == "semantic":
            # Could disable semantic search temporarily
            logger.critical("EMERGENCY: Consider disabling semantic search temporarily")

        elif method == "exact":
            # Force cache rebuild
            logger.critical("EMERGENCY: Recommend trie cache rebuild")

        self.stats["auto_optimizations"] += 1

    def get_performance_summary(self) -> dict[str, Any]:
        """Get performance summary with statistics."""
        summary = {}

        for method, times in self.metrics.items():
            if times:
                avg_time = sum(times) / len(times)
                median_time = sorted(times)[len(times) // 2]
                p95_time = sorted(times)[int(len(times) * 0.95)] if len(times) > 5 else max(times)
                min_time = min(times)
                max_time = max(times)
                target = self.targets[method]

                summary[method] = {
                    "avg_ms": round(avg_time, 2),
                    "median_ms": round(median_time, 2),
                    "p95_ms": round(p95_time, 2),
                    "min_ms": round(min_time, 2),
                    "max_ms": round(max_time, 2),
                    "target_ms": target,
                    "within_target": p95_time <= target,
                    "samples": len(times),
                    "variance": round(max_time - min_time, 2),
                }
            else:
                summary[method] = {
                    "avg_ms": 0,
                    "median_ms": 0,
                    "p95_ms": 0,
                    "min_ms": 0,
                    "max_ms": 0,
                    "target_ms": self.targets[method],
                    "within_target": True,
                    "samples": 0,
                    "variance": 0,
                }

        summary["optimization_states"] = dict(self.optimization_states)
        summary["stats"] = dict(self.stats)

        return summary

    def get_recommendations(self) -> list[str]:
        """Get performance optimization recommendations."""
        recommendations = []

        for method, times in self.metrics.items():
            if not times:
                continue

            target = self.targets[method]
            p95_time = sorted(times)[int(len(times) * 0.95)] if len(times) > 5 else max(times)
            variance = max(times) - min(times)

            if p95_time > target * 3:
                recommendations.append(
                    f"URGENT: {method} search P95 ({p95_time:.1f}ms) is 3x over target ({target}ms)"
                )
            elif p95_time > target * 1.5:
                recommendations.append(
                    f"ATTENTION: {method} search P95 ({p95_time:.1f}ms) exceeds target ({target}ms)"
                )

            if variance > target * 10:
                recommendations.append(
                    f"HIGH VARIANCE: {method} search varies by {variance:.1f}ms (inconsistent performance)"
                )

        # Optimization recommendations
        fuzzy_candidates = self.optimization_states["fuzzy_max_candidates"]
        if fuzzy_candidates > 500:
            recommendations.append(
                f"OPTIMIZE: Consider reducing fuzzy candidates from {fuzzy_candidates} to improve consistency"
            )

        return recommendations

    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        for method in self.metrics:
            self.metrics[method].clear()
        self.stats = {"total_searches": 0, "auto_optimizations": 0, "performance_alerts": 0}
        logger.info("Performance metrics reset")

    def get_optimization_settings(self) -> dict[str, Any]:
        """Get current optimization settings for other components."""
        return self.optimization_states.copy()


# Global performance monitor instance
_performance_monitor: PerformanceMonitor | None = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor
