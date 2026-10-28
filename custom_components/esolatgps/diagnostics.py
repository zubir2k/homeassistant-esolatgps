"""Diagnostics for eSolat GPS: what each location resolved to, with locations redacted."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import EsolatGPSConfigEntry

# Anything that pinpoints where a person is
TO_REDACT = {"gps", "state", "region", "zone_name", "location", "latitude", "longitude"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EsolatGPSConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": {"data": dict(entry.data), "options": dict(entry.options)},
        "last_update_success": coordinator.last_update_success,
        "update_interval": str(coordinator.update_interval),
        "hijri": coordinator.hijri,
        "zone_data_version": coordinator._zones.version if coordinator._zones else None,
        "cached_zone_months": sorted(coordinator._months),
        "locations": async_redact_data(coordinator.data or {}, TO_REDACT),
    }
