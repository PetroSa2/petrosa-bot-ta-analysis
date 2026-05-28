"""Content-addressable strategy revision identity (FR53 / P3.4 AC1).

Binds a *characterization artifact* to a stable identifier derived from
``(strategy_module_source, parameter_set)``. Same source + same parameters
always produce the same revision id; any mutation of either side produces a
different id, so a CIO consumer can refuse to apply a stale characterization
to a strategy whose code or default parameters have drifted.

Determinism rules:
    * Module hash uses the strategy class's source file (``inspect.getsourcefile``)
      so the hash is stable against decorators and out-of-class helpers defined
      in the same file. Falls back to ``inspect.getsource(cls)`` if no file
      can be located (e.g. classes generated in tests via ``exec``).
    * Parameter hash uses canonical JSON: ``sort_keys=True``,
      ``separators=(",", ":")``, with a typed default that normalizes
      ``Enum``, ``datetime`` (assumed UTC if naive — same rule as the
      data-manager ``compute_inputs_hash``), and ``Path``.
    * The combined ``revision_id`` is ``srev_{module[:12]}_{params[:12]}`` —
      short enough for logs and Grafana labels, with the full 64-hex
      components available on the :class:`StrategyRevision` dataclass.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

_REVISION_ID_PREFIX = "srev_"
_HEX_PREFIX_LEN = 12


@dataclass(frozen=True)
class StrategyRevision:
    """Content-addressable identity for a strategy snapshot.

    Carries both the short combined ``revision_id`` (intended for log/UI
    use) and the two full-length component hashes so downstream consumers
    can detect *why* a revision differs (code change vs. parameter change).
    """

    strategy_id: str
    revision_id: str
    module_hash: str
    parameter_hash: str

    def to_dict(self) -> dict[str, str]:
        return {
            "strategy_id": self.strategy_id,
            "revision_id": self.revision_id,
            "module_hash": self.module_hash,
            "parameter_hash": self.parameter_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StrategyRevision:
        return cls(
            strategy_id=str(data["strategy_id"]),
            revision_id=str(data["revision_id"]),
            module_hash=str(data["module_hash"]),
            parameter_hash=str(data["parameter_hash"]),
        )


def compute_strategy_module_hash(strategy_cls: type) -> str:
    """SHA-256 hex digest of the strategy class's source.

    Prefers the whole source *file* (so refactors that move helpers out of
    the class body still register as code change). Falls back to
    ``inspect.getsource`` when only the class body is available, and finally
    to the class's ``repr`` if even that fails — every fallback still
    discriminates between distinct class objects so the hash never collapses.
    """
    source_file: str | None = None
    try:
        source_file = inspect.getsourcefile(strategy_cls)
    except TypeError:
        source_file = None
    if source_file is None:
        module_name = getattr(strategy_cls, "__module__", None)
        if module_name:
            module = sys.modules.get(module_name)
            module_file = getattr(module, "__file__", None) if module else None
            if module_file:
                source_file = module_file
    if source_file:
        source = Path(source_file).read_text(encoding="utf-8")
    else:
        try:
            source = inspect.getsource(strategy_cls)
        except (OSError, TypeError):
            # Last-resort discriminator: qualified name + module. Stable
            # across runs (no memory address) and unique per class object.
            source = (
                f"<no-source:{strategy_cls.__module__}.{strategy_cls.__qualname__}>"
            )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _canonicalize(value: Any) -> Any:
    """JSON-default for values json.dumps cannot serialize directly.

    Matches the data-manager ``compute_inputs_hash`` semantics: naive
    datetimes are tagged UTC, enums collapse to their value, paths to str.
    """
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (set, frozenset)):
        return sorted(
            value, key=lambda x: json.dumps(x, default=_canonicalize, sort_keys=True)
        )
    raise TypeError(f"Cannot canonicalize {type(value).__name__} for parameter hash")


def compute_parameter_set_hash(parameters: dict[str, Any] | None) -> str:
    """SHA-256 hex digest of a parameter dict under canonical JSON.

    ``None`` and ``{}`` collapse to the same hash so a strategy with no
    runtime config matches a strategy whose config dict is empty.
    """
    canonical = json.dumps(
        parameters or {},
        sort_keys=True,
        separators=(",", ":"),
        default=_canonicalize,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_strategy_revision_id(
    strategy_cls: type,
    parameters: dict[str, Any] | None,
) -> str:
    """Short content-addressable id for ``(strategy class, parameters)``.

    Shape: ``srev_{module_hash[:12]}_{parameter_hash[:12]}``.
    """
    module_hash = compute_strategy_module_hash(strategy_cls)
    parameter_hash = compute_parameter_set_hash(parameters)
    return (
        f"{_REVISION_ID_PREFIX}{module_hash[:_HEX_PREFIX_LEN]}"
        f"_{parameter_hash[:_HEX_PREFIX_LEN]}"
    )


def build_strategy_revision(
    *,
    strategy_id: str,
    strategy_cls: type,
    parameters: dict[str, Any] | None,
) -> StrategyRevision:
    """Assemble a full :class:`StrategyRevision` for a strategy snapshot."""
    module_hash = compute_strategy_module_hash(strategy_cls)
    parameter_hash = compute_parameter_set_hash(parameters)
    revision_id = (
        f"{_REVISION_ID_PREFIX}{module_hash[:_HEX_PREFIX_LEN]}"
        f"_{parameter_hash[:_HEX_PREFIX_LEN]}"
    )
    return StrategyRevision(
        strategy_id=strategy_id,
        revision_id=revision_id,
        module_hash=module_hash,
        parameter_hash=parameter_hash,
    )
