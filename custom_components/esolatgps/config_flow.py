"""Config flow for EsolatGPS integration."""
from __future__ import annotations
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_SCAN_INTERVAL
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    # Convert scan_interval from minutes to timedelta for validation
    scan_interval = data[CONF_SCAN_INTERVAL]
    if not MIN_SCAN_INTERVAL <= scan_interval <= MAX_SCAN_INTERVAL:
        raise ValueError(
            f"Scan interval must be between {MIN_SCAN_INTERVAL} and {MAX_SCAN_INTERVAL} minutes"
        )  
    return {"title": "eSolat GPS"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EsolatGPS."""
    VERSION = 1
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_SCAN_INTERVAL,
                            default=DEFAULT_SCAN_INTERVAL,
                        ): vol.All(
                            vol.Coerce(int),
                            vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                        ),
                    }
                ),
            )

        try:
            info = await validate_input(self.hass, user_input)
        except ValueError as err:
            errors["base"] = "invalid_scan_interval"
            _LOGGER.error("Invalid scan interval: %s", err)
        except Exception:  # pylint: disable=broad-except
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                    ),
                }
            ),
            errors=errors,
        )