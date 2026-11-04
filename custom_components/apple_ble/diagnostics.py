"""Diagnostics support for Apple BLE."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import AppleBleConfigEntry

TO_REDACT = {"unique_id", "address"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AppleBleConfigEntry
) -> dict[str, Any]:
    """Return the entry data and the last AirPods state, redacted."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(
            {"data": dict(entry.data), "unique_id": entry.unique_id}, TO_REDACT
        ),
        "data": asdict(coordinator.data) if coordinator.data is not None else None,
        "best_rssi": coordinator.best_rssi,
        "apple_devices_nearby": coordinator.apple_devices_nearby,
    }
