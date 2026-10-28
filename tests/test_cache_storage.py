"""Timetables are kept in .storage, so a restart or reload does not refetch them."""
from unittest.mock import patch

from homeassistant.core import HomeAssistant

from custom_components.esolatgps.coordinator import STORAGE_KEY

from .test_coordinator import KJ, SG, frozen  # noqa: F401
from .test_diagnostic_sensors import _move, _setup


def _calls(mock_http, host):
    return sum(1 for c in mock_http.mock_calls if host in str(c[1]))


async def _reload(hass, entry):
    with patch("custom_components.esolatgps.async_register_card"):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()


async def test_reload_reuses_saved_timetables(hass: HomeAssistant, mock_http, hass_storage) -> None:
    entry = await _setup(hass, mock_http)
    saved = hass_storage[STORAGE_KEY]["data"]
    assert list(saved["jakim"]) == ["SGR01"]
    assert len(saved["aladhan"]) == 1
    before = hass.states.get("sensor.esolat_sgr01").state
    jakim, aladhan = _calls(mock_http, "waktusolat"), _calls(mock_http, "aladhan")

    await _reload(hass, entry)

    assert _calls(mock_http, "waktusolat") == jakim
    assert _calls(mock_http, "aladhan") == aladhan
    assert hass.states.get("sensor.esolat_sgr01").state == before
    assert hass.states.get("sensor.esolat_home").attributes["subuh"]


async def test_unreadable_cache_is_ignored(hass: HomeAssistant, mock_http, hass_storage) -> None:
    hass_storage[STORAGE_KEY] = {"version": 1, "key": STORAGE_KEY, "data": {"jakim": {"SGR01": {"oops": 1}}}}
    await _setup(hass, mock_http)
    assert hass.states.get("sensor.esolat_home").attributes["subuh"]
    assert "data" in hass_storage[STORAGE_KEY]["data"]["jakim"]["SGR01"]


async def test_removing_entry_deletes_cache(hass: HomeAssistant, mock_http, hass_storage) -> None:
    entry = await _setup(hass, mock_http)
    assert STORAGE_KEY in hass_storage
    with patch("custom_components.esolatgps.async_unregister_card"):
        await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()
    assert STORAGE_KEY not in hass_storage



async def test_unused_entries_are_cleared_from_disk(hass: HomeAssistant, mock_http, hass_storage, frozen) -> None:  # noqa: F811
    await _setup(hass, mock_http)
    # Person comes home: the Singapore Aladhan day is no longer used
    await _move(hass, frozen, "person.zubir", KJ)
    assert hass_storage[STORAGE_KEY]["data"]["aladhan"] == []
    assert list(hass_storage[STORAGE_KEY]["data"]["jakim"]) == ["SGR01"]
    # Everyone leaves Malaysia: SGR01 goes from disk too
    hass.states.async_set("zone.home", "0", {"latitude": SG[0], "longitude": SG[1]})
    await _move(hass, frozen, "person.zubir", SG)
    assert hass_storage[STORAGE_KEY]["data"]["jakim"] == {}
    assert len(hass_storage[STORAGE_KEY]["data"]["aladhan"]) == 1
