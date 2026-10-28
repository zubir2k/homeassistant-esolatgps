"""Config flow for EsolatGPS integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    ALADHAN_METHODS,
    CONF_ALADHAN_METHOD,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    WAKTUSOLAT_ZONES_URL,
)

_LOGGER = logging.getLogger(__name__)

INTERVAL_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=MIN_SCAN_INTERVAL,
        max=MAX_SCAN_INTERVAL,
        step=1,
        mode=NumberSelectorMode.BOX,
        unit_of_measurement="min",
    )
)

METHOD_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=list(ALADHAN_METHODS),
        mode=SelectSelectorMode.DROPDOWN,
        translation_key="aladhan_method",
    )
)


def _valid_method(value: Any) -> str:
    """A stored method that is no longer offered (e.g. JAKIM, 17) falls back to auto."""
    value = str(value)
    return value if value in ALADHAN_METHODS else "auto"


async def _async_can_reach_provider(hass: HomeAssistant) -> bool:
    """True when the JAKIM provider (waktusolat.app) answers."""
    try:
        async with async_get_clientsession(hass).get(
            WAKTUSOLAT_ZONES_URL, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            return resp.status == 200
    except (aiohttp.ClientError, TimeoutError):
        return False


class EsolatGPSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EsolatGPS."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step. A second entry is blocked by single_config_entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if await _async_can_reach_provider(self.hass):
                return self.async_create_entry(
                    title="eSolat GPS",
                    data={},
                    options={
                        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                        CONF_ALADHAN_METHOD: _valid_method(
                            user_input.get(CONF_ALADHAN_METHOD, "auto")
                        ),
                    },
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=(user_input or {}).get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): INTERVAL_SELECTOR,
                    vol.Required(
                        CONF_ALADHAN_METHOD,
                        default=(user_input or {}).get(CONF_ALADHAN_METHOD, "auto"),
                    ): METHOD_SELECTOR,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options: update interval and the calculation method used outside Malaysia."""
        return EsolatGPSOptionsFlow()


class EsolatGPSOptionsFlow(OptionsFlow):
    """Change the update interval and the Aladhan method without re-adding the integration."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_SCAN_INTERVAL] = int(user_input[CONF_SCAN_INTERVAL])
            return self.async_create_entry(data=user_input)

        entry = self.config_entry
        # Entries made before 0.4.0 keep the interval in data
        interval = entry.options.get(
            CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        method = _valid_method(
            entry.options.get(CONF_ALADHAN_METHOD, entry.data.get(CONF_ALADHAN_METHOD, "auto"))
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=interval): INTERVAL_SELECTOR,
                    vol.Required(CONF_ALADHAN_METHOD, default=method): METHOD_SELECTOR,
                }
            ),
        )
