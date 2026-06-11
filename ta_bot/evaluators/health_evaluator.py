"""bot-ta-analysis health evaluator (P2.7, petrosa_k8s#697 AC4 / #248).

Emits ``evaluator.bot-ta-analysis.verdict`` via the shared P2.1 framework
(:mod:`petrosa_otel.evaluators`) so the operator dashboard's evaluator strip
counts bot-ta-analysis among the reporting subsystems (FR17 / FR23 / FR32).

The verdict combines three health signals sampled from the running
``NATSListener`` (which owns the signal engine, candle data client, and the
signal publisher) on each emit tick:

1. **Indicator-compute latency** — rolling mean of the per-extraction
   ``analyze_candles`` duration. A sustained high value means the strategy
   computation is degrading (slow candle-data reads, CPU starvation, etc.).
2. **Candle-data connection health** — whether the most recent candle-data fetch
   succeeded. Repeated fetch failures mean the candle source (data-manager API)
   is unreachable, so no analysis can run.
3. **Signal-emission rate** — outbound signal count. TA signals are sparse
   (emitted only on candle-close extraction events), so the collapse check
   stays dormant until a meaningful emission baseline is established; it then
   trips if emission falls to a small fraction of that baseline.

Verdict vocabulary is the framework's locked three-state contract
(``healthy`` / ``unhealthy`` / ``unknown``); there is no separate ``degraded``
state, so any breached signal maps to ``unhealthy`` and the reason string names
which signal tripped (NFR-O5 verbatim render).

Hysteresis / cadence (AC4 / AC7, FR18 per-evaluator ``decision_window``): emits
every ``EMIT_INTERVAL_S`` (15s) and, via ``ConsecutiveSamplesHysteresis(n=3)``,
only flips the published verdict after 3 consecutive matching samples (~45s
decision window). Signals are bursty (extraction events are periodic), so
smoothing avoids flapping while a sustained problem surfaces within ~45s.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - py310 compatibility
    from datetime import timezone

    UTC = timezone.utc  # noqa: UP017

from petrosa_otel.evaluators import (
    ConsecutiveSamplesHysteresis,
    Evaluator,
    NatsVerdictPublisher,
)

if TYPE_CHECKING:
    from petrosa_otel.evaluators.base import HysteresisPolicy
    from petrosa_otel.evaluators.publisher import VerdictPublisher

logger = logging.getLogger(__name__)

SUBSYSTEM = "bot-ta-analysis"

# Cadence + smoothing (documented per AC4 / AC7).
EMIT_INTERVAL_S = 15.0
HYSTERESIS_SAMPLES = 3

# Indicator-compute latency: analyze_candles runs several strategies over ~250
# candles; a sustained mean above 5s indicates degraded computation (slow data
# reads, CPU starvation) rather than a single slow run.
DEFAULT_LATENCY_THRESHOLD_S = 5.0
# Signal-emission collapse: once a meaningful baseline exists, dropping below
# 10% of it means the analysis pipeline stalled.
DEFAULT_SIGNAL_COLLAPSE_RATIO = 0.1
# Minimum baseline emission rate (signals/s) before the collapse check may
# trip. TA signals are sparse (candle-close driven), so a near-zero baseline
# keeps the check dormant.
DEFAULT_MIN_SIGNAL_RATE = 0.02
# Rolling baseline window (8 samples ≈ 2 min at 15s).
DEFAULT_BASELINE_WINDOW = 8
DEFAULT_MIN_BASELINE_SAMPLES = 4


class BotTaAnalysisHealthEvaluator(Evaluator):
    """Subsystem evaluator for bot-ta-analysis compute→signal health."""

    def __init__(
        self,
        *,
        metrics_source: Callable[[], dict[str, Any]],
        publisher: VerdictPublisher | None = None,
        hysteresis: HysteresisPolicy | None = None,
        latency_threshold_s: float = DEFAULT_LATENCY_THRESHOLD_S,
        signal_collapse_ratio: float = DEFAULT_SIGNAL_COLLAPSE_RATIO,
        min_signal_rate: float = DEFAULT_MIN_SIGNAL_RATE,
        baseline_window: int = DEFAULT_BASELINE_WINDOW,
        min_baseline_samples: int = DEFAULT_MIN_BASELINE_SAMPLES,
        emit_interval_s: float = EMIT_INTERVAL_S,
        time_source: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(
            subsystem=SUBSYSTEM,
            publisher=publisher,
            hysteresis=hysteresis or ConsecutiveSamplesHysteresis(n=HYSTERESIS_SAMPLES),
        )
        self._metrics_source = metrics_source
        self._latency_threshold_s = latency_threshold_s
        self._signal_collapse_ratio = signal_collapse_ratio
        self._min_signal_rate = min_signal_rate
        self._min_baseline_samples = max(1, min_baseline_samples)
        self._emit_interval_s = emit_interval_s
        self._time = time_source or (lambda: datetime.now(UTC))

        self._signal_baseline: deque[float] = deque(maxlen=max(1, baseline_window))
        self._prev_signals: int | None = None
        self._prev_sample_at: datetime | None = None

        self._emit_task: asyncio.Task[Any] | None = None

    # ----- lifecycle -----

    async def start(self) -> None:
        """Start the periodic emit loop (idempotent)."""
        if self._emit_task is not None:
            return
        self._emit_task = asyncio.create_task(self._emit_loop())
        logger.info(
            "bot_ta_analysis_health_evaluator_started",
            extra={"subsystem": SUBSYSTEM, "emit_interval_s": self._emit_interval_s},
        )

    async def stop(self) -> None:
        """Stop the emit loop."""
        if self._emit_task is None:
            return
        self._emit_task.cancel()
        try:
            await self._emit_task
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"bot_ta_analysis_health_evaluator stop error: {exc}")
        self._emit_task = None

    async def _emit_loop(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception as exc:  # noqa: BLE001 — never crash the loop
                logger.warning(
                    "bot_ta_analysis_health_evaluator_tick_failed",
                    extra={"error": str(exc)},
                )
            await asyncio.sleep(self._emit_interval_s)

    # ----- framework hook -----

    async def evaluate(self) -> tuple[str, str]:
        """Compute the raw ``(verdict, reason)`` sample for the current state."""
        snapshot = self._metrics_source()
        now = self._time()

        signals = int(snapshot.get("signals_emitted", 0) or 0)
        latency_s = float(snapshot.get("analysis_latency_s", 0.0) or 0.0)
        nats_connected = bool(snapshot.get("nats_connected"))
        mysql_healthy = bool(snapshot.get("mysql_healthy", True))

        prev_signals = self._prev_signals
        prev_at = self._prev_sample_at

        self._prev_signals = signals
        self._prev_sample_at = now

        if prev_signals is None or prev_at is None:
            return "unknown", "establishing baseline (first sample)"

        if signals < prev_signals:
            self._signal_baseline.clear()
            return "unknown", "counter reset detected; rebaselining"

        # 1) Connectivity is the dominant signal.
        if not nats_connected:
            return "unhealthy", "NATS publisher disconnected; cannot emit signals"

        # 2) Candle-data / Data Manager connection health.
        if not mysql_healthy:
            return "unhealthy", "candle-data source unreachable (data-manager API)"

        # 3) Indicator-compute latency.
        if latency_s > self._latency_threshold_s:
            return (
                "unhealthy",
                f"indicator-compute latency {latency_s:.1f}s > "
                f"{self._latency_threshold_s:.1f}s threshold",
            )

        # 4) Signal-emission rate vs baseline (dormant until a real baseline).
        interval_s = (now - prev_at).total_seconds()
        signal_rate = (signals - prev_signals) / interval_s if interval_s > 0 else 0.0
        if (
            len(self._signal_baseline) >= self._min_baseline_samples
            and self._signal_baseline
        ):
            sig_baseline_mean = sum(self._signal_baseline) / len(self._signal_baseline)
            if (
                sig_baseline_mean >= self._min_signal_rate
                and signal_rate < self._signal_collapse_ratio * sig_baseline_mean
            ):
                self._signal_baseline.append(signal_rate)
                return (
                    "unhealthy",
                    f"signal emission collapsed: {signal_rate:.3f}/s vs baseline "
                    f"{sig_baseline_mean:.3f}/s",
                )
        self._signal_baseline.append(signal_rate)

        return (
            "healthy",
            f"compute {latency_s:.2f}s, {signal_rate:.3f} signals/s, candle-data ok",
        )


def build_bot_ta_analysis_health_evaluator(
    nats_listener: Any,
) -> BotTaAnalysisHealthEvaluator | None:
    """Construct an evaluator sourcing from a started ``NATSListener``.

    Publishes verdicts on the listener's signal publisher's NATS connection.
    Returns ``None`` if that publisher has no live NATS client. Call after
    ``nats_listener.start()``.
    """
    publisher = getattr(nats_listener, "publisher", None)
    nats_client = getattr(publisher, "nats_client", None) if publisher else None
    if nats_client is None:
        logger.warning(
            "bot_ta_analysis_health_evaluator not started: no NATS client available"
        )
        return None

    def _snapshot() -> dict[str, Any]:
        return nats_listener.get_health_metrics()

    verdict_publisher = NatsVerdictPublisher(nats_client=nats_client)
    return BotTaAnalysisHealthEvaluator(
        metrics_source=_snapshot,
        publisher=verdict_publisher,
    )
