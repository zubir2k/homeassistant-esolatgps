"""Diagnostic sensors: one per JAKIM zone in use (sensor.esolat_sgr01) and one for Aladhan."""
from datetime import timedelta
from unittest.mock import patch

from homeassistant.const import CONF_SCAN_INTERVAL, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.esolatgps.const import DOMAIN

from .conftest import load_json
from .test_coordinator import KJ, SG, TAKWIM, _mock_malaysia, _mock_singapore, frozen  # noqa: F401


async def _setup(hass: HomeAssistant, mock_http, home=KJ, person=SG):
    hass.states.async_set("zone.home", "0", {"latitude": home[0], "longitude": home[1]})
    hass.states.async_set("person.zubir", "away", {"latitude": person[0], "longitude": person[1]})
    _mock_malaysia(mock_http)
    _mock_singapore(mock_http)
    mock_http.get(TAKWIM, json=load_json("tarikhtakwim.json"))
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={CONF_SCAN_INTERVAL: 5})
    entry.add_to_hass(hass)
    with patch("custom_components.esolatgps.async_register_card"):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _move(hass, freezer, entity_id, latlon):
    hass.states.async_set(entity_id, "x", {"latitude": latlon[0], "longitude": latlon[1]})
    freezer.tick(timedelta(minutes=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_zone_and_aladhan_sensors(hass: HomeAssistant, mock_http) -> None:
    entry = await _setup(hass, mock_http)
    ent_reg = er.async_get(hass)

    zone = hass.states.get("sensor.esolat_sgr01")
    assert zone.state == "2026-10-28T02:00:00+00:00"  # fetched at 10:00 MYT
    assert zone.attributes["device_class"] == "timestamp"
    assert zone.attributes["locations"] == ["zone.home"]
    assert zone.attributes["negeri"] == "Selangor"
    assert zone.attributes["days"] > 27
    assert ent_reg.async_get("sensor.esolat_sgr01").entity_category is EntityCategory.DIAGNOSTIC

    aladhan = hass.states.get("sensor.esolat_aladhan")
    assert aladhan.state == "2026-10-28T02:00:00+00:00"
    assert aladhan.attributes["locations"] == ["person.zubir"]
    assert aladhan.attributes["timezones"] == ["Asia/Singapore"]
    assert aladhan.attributes["areas"] == 1
    assert ent_reg.async_get("sensor.esolat_aladhan").entity_category is EntityCategory.DIAGNOSTIC
    assert entry.runtime_data._aladhan_cache


async def test_unused_sources_are_removed_with_their_cache(hass: HomeAssistant, mock_http, frozen) -> None:  # noqa: F811
    entry = await _setup(hass, mock_http)
    coord = entry.runtime_data
    ent_reg = er.async_get(hass)

    # Person comes home: Aladhan sensor and its cache go, SGR01 now lists both
    await _move(hass, frozen, "person.zubir", KJ)
    assert ent_reg.async_get("sensor.esolat_aladhan") is None
    assert hass.states.get("sensor.esolat_aladhan") is None
    assert coord._aladhan_cache == {}
    assert hass.states.get("sensor.esolat_sgr01").attributes["locations"] == ["person.zubir", "zone.home"]

    # Everyone leaves Malaysia: SGR01 sensor and its cached month go, Aladhan comes back
    hass.states.async_set("zone.home", "0", {"latitude": SG[0], "longitude": SG[1]})
    await _move(hass, frozen, "person.zubir", SG)
    assert ent_reg.async_get("sensor.esolat_sgr01") is None
    assert coord._months == {} and coord._fetched == {}
    assert hass.states.get("sensor.esolat_aladhan").attributes["locations"] == ["person.zubir", "zone.home"]

    # Back in Kajang: SGR01 is refetched and its sensor re-created
    hass.states.async_set("zone.home", "0", {"latitude": KJ[0], "longitude": KJ[1]})
    await _move(hass, frozen, "person.zubir", KJ)
    assert hass.states.get("sensor.esolat_sgr01").state == "2026-10-28T02:18:00+00:00"


async def test_zone_left_before_restart_is_removed_on_setup(hass: HomeAssistant, mock_http) -> None:
    ent_reg = er.async_get(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={CONF_SCAN_INTERVAL: 5})
    entry.add_to_hass(hass)
    ent_reg.async_get_or_create(
        "sensor", DOMAIN, "esolat_source_phg01", suggested_object_id="esolat_phg01", config_entry=entry
    )
    hass.states.async_set("zone.home", "0", {"latitude": KJ[0], "longitude": KJ[1]})
    _mock_malaysia(mock_http)
    mock_http.get(TAKWIM, json=load_json("tarikhtakwim.json"))
    with patch("custom_components.esolatgps.async_register_card"):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert ent_reg.async_get("sensor.esolat_phg01") is None
    assert hass.states.get("sensor.esolat_sgr01") is not None


async def test_person_sensor_follows_gps(hass: HomeAssistant, mock_http, frozen) -> None:  # noqa: F811
    await _setup(hass, mock_http, person=KJ)
    ent_reg = er.async_get(hass)
    assert hass.states.get("sensor.esolat_zubir").state == "Saujana Impian, Hulu Langat"

    # GPS goes away: the sensor is removed, not left unavailable
    hass.states.async_set("person.zubir", "unknown", {})
    frozen.tick(timedelta(minutes=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert ent_reg.async_get("sensor.esolat_zubir") is None
    assert hass.states.get("sensor.esolat_zubir") is None

    # GPS comes back (or a new person appears) without a reload: the sensor is created
    await _move(hass, frozen, "person.zubir", KJ)
    assert hass.states.get("sensor.esolat_zubir").state == "Saujana Impian, Hulu Langat"
    await _move(hass, frozen, "person.guest", KJ)
    assert hass.states.get("sensor.esolat_guest") is not None


async def test_person_without_gps_at_startup_is_removed(hass: HomeAssistant, mock_http) -> None:
    ent_reg = er.async_get(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={CONF_SCAN_INTERVAL: 5})
    entry.add_to_hass(hass)
    ent_reg.async_get_or_create("sensor", DOMAIN, "esolat_dummy", suggested_object_id="esolat_dummy", config_entry=entry)
    hass.states.async_set("person.dummy", "unknown", {})
    hass.states.async_set("zone.home", "0", {"latitude": KJ[0], "longitude": KJ[1]})
    _mock_malaysia(mock_http)
    mock_http.get(TAKWIM, json=load_json("tarikhtakwim.json"))
    with patch("custom_components.esolatgps.async_register_card"):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert ent_reg.async_get("sensor.esolat_dummy") is None
    assert hass.states.get("sensor.esolat_home") is not None and hass.states.get("sensor.esolatnow") is not None


async def test_nothing_is_removed_when_an_update_fails(hass: HomeAssistant, mock_http, frozen) -> None:  # noqa: F811
    entry = await _setup(hass, mock_http, person=KJ)
    coord = entry.runtime_data
    coord.last_update_success = False
    coord.async_update_listeners()
    assert er.async_get(hass).async_get("sensor.esolat_zubir") is not None
