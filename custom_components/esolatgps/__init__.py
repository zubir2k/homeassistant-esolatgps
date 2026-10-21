"""EsolatGPS integration."""
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.loader import async_get_integration

_LOGGER = logging.getLogger(__name__)

DOMAIN = "esolatgps"
PLATFORMS = ["sensor"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

CARD_FILENAME = "esolatgps-card.js"
CARD_URL_BASE = f"/{DOMAIN}_static"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve and auto-load the bundled eSolat GPS Lovelace card (runs once per HA start)."""
    await _async_register_card(hass)
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    if hass.data.get(f"{DOMAIN}_card_registered"):
        return

    card_path = Path(__file__).parent / "frontend" / CARD_FILENAME
    if not card_path.is_file():
        _LOGGER.warning("eSolat GPS card not found at %s", card_path)
        return

    integration = await async_get_integration(hass, DOMAIN)
    version = integration.version or "0"

    try:
        # HA 2024.7+
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_BASE, str(card_path.parent), cache_headers=False)]
        )
    except ImportError:
        # Older HA
        hass.http.register_static_path(CARD_URL_BASE, str(card_path.parent), cache_headers=False)

    # ?v= busts the browser cache whenever the integration version changes
    add_extra_js_url(hass, f"{CARD_URL_BASE}/{CARD_FILENAME}?v={version}")
    hass.data[f"{DOMAIN}_card_registered"] = True
    _LOGGER.debug("Registered eSolat GPS card at %s", CARD_URL_BASE)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EsolatGPS from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
