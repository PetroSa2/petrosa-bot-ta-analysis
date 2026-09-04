"""
Vendored Data Manager client SDK (petrosa-bot-ta-analysis#267).

Why vendored instead of an installed dependency
-------------------------------------------------
The wrapper in `ta_bot/services/data_manager_client.py` originally imported a
top-level `data_manager_client` package that was never actually installable:
`petrosa-data-manager`'s `setup.py` packages its client SDK source directory
(`client/`) under the pip name `petrosa_data_manager_client`, but
`find_packages()` discovers the importable module name `client`, not
`data_manager_client` — and no CI workflow in that repo publishes the package
anywhere (no PyPI step, no git tag consumed by any other repo). The import
was therefore guaranteed to fail (`ModuleNotFoundError`) in every deployed
image, which a bare `except ImportError` swallowed silently, permanently
routing every trading signal through a legacy raw-MySQL `INSERT` path that
nothing reads.

This module vendors the working client source
(`petrosa-data-manager/client/{client,exceptions,models}.py`, verified
functionally identical at vendor time) directly into this repo, mirroring the
pattern already used by `petrosa-binance-data-extractor` (`clients/data_manager_client.py`)
and `petrosa-tradeengine` (`shared/mysql_client.py` + local Data Manager
client), which each vendor their own local client rather than depending on
this unpublished package. This guarantees the import always succeeds in the
built image — no external package registry, no version-drift risk between
what's declared and what's actually installed.

If `petrosa-data-manager` ever ships a properly published, importable
`data_manager_client` package, this vendored copy can be retired in favor of
a real pip dependency — track that as a follow-up, not a blocker for #267.
"""

from .client import DataManagerClient
from .exceptions import (
    APIError,
    ConnectionError,
    DataManagerError,
    TimeoutError,
    ValidationError,
)

__all__ = [
    "DataManagerClient",
    "APIError",
    "ConnectionError",
    "DataManagerError",
    "TimeoutError",
    "ValidationError",
]
