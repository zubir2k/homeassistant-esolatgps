"""Base entity for eSolat GPS."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import get_device_info
from .coordinator import EsolatGPSCoordinator


class EsolatGPSEntity(CoordinatorEntity[EsolatGPSCoordinator]):
    """Common base: named in the context of the eSolat GPS service device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EsolatGPSCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = get_device_info(coordinator.config_entry.entry_id)
