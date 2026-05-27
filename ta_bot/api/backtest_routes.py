"""FastAPI route for triggering backtests over HTTP (FR2 / #239).

P3.1 (#234) shipped the backtest engine with a CLI surface only. This module
adds an HTTP API trigger surface so backtests can be launched by schedulers,
operators, or other services without a shell. The endpoint reuses the exact
same `BacktestEngine` + `ArtifactPersister` path as `python -m backtest`, so the
produced `CharacterizationArtifact` is identical to the CLI's (FR3 / P3.2
contract) — there is no parallel backtest implementation.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ta_bot.api.response_models import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class BacktestTriggerRequest(BaseModel):
    """Payload for POST /api/v1/backtest."""

    strategy_id: str = Field(..., description="Registered strategy_id to replay")
    range_from: datetime = Field(
        ...,
        alias="from",
        description="ISO-8601 start of the candle window (UTC assumed if naive)",
    )
    range_to: datetime = Field(
        ...,
        alias="to",
        description="ISO-8601 end of the candle window (UTC assumed if naive)",
    )
    symbol: str = Field("BTCUSDT", description="Trading symbol")
    period: str = Field("15m", description="Candle period")
    warmup: int = Field(
        200, ge=1, description="Minimum candles before strategies are evaluated"
    )
    max_candles: int = Field(
        1000, ge=1, description="Cap on data-manager candle fetches"
    )
    persist: bool = Field(
        True, description="Persist the artifact to petrosa-data-manager after the run"
    )
    parameter_overrides: dict[str, Any] | None = Field(
        None,
        description=(
            "Reserved for per-run strategy parameter overrides. The engine "
            "currently replays the registered strategy parameters and does not "
            "yet apply overrides; supplying a non-empty value returns HTTP 422."
        ),
    )

    model_config = {"populate_by_name": True}


class BacktestTriggerResponse(BaseModel):
    """Summary of a triggered backtest run (the full artifact is persisted)."""

    strategy_id: str
    symbol: str
    period: str
    range_from: str
    range_to: str
    candle_count: int
    signal_count: int
    schema_version: str
    source: str
    persisted: bool


@router.post(
    "/backtest",
    response_model=APIResponse[BacktestTriggerResponse],
    summary="Trigger a backtest run over HTTP",
    description=(
        "Replays a registered TA strategy against historical candles from "
        "petrosa-data-manager and emits a CharacterizationArtifact — the same "
        "engine and artifact contract as `python -m backtest`. When `persist` is "
        "true (default) the artifact is written to the data-manager "
        "`characterization_artifacts` collection."
    ),
)
async def trigger_backtest(
    payload: BacktestTriggerRequest,
) -> APIResponse[BacktestTriggerResponse]:
    range_from = payload.range_from
    if range_from.tzinfo is None:
        range_from = range_from.replace(tzinfo=UTC)
    range_to = payload.range_to
    if range_to.tzinfo is None:
        range_to = range_to.replace(tzinfo=UTC)

    if range_to < range_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'to' must be on or after 'from'",
        )
    if payload.parameter_overrides:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "parameter_overrides is accepted by the API contract but not yet "
                "applied by the backtest engine; omit it until engine support lands"
            ),
        )

    from backtest.data_source import DataManagerHistoricalSource
    from backtest.engine import BacktestEngine, BacktestRequest

    engine = BacktestEngine(
        data_source=DataManagerHistoricalSource(max_candles=payload.max_candles)
    )
    request = BacktestRequest(
        strategy_id=payload.strategy_id,
        symbol=payload.symbol,
        period=payload.period,
        range_from=range_from,
        range_to=range_to,
        warmup=payload.warmup,
    )

    try:
        # engine.run is synchronous (pandas + indicator math); keep the event
        # loop responsive by running it in a worker thread.
        artifact = await asyncio.to_thread(engine.run, request)
    except ValueError as exc:
        # Unknown strategy_id / invalid warmup — a client error.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Backtest run failed for %s", payload.strategy_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"backtest failed: {exc}",
        ) from exc

    persisted = False
    if payload.persist:
        from backtest.persistence import ArtifactPersister

        persisted = await ArtifactPersister().apersist(artifact)

    return APIResponse(
        success=True,
        data=BacktestTriggerResponse(
            strategy_id=artifact.strategy_id,
            symbol=artifact.symbol,
            period=artifact.period,
            range_from=artifact.range_from,
            range_to=artifact.range_to,
            candle_count=artifact.candle_count,
            signal_count=artifact.signal_count,
            schema_version=artifact.schema_version,
            source=artifact.source,
            persisted=persisted,
        ),
        metadata={"persisted": persisted, "requested_persist": payload.persist},
    )
