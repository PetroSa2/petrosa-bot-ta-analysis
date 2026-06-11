"""Unit tests for BotTaAnalysisHealthEvaluator (#248, P2.7 AC4)."""

import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
from petrosa_otel.evaluators import ConsecutiveSamplesHysteresis
from petrosa_otel.evaluators.publisher import (
    EVALUATOR_SUBJECT_TEMPLATE,
    NatsVerdictPublisher,
)

from ta_bot.evaluators import (
    BotTaAnalysisHealthEvaluator,
    build_bot_ta_analysis_health_evaluator,
)


class FakeClock:
    def __init__(self, start: datetime, step: timedelta) -> None:
        self._t = start
        self._step = step

    def __call__(self) -> datetime:
        now = self._t
        self._t = self._t + self._step
        return now


class MetricsSource:
    def __init__(self) -> None:
        self.snap = {
            "nats_connected": True,
            "mysql_healthy": True,
            "analysis_latency_s": 0.5,
            "signals_emitted": 0,
        }

    def __call__(self) -> dict:
        return dict(self.snap)


class FakeNats:
    def __init__(self) -> None:
        self.messages: list[tuple[str, bytes]] = []

    async def publish(self, subject: str, payload: bytes) -> None:
        self.messages.append((subject, payload))


def _make(source, clock, *, publisher=None, n: int = 1):
    return BotTaAnalysisHealthEvaluator(
        metrics_source=source,
        publisher=publisher,
        hysteresis=ConsecutiveSamplesHysteresis(n=n),
        time_source=clock,
    )


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 5, 27, 12, 0, 0, tzinfo=UTC), timedelta(seconds=15))


@pytest.mark.asyncio
async def test_first_sample_is_unknown(clock):
    ev = _make(MetricsSource(), clock)
    verdict, reason = await ev.evaluate()
    assert verdict == "unknown"
    assert "baseline" in reason.lower()


@pytest.mark.asyncio
async def test_healthy_when_connected_and_ok(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    await ev.evaluate()
    verdict, reason = await ev.evaluate()
    assert verdict == "healthy"
    assert "candle-data ok" in reason


@pytest.mark.asyncio
async def test_unhealthy_when_nats_disconnected(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    await ev.evaluate()
    src.snap["nats_connected"] = False
    verdict, reason = await ev.evaluate()
    assert verdict == "unhealthy"
    assert "NATS" in reason


@pytest.mark.asyncio
async def test_unhealthy_when_mysql_unhealthy(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    await ev.evaluate()
    src.snap["mysql_healthy"] = False
    verdict, reason = await ev.evaluate()
    assert verdict == "unhealthy"
    assert "candle-data" in reason.lower()


@pytest.mark.asyncio
async def test_unhealthy_on_high_latency(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    await ev.evaluate()
    src.snap["analysis_latency_s"] = 8.0  # > 5s threshold
    verdict, reason = await ev.evaluate()
    assert verdict == "unhealthy"
    assert "latency" in reason


@pytest.mark.asyncio
async def test_unhealthy_on_signal_collapse(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    await ev.evaluate()  # prime
    signals = 0
    for _ in range(4):
        signals += 1  # ~0.067 signals/s baseline
        src.snap["signals_emitted"] = signals
        verdict, _ = await ev.evaluate()
        assert verdict == "healthy"
    # Emission stops while everything else stays nominal.
    verdict, reason = await ev.evaluate()
    assert verdict == "unhealthy"
    assert "signal emission collapsed" in reason


@pytest.mark.asyncio
async def test_counter_reset_returns_unknown(clock):
    src = MetricsSource()
    ev = _make(src, clock)
    src.snap["signals_emitted"] = 500
    await ev.evaluate()
    src.snap["signals_emitted"] = 3  # pod restart
    verdict, reason = await ev.evaluate()
    assert verdict == "unknown"
    assert "reset" in reason.lower()


@pytest.mark.asyncio
async def test_publishes_on_bot_ta_analysis_subject(clock):
    src = MetricsSource()
    nats = FakeNats()
    publisher = NatsVerdictPublisher(nats_client=nats)
    ev = _make(src, clock, publisher=publisher, n=1)

    await ev.tick()  # unknown baseline
    await ev.tick()  # healthy

    assert nats.messages, "evaluator did not publish"
    subject, payload = nats.messages[-1]
    assert subject == "evaluator.bot-ta-analysis.verdict"
    assert subject == EVALUATOR_SUBJECT_TEMPLATE.format(subsystem="bot-ta-analysis")
    body = json.loads(payload.decode())
    assert body["subsystem"] == "bot-ta-analysis"
    assert body["verdict"] == "healthy"


@pytest.mark.asyncio
async def test_hysteresis_suppresses_single_flap(clock):
    src = MetricsSource()
    ev = _make(src, clock, n=3)

    await ev.tick()  # unknown baseline
    for _ in range(3):
        v = await ev.tick()
    assert v.verdict == "healthy"

    # One MySQL-down sample must NOT flip the committed verdict (n=3).
    src.snap["mysql_healthy"] = False
    v = await ev.tick()
    assert v.verdict == "healthy"


def test_build_returns_none_without_nats():
    class _Pub:
        nats_client = None

    class _Listener:
        publisher = _Pub()

    assert build_bot_ta_analysis_health_evaluator(_Listener()) is None


def test_build_returns_evaluator_with_nats():
    class _Pub:
        nats_client = FakeNats()

    class _Listener:
        publisher = _Pub()

        def get_health_metrics(self):
            return {
                "nats_connected": True,
                "mysql_healthy": True,
                "analysis_latency_s": 0.0,
                "signals_emitted": 0,
            }

    ev = build_bot_ta_analysis_health_evaluator(_Listener())
    assert isinstance(ev, BotTaAnalysisHealthEvaluator)


@pytest.mark.asyncio
async def test_emit_loop_tolerates_source_errors(clock):
    """The emit loop logs and continues when a tick raises (never crashes)."""

    def _bad_source() -> dict:
        raise RuntimeError("boom")

    ev = BotTaAnalysisHealthEvaluator(
        metrics_source=_bad_source,
        publisher=None,
        hysteresis=ConsecutiveSamplesHysteresis(n=1),
        emit_interval_s=0.01,
        time_source=clock,
    )
    await ev.start()
    await asyncio.sleep(0.03)
    await ev.stop()  # must not raise despite the failing source


@pytest.mark.asyncio
async def test_start_stop_lifecycle_publishes(clock):
    """start() runs the emit loop (at least one tick) and stop() cancels it."""
    src = MetricsSource()
    nats = FakeNats()
    publisher = NatsVerdictPublisher(nats_client=nats)
    ev = BotTaAnalysisHealthEvaluator(
        metrics_source=src,
        publisher=publisher,
        hysteresis=ConsecutiveSamplesHysteresis(n=1),
        emit_interval_s=0.01,
        time_source=clock,
    )
    await ev.start()
    await ev.start()  # idempotent — second call is a no-op
    # Let the loop tick a few times (unknown → healthy).
    await asyncio.sleep(0.05)
    await ev.stop()
    await ev.stop()  # idempotent when already stopped

    assert nats.messages, "emit loop did not publish"
    subject, _ = nats.messages[-1]
    assert subject == "evaluator.bot-ta-analysis.verdict"
