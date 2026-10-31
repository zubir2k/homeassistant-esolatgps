"""Coordinator tests against recorded provider responses (Kajang SGR01 and Singapore, 28 Oct 2026)."""
import re
from datetime import timedelta

import aiohttp
import pytest
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.esolatgps.const import (
    ALADHAN_URL,
    CONF_ALADHAN_METHOD,
    DOMAIN,
    FLAG_LOCAL,
    FLAG_OUTSIDE,
    WAKTUSOLAT_ZONE_URL,
)
from custom_components.esolatgps.coordinator import EsolatGPSCoordinator

from .conftest import load_json

KJ = (3.0218853, 101.7915175)
SG = (1.3521, 103.8198)
KJ_URL = WAKTUSOLAT_ZONE_URL.format(zone="SGR01")
NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
TAKWIM = "https://www.e-solat.gov.my/index.php"
ALADHAN_RE = re.compile(re.escape(ALADHAN_URL) + r"/\d\d-\d\d-\d{4}")


@pytest.fixture(autouse=True)
def frozen(freezer):
    """10:00 MYT, 28 Oct 2026: same calendar day in Malaysia, Singapore and UTC."""
    freezer.move_to("2026-10-28T02:00:00+00:00")
    return freezer


def _coordinator(hass: HomeAssistant, options=None, data=None) -> EsolatGPSCoordinator:
    entry = MockConfigEntry(domain=DOMAIN, data=data or {}, options=options or {})
    entry.add_to_hass(hass)
    return EsolatGPSCoordinator(hass, entry)


def _mock_malaysia(mock_http, gps=None):
    mock_http.get(KJ_URL, json=gps or load_json("waktusolat_gps.json"))
    mock_http.get(NOMINATIM, json=load_json("nominatim_kajang.json"))


def _mock_singapore(mock_http):
    mock_http.get(NOMINATIM, json=load_json("nominatim_sg.json"))
    mock_http.get(ALADHAN_RE, json=load_json("aladhan_sg.json"))


async def _fetch(hass, coord, latlon, entity_id="zone.home"):
    return await coord._fetch_prayer_times(async_get_clientsession(hass), *latlon, entity_id)


# --- Interval -------------------------------------------------------------------------------

async def test_interval_from_options_then_data(hass: HomeAssistant) -> None:
    assert _coordinator(hass, options={CONF_SCAN_INTERVAL: 7}).update_interval == timedelta(minutes=7)
    assert _coordinator(hass, data={CONF_SCAN_INTERVAL: 30}).update_interval == timedelta(minutes=30)
    assert _coordinator(hass).update_interval == timedelta(minutes=15)


# --- Malaysia (waktusolat.app) -------------------------------------------------------------

async def test_malaysia_times_from_jakim(hass: HomeAssistant, mock_http) -> None:
    _mock_malaysia(mock_http)
    result = await _fetch(hass, _coordinator(hass), KJ)

    assert result["state"] == "Saujana Impian, Hulu Langat"
    a = result["attributes"]
    assert a["flag"] == FLAG_LOCAL
    assert a["zone"] == "SGR01"
    assert a["zone_name"].startswith("Gombak")
    assert a["region"] == "Selangor"
    assert a["country"] == "Malaysia"
    assert a["provider"] == "JAKIM (waktusolat.app)"
    assert a["hijri"] == "1448-05-17"
    assert a["gps"] == f"{KJ[0]},{KJ[1]}"
    # 28 Oct 2026, SGR01
    assert a["imsak_24h"] == "05:38:00"
    assert a["subuh_12h"] == "5:48 AM"
    assert a["syuruk_24h"] == "06:55:00"
    assert a["isyraq_24h"] == "07:07:00"  # Syuruk + 12
    assert a["dhuha_24h"] == "07:20:00"   # from JAKIM
    assert a["zohor_24h"] == "13:00:00"
    assert a["asar_24h"] == "16:19:00"
    assert a["maghrib_24h"] == "18:59:00"
    assert a["isyak_12h"] == "8:09 PM"
    assert a["subuh"] == "2026-10-27T21:48:00+00:00"


async def test_dhuha_falls_back_to_syuruk_plus_25(hass: HomeAssistant, mock_http) -> None:
    gps = load_json("waktusolat_gps.json")
    for row in gps["prayers"]:
        row.pop("dhuha")
    _mock_malaysia(mock_http, gps)
    a = (await _fetch(hass, _coordinator(hass), KJ))["attributes"]
    assert a["dhuha_24h"] == "07:20:00"


async def test_place_falls_back_to_zone_when_geocoding_fails(hass: HomeAssistant, mock_http) -> None:
    mock_http.get(KJ_URL, json=load_json("waktusolat_gps.json"))
    mock_http.get(NOMINATIM, status=429)
    result = await _fetch(hass, _coordinator(hass), KJ)
    assert result["state"].startswith("Gombak")
    assert result["attributes"]["region"] == "Selangor"
    assert result["attributes"]["country"] == "Malaysia"


async def test_month_is_fetched_once_per_zone(hass: HomeAssistant, mock_http) -> None:
    """Moving around inside a zone, or a second person in it, never refetches the timetable."""
    _mock_malaysia(mock_http)
    coord = _coordinator(hass)
    await _fetch(hass, coord, KJ)
    await _fetch(hass, coord, (2.9935, 101.7874), "person.a")   # Saujana Impian, also SGR01
    await _fetch(hass, coord, (3.0738, 101.5183), "person.b")   # Shah Alam, SGR01
    zone_calls = [c for c in mock_http.mock_calls if "waktusolat" in str(c[1])]
    assert len(zone_calls) == 1


async def test_month_rollover_refetches(hass: HomeAssistant, mock_http, frozen) -> None:
    _mock_malaysia(mock_http)
    coord = _coordinator(hass)
    await _fetch(hass, coord, KJ)
    frozen.move_to("2026-11-05" + "T02:00:00+00:00")
    await _fetch(hass, coord, KJ)  # October cache is stale -> asks again
    zone_calls = [c for c in mock_http.mock_calls if "waktusolat" in str(c[1])]
    assert len(zone_calls) == 2


async def test_first_of_month_before_8am_asks_for_the_malaysian_month(hass: HomeAssistant, mock_http, frozen) -> None:
    """waktusolat.app defaults to its UTC month; at 00:30 MYT on 1 Nov that is still October."""
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse

    october = load_json("waktusolat_gps.json")
    november = {**october, "month": "NOV", "month_number": 11}

    async def zone_month(method, url, data):
        asked = url.query.get("month")
        return AiohttpClientMockResponse(method, url, json=november if asked == "11" else october)

    mock_http.get(KJ_URL, side_effect=zone_month)
    mock_http.get(NOMINATIM, json=load_json("nominatim_kajang.json"))
    frozen.move_to("2026-11-01 00:30:00+08:00")
    result = await _fetch(hass, _coordinator(hass), KJ)
    assert result["attributes"]["subuh"]
    assert result["attributes"]["zone"] == "SGR01"
    call = next(c for c in mock_http.mock_calls if "waktusolat" in str(c[1]))
    assert call[1].query["year"] == "2026" and call[1].query["month"] == "11"


async def test_cached_month_survives_provider_outage(hass: HomeAssistant, mock_http) -> None:
    _mock_malaysia(mock_http)
    coord = _coordinator(hass)
    await _fetch(hass, coord, KJ)
    mock_http.clear_requests()
    mock_http.get(KJ_URL, status=503, text="down")
    mock_http.get(NOMINATIM, json=load_json("nominatim_kajang.json"))
    a = (await _fetch(hass, coord, KJ))["attributes"]
    assert a["zone"] == "SGR01"
    assert a["subuh_24h"] == "05:48:00"


async def test_different_zone_fetches_its_own_month(hass: HomeAssistant, mock_http) -> None:
    _mock_malaysia(mock_http)
    kl = load_json("waktusolat_gps.json")
    kl["zone"] = "WLY01"
    mock_http.get(WAKTUSOLAT_ZONE_URL.format(zone="WLY01"), json=kl)
    coord = _coordinator(hass)
    await _fetch(hass, coord, KJ)
    a = (await _fetch(hass, coord, (3.139, 101.6869), "person.kl"))["attributes"]
    assert a["zone"] == "WLY01"
    assert set(coord._months) == {"SGR01", "WLY01"}


async def test_near_border_point_abroad_goes_to_aladhan(hass: HomeAssistant, mock_http) -> None:
    """Woodlands is within the coastal tolerance of Johor Bahru, but Nominatim says Singapore."""
    _mock_singapore(mock_http)
    result = await _fetch(hass, _coordinator(hass), (1.445, 103.77), "person.zubir")
    assert result["attributes"]["flag"] == FLAG_OUTSIDE
    assert not [c for c in mock_http.mock_calls if "waktusolat" in str(c[1])]


async def test_aladhan_answer_reused_same_day(hass: HomeAssistant, mock_http) -> None:
    _mock_singapore(mock_http)
    coord = _coordinator(hass)
    await _fetch(hass, coord, SG)
    await _fetch(hass, coord, (SG[0] + 0.001, SG[1]))  # same ~1 km cell
    aladhan_calls = [c for c in mock_http.mock_calls if "aladhan" in str(c[1])]
    assert len(aladhan_calls) == 1


async def test_http_error_marks_location_unavailable(hass: HomeAssistant, mock_http) -> None:
    mock_http.get(KJ_URL, status=500, text="boom")
    result = await _fetch(hass, _coordinator(hass), KJ)
    assert result["state"] == "unavailable"
    assert result["attributes"]["location"] == "ERROR CODE:500"


async def test_client_error_marks_location_unavailable(hass: HomeAssistant, mock_http) -> None:
    mock_http.get(KJ_URL, exc=aiohttp.ClientError())
    result = await _fetch(hass, _coordinator(hass), KJ)
    assert result == {
        "state": "unavailable",
        "attributes": {"location": "Client error", "gps": f"{KJ[0]},{KJ[1]}"},
    }


async def test_wrong_month_is_unavailable(hass: HomeAssistant, mock_http, frozen) -> None:
    frozen.move_to("2026-11-05T02:00:00+00:00")  # response is still October
    _mock_malaysia(mock_http)
    result = await _fetch(hass, _coordinator(hass), KJ)
    assert result["state"] == "unavailable"
    assert result["attributes"]["location"] == "Unexpected error"


# --- Outside Malaysia (Aladhan) ------------------------------------------------------------

async def test_outside_malaysia_uses_aladhan(hass: HomeAssistant, mock_http) -> None:
    _mock_singapore(mock_http)
    result = await _fetch(hass, _coordinator(hass), SG, "person.zubir")

    assert result["state"] == "Bishan, Singapore, SG"
    a = result["attributes"]
    assert a["flag"] == FLAG_OUTSIDE
    assert a["provider"] == "Aladhan"
    assert a["method"] == "Majlis Ugama Islam Singapura, Singapore"
    assert a["timezone"] == "Asia/Singapore"
    assert a["country"] == "Singapore"
    assert a["subuh_24h"] == "05:28:00"
    assert a["syuruk_12h"] == "6:46 AM"
    assert a["isyraq_24h"] == "06:58:00"  # Sunrise + 12
    assert a["dhuha_24h"] == "07:11:00"   # Sunrise + 25
    assert a["isyak_24h"] == "20:01:00"
    assert a["subuh"] == "2026-10-27T21:28:00+00:00"
    # Auto: no method sent, Aladhan picks the local authority
    aladhan_calls = [c for c in mock_http.mock_calls if "aladhan" in str(c[1])]
    assert "method" not in aladhan_calls[0][1].query


async def test_aladhan_method_option_is_sent(hass: HomeAssistant, mock_http) -> None:
    _mock_singapore(mock_http)
    await _fetch(hass, _coordinator(hass, options={CONF_ALADHAN_METHOD: "3"}), SG)
    aladhan_calls = [c for c in mock_http.mock_calls if "aladhan" in str(c[1])]
    assert aladhan_calls[0][1].query["method"] == "3"


async def test_legacy_jakim_method_is_treated_as_auto(hass: HomeAssistant, mock_http) -> None:
    _mock_singapore(mock_http)
    await _fetch(hass, _coordinator(hass, options={CONF_ALADHAN_METHOD: "17"}), SG)
    aladhan_calls = [c for c in mock_http.mock_calls if "aladhan" in str(c[1])]
    assert "method" not in aladhan_calls[0][1].query


async def test_aladhan_asks_again_with_local_date(hass: HomeAssistant, mock_http, frozen) -> None:
    # 23:30 UTC on the 27th is already the 28th in Singapore
    frozen.move_to("2026-10-27T23:30:00+00:00")
    _mock_singapore(mock_http)
    await _fetch(hass, _coordinator(hass), SG)
    dates = [c[1].path.rsplit("/", 1)[1] for c in mock_http.mock_calls if "aladhan" in str(c[1])]
    assert dates == ["27-10-2026", "28-10-2026"]


async def test_aladhan_failure_keeps_place_without_times(hass: HomeAssistant, mock_http) -> None:
    mock_http.get(NOMINATIM, json=load_json("nominatim_sg.json"))
    mock_http.get(ALADHAN_RE, json={"code": 400, "status": "Bad Request", "data": "x"})
    result = await _fetch(hass, _coordinator(hass), SG)
    assert result["state"] == "Bishan, Singapore, SG"
    assert "subuh" not in result["attributes"]
    assert "Aladhan returned 400" in result["attributes"]["error"]


# --- Hijri ---------------------------------------------------------------------------------

async def test_hijri_date(hass: HomeAssistant, mock_http) -> None:
    mock_http.get(TAKWIM, json=load_json("tarikhtakwim.json"))
    assert await _coordinator(hass).fetch_hijri_date(async_get_clientsession(hass)) == "17 Jamadil Awwal 1448"


@pytest.mark.parametrize(
    "kwargs",
    [{"status": 503}, {"exc": aiohttp.ClientError()}, {"json": {"takwim": {"2026-10-28": "bad"}}}],
)
async def test_hijri_date_failures(hass: HomeAssistant, mock_http, kwargs) -> None:
    mock_http.get(TAKWIM, **kwargs)
    assert await _coordinator(hass).fetch_hijri_date(async_get_clientsession(hass)) == "unavailable"


# --- Full update ---------------------------------------------------------------------------

async def test_update_covers_people_and_home_and_caches_hijri(hass: HomeAssistant, mock_http) -> None:
    hass.states.async_set("zone.home", "0", {"latitude": KJ[0], "longitude": KJ[1]})
    hass.states.async_set("person.zubir", "away", {"latitude": SG[0], "longitude": SG[1]})
    hass.states.async_set("person.guest", "unknown", {})  # no GPS: skipped
    _mock_malaysia(mock_http)
    _mock_singapore(mock_http)
    mock_http.get(TAKWIM, json=load_json("tarikhtakwim.json"))

    coord = _coordinator(hass)
    data = await coord._async_update_data()
    assert set(data) == {"zone.home", "person.zubir"}
    assert coord.hijri == "17 Jamadil Awwal 1448"

    takwim_calls = lambda: sum("e-solat" in str(c[1]) for c in mock_http.mock_calls)
    before = takwim_calls()
    await coord._async_update_data()
    assert takwim_calls() == before  # once a day


async def test_update_fails_when_nothing_resolves(hass: HomeAssistant, mock_http) -> None:
    hass.states.async_set("zone.home", "0", {"latitude": KJ[0], "longitude": KJ[1]})
    mock_http.get(KJ_URL, exc=aiohttp.ClientError())
    with pytest.raises(UpdateFailed):
        await _coordinator(hass)._async_update_data()


# --- Reverse geocoding ---------------------------------------------------------------------

async def test_geocode_dedupes_and_survives_errors(hass: HomeAssistant, mock_http) -> None:
    coord = _coordinator(hass)
    session = async_get_clientsession(hass)
    mock_http.get(NOMINATIM, json={"address": {"town": "Kajang", "country": "Malaysia", "state": "Selangor"}})
    assert (await coord._reverse_geocode(session, 2.99, 101.78))["name"] == "Kajang"

    mock_http.clear_requests()
    mock_http.get(NOMINATIM, exc=aiohttp.ClientError())
    assert await coord._reverse_geocode(session, 2.5, 101.5) is None


async def test_geocode_cache_is_bounded(hass: HomeAssistant, mock_http) -> None:
    coord = _coordinator(hass)
    coord._geo_cache = {(i, i): {} for i in range(300)}
    mock_http.get(NOMINATIM, json=load_json("nominatim_kajang.json"))
    await coord._reverse_geocode(async_get_clientsession(hass), *KJ)
    assert len(coord._geo_cache) == 1
