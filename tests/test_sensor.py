"""Current/next prayer logic of sensor.esolatnow (Kajang, 28 Oct 2026)."""
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.esolatgps.const import DOMAIN

from .test_init import GOOD, FETCH, HIJRI


async def _setup(hass: HomeAssistant, freezer, when: str, data=GOOD):
    freezer.move_to(when)
    hass.states.async_set("zone.home", "0", {"latitude": 3.02, "longitude": 101.79})
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={CONF_SCAN_INTERVAL: 15})
    entry.add_to_hass(hass)
    with (
        patch(FETCH, return_value=data),
        patch(HIJRI, return_value="17 Jamadil Awwal 1448"),
        patch("custom_components.esolatgps.async_register_card"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return hass.states.get("sensor.esolatnow")


@pytest.mark.parametrize(
    ("when", "current", "nxt", "remaining"),
    [
        ("2026-10-27T21:40:00+00:00", "Imsak", "Subuh", "8 minutes"),            # 05:40 MYT
        ("2026-10-27T23:10:00+00:00", "Isyraq", "Dhuha", "10 minutes"),          # 07:10
        ("2026-10-28T02:00:00+00:00", "Dhuha", "Zohor", "3 hours, 0 minutes"),   # 10:00
        ("2026-10-28T08:20:00+00:00", "Asar", "Maghrib", "2 hours, 39 minutes"), # 16:20
        ("2026-10-28T13:00:00+00:00", "Isyak", "Imsak", "8 hours, 38 minutes"),  # 21:00, to tomorrow's Imsak
        ("2026-10-27T19:00:00+00:00", "Isyak", "Imsak", "2 hours, 38 minutes"),  # 03:00, before today's Imsak
    ],
)
async def test_current_and_next(hass, freezer, when, current, nxt, remaining) -> None:
    state = await _setup(hass, freezer, when)
    home = state.attributes["array"]["home"]
    assert (home["current"], home["next"], home["time_remaining"]) == (current, nxt, remaining)
    assert home["location"] == "Saujana Impian, Hulu Langat"
    assert state.state == "1"
    assert state.attributes["hijri"] == "17 Jamadil Awwal 1448"


async def test_one_hour_is_singular(hass, freezer) -> None:
    home = (await _setup(hass, freezer, "2026-10-28T03:59:00+00:00")).attributes["array"]["home"]
    assert home["time_remaining"] == "1 hour, 1 minute"


async def test_countdown_ticks_every_minute(hass, freezer) -> None:
    await _setup(hass, freezer, "2026-10-28T02:00:00+00:00")
    freezer.tick(60)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    home = hass.states.get("sensor.esolatnow").attributes["array"]["home"]
    assert home["time_remaining"] == "2 hours, 59 minutes"


async def test_location_without_times_is_left_out(hass, freezer) -> None:
    partial = {"state": "Somewhere", "attributes": {**GOOD["attributes"], "zohor": ""}}
    state = await _setup(hass, freezer, "2026-10-28T02:00:00+00:00", partial)
    # Dhuha's next (Zohor) is missing, and so is Zohor itself, so 10:00 matches nothing
    assert state.attributes["array"] == {}
    assert state.state == "0"
