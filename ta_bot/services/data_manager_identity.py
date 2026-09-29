"""Shared identity headers for calls to the data-manager gateway."""

import logging
import os

logger = logging.getLogger(__name__)
_missing_token_warning_emitted = False


def data_manager_headers() -> dict[str, str]:
    """Return gateway identity headers without ever exposing the token."""
    global _missing_token_warning_emitted
    service_name = os.getenv("DM_SERVICE_NAME", "petrosa-bot-ta-analysis")
    token = os.getenv("DM_SERVICE_TOKEN")
    if not token and not _missing_token_warning_emitted:
        logger.warning("DM_SERVICE_TOKEN is unset; data-manager calls use service identity only")
        _missing_token_warning_emitted = True

    headers = {"X-Petrosa-Service": service_name}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
