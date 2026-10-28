"""EsolatGPS integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .card_registration import async_register_card, async_unregister_card
from .const import DOMAIN
from .coordinator import EsolatGPSConfigEntry, EsolatGPSCoordinator, cache_store

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve and register the bundled eSolat GPS Lovelace card."""
    await async_register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: EsolatGPSConfigEntry) -> bool:
    """Set up EsolatGPS from a config entry."""
    # Re-sync the card resource: removing the integration deletes it, and async_setup does
    # not run again when the integration is added back without a restart.
    await async_register_card(hass)

    coordinator = EsolatGPSCoordinator(hass, entry)
    # Raises ConfigEntryNotReady (HA retries setup) when no provider can be reached
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: EsolatGPSConfigEntry) -> None:
    """Apply a new update interval or Aladhan method."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: EsolatGPSConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the card's dashboard resource when the last entry is deleted.

    Not done on unload: reloading an entry should not make the card disappear.
    """
    others = [
        e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id
    ]
    if not others:
        await async_unregister_card(hass)
        await cache_store(hass).async_remove()
