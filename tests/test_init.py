"""Setup, entities, unavailability and diagnostics tests for eSolat GPS."""
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_SCAN_INTERVAL, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.esolatgps.const import DOMAIN
from custom_components.esolatgps.diagnostics import async_get_config_entry_diagnostics

FETCH = "custom_components.esolatgps.coordinator.EsolatGPSCoordinator._fetch_prayer_times"
HIJRI = "custom_components.esolatgps.coordinator.EsolatGPSCoordinator.fetch_hijri_date"

GOOD = {
    "state": "Saujana Impian, Hulu Langat",
    "attributes": {
        "gps": "3.0218853,101.7915175",
        "flag": "local",
        "zone": "SGR01",
        "zone_name": "Gombak, Petaling, Sepang, Hulu Langat, Hulu Selangor, S.Alam",
        "region": "Selangor",
        "imsak": "2026-10-27T21:38:00+00:00",
        "subuh": "2026-10-27T21:48:00+00:00",
        "syuruk": "2026-10-27T22:55:00+00:00",
        "isyraq": "2026-10-27T23:07:00+00:00",
        "dhuha": "2026-10-27T23:20:00+00:00",
        "zohor": "2026-10-28T05:00:00+00:00",
        "asar": "2026-10-28T08:19:00+00:00",
        "maghrib": "2026-10-28T10:59:00+00:00",
        "isyak": "2026-10-28T12:09:00+00:00",
    },
}
BAD = {"state": "unavailable", "attributes": {"location": "Client error"}}


async def _setup(hass: HomeAssistant, fetch_result) -> MockConfigEntry:
    hass.states.async_set("zone.home", "0", {"latitude": 3.02, "longitude": 101.79})
    hass.states.async_set(
        "person.zubir", "home", {"latitude": 3.02, "longitude": 101.79, "friendly_name": "Zubir"}
    )
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={CONF_SCAN_INTERVAL: 15})
    entry.add_to_hass(hass)
    with (
        patch(FETCH, return_value=fetch_result),
        patch(HIJRI, return_value="6 Jamadil Awwal 1448"),
        patch("custom_components.esolatgps.async_register_card"),
        patch("custom_components.esolatgps.async_unregister_card"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_setup_creates_named_entities_on_service_device(hass: HomeAssistant) -> None:
    entry = await _setup(hass, GOOD)
    assert entry.state is ConfigEntryState.LOADED

    home = hass.states.get("sensor.esolat_home")
    assert home.state == "Saujana Impian, Hulu Langat"
    assert home.attributes["zone"] == "SGR01"
    assert home.attributes["friendly_name"] == "eSolat GPS Home prayer time"
    assert hass.states.get("sensor.esolat_zubir").attributes["friendly_name"] == "eSolat GPS Zubir prayer time"
    assert hass.states.get("sensor.esolatnow").attributes["hijri"] == "6 Jamadil Awwal 1448"

    reg = dr.async_get(hass)
    if hasattr(reg, "async_get_device_by_identifier"):  # HA 2026.10+
        device = reg.async_get_device_by_identifier((DOMAIN, entry.entry_id), entry.entry_id)
    else:
        device = reg.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device.entry_type is dr.DeviceEntryType.SERVICE
    ent_reg = er.async_get(hass)
    for eid in ("sensor.esolat_home", "sensor.esolat_zubir", "sensor.esolatnow"):
        assert ent_reg.async_get(eid).device_id == device.id

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_when_no_provider_answers(hass: HomeAssistant) -> None:
    entry = await _setup(hass, BAD)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_one_failed_location_is_unavailable(hass: HomeAssistant) -> None:
    async def fake(self, session, lat, lon, entity_id):
        return BAD if entity_id == "person.zubir" else GOOD

    hass.states.async_set("zone.home", "0", {"latitude": 3.02, "longitude": 101.79})
    hass.states.async_set("person.zubir", "home", {"latitude": 1.3, "longitude": 103.8, "friendly_name": "Zubir"})
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={CONF_SCAN_INTERVAL: 15})
    entry.add_to_hass(hass)
    with (
        patch(FETCH, fake),
        patch(HIJRI, return_value="6 Jamadil Awwal 1448"),
        patch("custom_components.esolatgps.async_register_card"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert hass.states.get("sensor.esolat_zubir").state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.esolat_home").state == "Saujana Impian, Hulu Langat"


async def test_diagnostics_redacts_location(hass: HomeAssistant) -> None:
    entry = await _setup(hass, GOOD)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    home = diag["locations"]["zone.home"]
    assert home["state"] == "**REDACTED**"
    assert home["attributes"]["gps"] == "**REDACTED**"
    assert home["attributes"]["zone"] == "SGR01"


async def test_options_change_reloads(hass: HomeAssistant) -> None:
    entry = await _setup(hass, GOOD)
    with (
        patch(FETCH, return_value=GOOD),
        patch(HIJRI, return_value="6 Jamadil Awwal 1448"),
    ):
        hass.config_entries.async_update_entry(entry, options={CONF_SCAN_INTERVAL: 45})
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    from datetime import timedelta
    assert entry.runtime_data.update_interval == timedelta(minutes=45)


async def test_removing_entry_removes_card_resource(hass: HomeAssistant) -> None:
    entry = await _setup(hass, GOOD)
    with patch("custom_components.esolatgps.async_unregister_card") as unregister:
        await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()
    unregister.assert_awaited_once()
