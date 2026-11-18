"""Config flow for EsolatGPS integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    ALADHAN_METHODS,
    CONF_ALADHAN_METHOD,
    DOMAIN,
    WAKTUSOLAT_ZONES_URL,
)

_LOGGER = logging.getLogger(__name__)

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
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            if await _async_can_reach_provider(self.hass):
                return self.async_create_entry(
                    title="eSolat GPS",
                    data={},
                    options={
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
        """Options: calculation method used outside Malaysia."""
        return EsolatGPSOptionsFlow()


class EsolatGPSOptionsFlow(OptionsFlow):
    """Change the Aladhan method without re-adding the integration."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        entry = self.config_entry
        method = _valid_method(
            entry.options.get(CONF_ALADHAN_METHOD, entry.data.get(CONF_ALADHAN_METHOD, "auto"))
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ALADHAN_METHOD, default=method): METHOD_SELECTOR,
                }
            ),
        )
