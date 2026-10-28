"""Serve and register the bundled eSolat GPS Lovelace card.

The card file ships inside the integration (frontend/esolatgps-card.js). Two things are
needed for dashboards to use it:

1. the folder has to be served over HTTP (a static path), and
2. the browser has to be told to load the script.

For (2) we prefer a real Lovelace *resource* (type "module"), the same way HACS cards and
other integrations with bundled cards do. It is visible under Settings > Dashboards >
Resources, Home Assistant reports a clear "Failed to load Lovelace resource" error in the
browser console if it cannot be loaded, and it is loaded together with every other card.

Dashboards whose resources are managed in YAML (or any case where the resource store is not
usable) fall back to ``add_extra_js_url``, which injects the script into every page.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "esolatgps-card.js"
CARD_URL_BASE = f"/{DOMAIN}_static"
CARD_URL = f"{CARD_URL_BASE}/{CARD_FILENAME}"

_URL_KEY = f"{DOMAIN}_card_url"
_INJECTED_KEY = f"{DOMAIN}_card_injected"
_LOCK_KEY = f"{DOMAIN}_card_lock"
_LOVELACE_KEY = "lovelace"


# --------------------------------------------------------------------------- #
# Lovelace access. Home Assistant changed how this is exposed over the years:
#   < 2025.2   hass.data["lovelace"] is a dict: {"mode": ..., "resources": ...}
#   2025.2+    LovelaceData dataclass with .mode and .resources
#   2026.2+    LovelaceData.resource_mode (.mode kept as a deprecated fallback)
# --------------------------------------------------------------------------- #
def _lovelace_resources(hass: HomeAssistant) -> tuple[str | None, Any]:
    """Return (resource_mode, resource_collection), or (None, None) if unavailable."""
    data = hass.data.get(_LOVELACE_KEY)
    if data is None:
        return None, None
    if isinstance(data, dict):
        return data.get("mode"), data.get("resources")
    mode = getattr(data, "resource_mode", None)
    if mode is None:
        mode = getattr(data, "mode", None)
    return mode, getattr(data, "resources", None)


async def _async_ensure_loaded(resources: Any) -> bool:
    """Make sure the resource store has been read from disk.

    Listing resources before that returns an empty list, which would make us create a
    duplicate of an entry that already exists. Reading ``async_get_info`` loads the store.
    """
    if getattr(resources, "loaded", True):
        return True
    try:
        await resources.async_get_info()
    except Exception:  # noqa: BLE001 - never let card registration break setup
        _LOGGER.debug("Could not load Lovelace resources", exc_info=True)
    return bool(getattr(resources, "loaded", False))


def _our_resources(resources: Any) -> list[dict[str, Any]]:
    return [
        item
        for item in (resources.async_items() or [])
        if str(item.get("url", "")).split("?", 1)[0] == CARD_URL
    ]


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and make dashboards load it.

    Called from ``async_setup`` and again from every ``async_setup_entry``. The static path
    and the script injection can only be done once per Home Assistant run, so those are
    guarded. The Lovelace resource is synced on every call, because deleting the last entry
    removes it and adding the integration back (without a restart) must restore it.
    """
    card_path = Path(__file__).parent / "frontend" / CARD_FILENAME
    if not card_path.is_file():
        _LOGGER.warning("eSolat GPS card not found at %s", card_path)
        return

    lock = hass.data.setdefault(_LOCK_KEY, asyncio.Lock())
    async with lock:
        url = hass.data.get(_URL_KEY)
        if url is None:
            await _async_register_static_path(hass, card_path.parent)
            # The cache-busting version changes whenever the card file changes, so a card
            # update always reaches browsers even if the integration version was not bumped.
            integration = await async_get_integration(hass, DOMAIN)
            digest = await hass.async_add_executor_job(_file_digest, card_path)
            url = f"{CARD_URL}?v={integration.version or '0'}-{digest}"
            hass.data[_URL_KEY] = url

        mode, resources = _lovelace_resources(hass)
        if mode == "storage" and resources is not None:
            try:
                if await _async_ensure_loaded(resources):
                    await _async_sync_resource(resources, url)
                    _LOGGER.debug("eSolat GPS card registered as Lovelace resource %s", url)
                    return
                _LOGGER.debug("Lovelace resources not loaded; injecting the card script instead")
            except Exception:  # noqa: BLE001
                _LOGGER.warning(
                    "Could not register the eSolat GPS card as a Lovelace resource; "
                    "injecting the card script instead",
                    exc_info=True,
                )

        # YAML-managed resources, or the resource store was not usable. The injected script
        # lives for the whole Home Assistant run, so add it only once.
        if not hass.data.get(_INJECTED_KEY):
            hass.data[_INJECTED_KEY] = True
            add_extra_js_url(hass, url)
            _LOGGER.debug("eSolat GPS card injected via add_extra_js_url: %s", url)


async def async_unregister_card(hass: HomeAssistant) -> None:
    """Remove our Lovelace resource (called when the integration is removed)."""
    mode, resources = _lovelace_resources(hass)
    if mode != "storage" or resources is None:
        return
    try:
        if not await _async_ensure_loaded(resources):
            return
        for item in _our_resources(resources):
            await resources.async_delete_item(item["id"])
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not remove the eSolat GPS Lovelace resource", exc_info=True)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
async def _async_register_static_path(hass: HomeAssistant, folder: Path) -> None:
    try:
        # HA 2024.7+
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_BASE, str(folder), cache_headers=False)]
        )
    except ImportError:
        # Older HA
        hass.http.register_static_path(CARD_URL_BASE, str(folder), cache_headers=False)
    except RuntimeError:
        _LOGGER.debug("eSolat GPS static path already registered")


async def _async_sync_resource(resources: Any, url: str) -> None:
    """Create our resource, or bring an existing one (even a manual one) up to date."""
    existing = _our_resources(resources)

    if not existing:
        await resources.async_create_item({"res_type": "module", "url": url})
        return

    keep, duplicates = existing[0], existing[1:]
    if keep.get("url") != url or keep.get("type") != "module":
        await resources.async_update_item(keep["id"], {"res_type": "module", "url": url})
    for extra in duplicates:
        await resources.async_delete_item(extra["id"])
