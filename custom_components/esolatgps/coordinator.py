import logging
import aiohttp
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DEFAULT_SCAN_INTERVAL,
    ALADHAN_URL,
    NOMINATIM_UA,
    ALADHAN_METHODS,
    CONF_ALADHAN_METHOD,
    FLAG_LOCAL,
    FLAG_OUTSIDE,
    WAKTUSOLAT_ZONE_URL,
    WAKTUSOLAT_FIELDS,
    ISYRAQ_OFFSET_MINUTES,
    DHUHA_OFFSET_MINUTES,
)
from .zones import ZoneIndex

MYT = ZoneInfo("Asia/Kuala_Lumpur")

_LOGGER = logging.getLogger(__name__)

type EsolatGPSConfigEntry = ConfigEntry["EsolatGPSCoordinator"]


class EsolatGPSCoordinator(DataUpdateCoordinator[dict]):
    """Fetches prayer times for every person with GPS coordinates and the Home zone."""

    config_entry: EsolatGPSConfigEntry

    def __init__(self, hass: HomeAssistant, entry: EsolatGPSConfigEntry):
        """Initialize the coordinator with the user-configured scan interval."""
        interval = entry.options.get(
            CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="eSolat GPS",
            update_interval=timedelta(minutes=interval),
        )
        self.hijri = None  # e.g. "6 Jamadil Awwal 1448", refreshed once a day
        self._hijri_day = None
        self.geo = "https://nominatim.openstreetmap.org/reverse?format=json&"
        self._geo_cache = {}
        self._zones: ZoneIndex | None = None  # bundled polygons, loaded once
        self._months = {}  # {"SGR01": waktusolat month response}, refetched only when the month rolls over
        self._aladhan_cache = {}  # {(lat2, lon2, method): (local date, data, fetched at)}
        self._fetched = {}  # {"SGR01": when its month was fetched (UTC)}
        self._aladhan_used = set()  # Aladhan cache keys used during the current update
        # What the diagnostic sensors show: one entry per JAKIM zone in use, plus Aladhan when used
        self.diag: dict = {"zones": {}, "aladhan": None}

    async def _async_update_data(self):
        """Fetch data from API."""
        session = async_get_clientsession(self.hass)
        data = {}
        self._aladhan_used = set()

        for entity_id in self.hass.states.async_entity_ids("person"):
            entity = self.hass.states.get(entity_id)
            latitude = entity.attributes.get("latitude")
            longitude = entity.attributes.get("longitude")
            if latitude and longitude:
                data[entity_id] = await self._fetch_prayer_times(session, latitude, longitude, entity_id)
            else:
                _LOGGER.debug("Skipping %s as it lacks GPS coordinates", entity_id)

        # Home zone processing
        home = self.hass.states.get("zone.home")
        if home is not None:
            data["zone.home"] = await self._fetch_prayer_times(
                session, home.attributes.get("latitude"), home.attributes.get("longitude"), "zone.home"
            )

        # Nothing usable at all means the providers are unreachable: fail the update so
        # entities go unavailable and the coordinator logs it once (and once on recovery).
        if not any(v.get("attributes", {}).get("subuh") for v in data.values()):
            raise UpdateFailed("No prayer times could be retrieved from any provider")

        today = datetime.now(MYT).date()
        if self._hijri_day != today or not self.hijri:
            hijri = await self.fetch_hijri_date(session)
            if hijri != "unavailable":
                self.hijri, self._hijri_day = hijri, today

        self._update_diag(data)

        return data

    def _update_diag(self, data: dict) -> None:
        """Rebuild the diagnostics view and drop cached data nobody uses any more.

        A JAKIM zone stays cached (and keeps its diagnostic sensor) only while at least one
        tracked location is in it; the same goes for each Aladhan area.
        """
        in_zone: dict[str, list[str]] = {}
        on_aladhan: list[str] = []
        for entity_id, value in data.items():
            attrs = value.get("attributes", {})
            if attrs.get("zone"):
                in_zone.setdefault(attrs["zone"], []).append(entity_id)
            elif attrs.get("provider") == "Aladhan":
                on_aladhan.append(entity_id)

        for zone in set(self._months) - set(in_zone):
            _LOGGER.debug("Nobody is in %s any more; dropping its cached timetable", zone)
            self._months.pop(zone, None)
            self._fetched.pop(zone, None)
        for key in set(self._aladhan_cache) - self._aladhan_used:
            self._aladhan_cache.pop(key, None)

        version = self._zones.version if self._zones else None
        zones = {}
        for zone, locations in in_zone.items():
            month = self._months.get(zone)
            if month is None:
                continue
            info = self._zones.zone_info(zone) if self._zones else {}
            zones[zone] = {
                "fetched": self._fetched.get(zone),
                "negeri": info.get("negeri"),
                "daerah": info.get("daerah"),
                "month": f"{month.get('month')} {month.get('year')}".strip(),
                "days": len(month.get("prayers", [])),
                "locations": sorted(locations),
                "map_version": version,
            }

        aladhan = None
        if self._aladhan_cache:
            cached = list(self._aladhan_cache.values())
            aladhan = {
                "fetched": max(c[2] for c in cached),
                "areas": len(cached),
                "timezones": sorted({c[1]["meta"]["timezone"] for c in cached}),
                "methods": sorted({c[1]["meta"].get("method", {}).get("name") or "?" for c in cached}),
                "locations": sorted(on_aladhan),
            }
        self.diag = {"zones": zones, "aladhan": aladhan}

    async def fetch_hijri_date(self, session):
        """Fetch Hijri date from API."""
        url = "https://www.e-solat.gov.my/index.php"
        params = {
            "r": "esolatApi/tarikhtakwim",
            "period": "today",
            "datetype": "miladi"
        }

        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()
                    hijri_date = next(iter(data["takwim"].values()))
                    parts = hijri_date.split('-')
                    day = parts[2]
                    month_number = int(parts[1]) - 1
                    year = parts[0]

                    months = [
                        "Muharram", "Safar", "Rabi'ul Awwal", "Rabi'ul Akhir",
                        "Jamadil Awwal", "Jamadil Akhir", "Rejab", "Sha'aban",
                        "Ramadhan", "Syawal", "Zulkaedah", "Zulhijjah"
                    ]

                    return f"{day} {months[month_number]} {year}"
                else:
                    _LOGGER.error(f"Failed to fetch Hijri date: HTTP {response.status}")
                    return "unavailable"
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Client error fetching Hijri date: {e}")
            return "unavailable"
        except Exception as e:
            _LOGGER.error(f"Unexpected error fetching Hijri date: {e}")
            return "unavailable"

    async def _get_zone_index(self) -> ZoneIndex:
        if self._zones is None:
            self._zones = await self.hass.async_add_executor_job(ZoneIndex.load)
        return self._zones

    async def _get_month(self, session, zone: str, today) -> dict:
        """JAKIM month for a zone, from cache unless the month changed. Raises on failure with no usable cache."""
        cached = self._months.get(zone)
        if cached and cached.get("year") == today.year and cached.get("month_number") == today.month:
            return cached
        url = WAKTUSOLAT_ZONE_URL.format(zone=zone)
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
            if response.status != 200:
                raise _HttpError(response.status, await response.text())
            data = await response.json()
        self._months[zone] = data
        self._fetched[zone] = datetime.now(ZoneInfo("UTC"))
        return data

    async def _fetch_prayer_times(self, session, latitude, longitude, entity_id):
        """JAKIM prayer times for the coordinate's zone; Aladhan outside Malaysia.

        The zone is resolved offline from the bundled polygons, so a poll only touches the
        network for the place name (Nominatim, cached per ~100 m) and, once a month per zone,
        for the JAKIM timetable.
        """
        today = datetime.now(MYT).date()
        gps = f"{latitude},{longitude}"

        try:
            match = (await self._get_zone_index()).lookup(latitude, longitude)
            geo = await self._reverse_geocode(session, latitude, longitude) or {}
            # Matched only by the coastal tolerance: trust the geocoder if it places us abroad
            # (e.g. Woodlands, Singapore, is within a kilometre of Johor Bahru).
            if match and not match.exact and geo.get("country_code") not in (None, "MY"):
                match = None
            if match is None:
                return await self._fetch_aladhan(session, latitude, longitude, entity_id)

            data = await self._get_month(session, match.zone, today)

            row = next((d for d in data.get("prayers", []) if d.get("day") == today.day), None)
            if (
                row is None
                or data.get("year") != today.year
                or data.get("month_number") != today.month
            ):
                raise ValueError(
                    f"No row for {today.isoformat()} in waktusolat.app response "
                    f"({data.get('month')}/{data.get('year')})"
                )

            prayer_times = {}

            def put(key, ts):
                utc = datetime.fromtimestamp(ts, ZoneInfo("UTC"))
                prayer_times[key] = utc.isoformat()
                prayer_times[f"{key}_12h"] = self.convert_to_local_12time(ts)
                prayer_times[f"{key}_24h"] = self.convert_to_local_24time(ts)

            for field, key in WAKTUSOLAT_FIELDS.items():
                if row.get(field) is not None:
                    put(key, int(row[field]))

            syuruk = row.get("syuruk")
            if syuruk is not None:
                put("isyraq", int(syuruk) + ISYRAQ_OFFSET_MINUTES * 60)
                if row.get("dhuha") is None:
                    put("dhuha", int(syuruk) + DHUHA_OFFSET_MINUTES * 60)

            return {
                "state": geo.get("name") or match.daerah or match.zone,
                "attributes": {
                    "gps": gps,
                    "flag": FLAG_LOCAL,
                    "zone": match.zone,
                    "zone_name": match.daerah,
                    "region": geo.get("state") or match.negeri,
                    "country": geo.get("country") or "Malaysia",
                    "provider": "JAKIM (waktusolat.app)",
                    "timezone": "Asia/Kuala_Lumpur",
                    "hijri": row.get("hijri"),
                    **prayer_times,
                },
            }
        except _HttpError as e:
            _LOGGER.error("Error retrieving prayer times for %s: HTTP %s %s", entity_id, e.status, e.body)
            return {"state": "unavailable", "attributes": {"location": f"ERROR CODE:{e.status}", "gps": gps}}
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Client error retrieving prayer times for {entity_id}: {e}")
            return {"state": "unavailable", "attributes": {"location": "Client error", "gps": gps}}
        except Exception as e:
            _LOGGER.error(f"Unexpected error retrieving prayer times for {entity_id}: {e}")
            return {"state": "unavailable", "attributes": {"location": "Unexpected error", "gps": gps}}

    async def _reverse_geocode(self, session, latitude, longitude):
        """Best-effort place lookup from Nominatim, cached per ~100 m. Never raises.

        Returns {"name": "Bishan, Singapore", "state": ..., "country": ..., "country_code": "SG"} or None.
        """
        key = (round(float(latitude), 3), round(float(longitude), 3))
        if key in self._geo_cache:
            return self._geo_cache[key]
        try:
            async with session.get(
                f"{self.geo}lat={latitude}&lon={longitude}&zoom=14",
                headers={"User-Agent": NOMINATIM_UA, "Accept-Language": "en"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as geo_response:
                if geo_response.status != 200:
                    return None
                address = (await geo_response.json()).get("address", {})
        except Exception as e:  # noqa: BLE001
            _LOGGER.debug("Reverse geocode failed for %s,%s: %s", latitude, longitude, e)
            return None

        pick = lambda *keys: next((address[k] for k in keys if address.get(k)), None)
        locality = pick("suburb", "quarter", "neighbourhood", "village", "hamlet", "town")
        area = pick("district", "city", "town", "county", "state_district", "state", "region")
        parts = [p for p in (locality, area) if p]
        if len(parts) == 2 and parts[0] == parts[1]:
            parts = parts[:1]
        result = {
            "name": ", ".join(parts) or address.get("country"),
            "state": address.get("state") or address.get("region"),
            "country": address.get("country"),
            "country_code": (address.get("country_code") or "").upper() or None,
        }
        if len(self._geo_cache) > 256:
            self._geo_cache.clear()
        self._geo_cache[key] = result
        return result

    async def _fetch_aladhan(self, session, latitude, longitude, entity_id):
        """Prayer times for locations outside Malaysia via api.aladhan.com."""
        geo = await self._reverse_geocode(session, latitude, longitude) or {}
        place = geo.get("name")
        if place and geo.get("country_code"):
            place = f"{place}, {geo['country_code']}"
        base_attrs = {
            "gps": f"{latitude},{longitude}",
            "flag": FLAG_OUTSIDE,
            "region": geo.get("state"),
            "country": geo.get("country"),
        }

        params = {"latitude": latitude, "longitude": longitude}
        method = self.config_entry.options.get(CONF_ALADHAN_METHOD, self.config_entry.data.get(CONF_ALADHAN_METHOD)) if self.config_entry else None
        if method is not None and str(method) in ALADHAN_METHODS and str(method) != "auto":
            params["method"] = str(method)  # otherwise Aladhan picks the nearest authority

        # Same ~1 km cell and method on the same local day: reuse the last answer
        cache_key = (round(float(latitude), 2), round(float(longitude), 2), params.get("method"))
        cached = self._aladhan_cache.get(cache_key)
        try:
            if cached and datetime.now(ZoneInfo(cached[1]["meta"]["timezone"])).strftime("%d-%m-%Y") == cached[0]:
                data = cached[1]
                self._aladhan_used.add(cache_key)
                tz_name = data["meta"]["timezone"]
                tz = ZoneInfo(tz_name)
            else:
                # Ask for "today" in UTC first, then re-ask with the location's local date
                today_utc = datetime.now(ZoneInfo("UTC")).strftime("%d-%m-%Y")
                data = await self._aladhan_get(session, today_utc, params)
                tz_name = data["meta"]["timezone"]
                tz = ZoneInfo(tz_name)
                local_today = datetime.now(tz).strftime("%d-%m-%Y")
                if local_today != today_utc:
                    data = await self._aladhan_get(session, local_today, params)
                if len(self._aladhan_cache) > 64:
                    self._aladhan_cache.clear()
                self._aladhan_cache[cache_key] = (local_today, data, datetime.now(ZoneInfo("UTC")))
                self._aladhan_used.add(cache_key)
        except Exception as e:  # noqa: BLE001
            _LOGGER.error("Aladhan fallback failed for %s: %s", entity_id, e)
            return {"state": place or "Outside Malaysia", "attributes": {**base_attrs, "error": str(e)}}

        timings = data["timings"]
        g = data["date"]["gregorian"]
        day = datetime(int(g["year"]), int(g["month"]["number"]), int(g["day"]), tzinfo=tz)

        def at(hhmm):
            hh, mm = hhmm.split(" ")[0].split(":")[:2]
            return day.replace(hour=int(hh), minute=int(mm))

        local = {
            "imsak": at(timings["Imsak"]),
            "subuh": at(timings["Fajr"]),
            "syuruk": at(timings["Sunrise"]),
            "zohor": at(timings["Dhuhr"]),
            "asar": at(timings["Asr"]),
            "maghrib": at(timings["Maghrib"]),
            "isyak": at(timings["Isha"]),
        }
        local["isyraq"] = local["syuruk"] + timedelta(minutes=ISYRAQ_OFFSET_MINUTES)
        local["dhuha"] = local["syuruk"] + timedelta(minutes=DHUHA_OFFSET_MINUTES)

        prayer_times = {}
        for key, dt in local.items():
            prayer_times[key] = dt.astimezone(ZoneInfo("UTC")).isoformat()
            prayer_times[f"{key}_12h"] = dt.strftime("%-I:%M %p")
            prayer_times[f"{key}_24h"] = dt.strftime("%H:%M:%S")

        method_meta = data.get("meta", {}).get("method", {})
        return {
            "state": place or tz_name,
            "attributes": {
                **base_attrs,
                "provider": "Aladhan",
                "method": method_meta.get("name"),
                "timezone": tz_name,
                **prayer_times,
            },
        }

    @staticmethod
    async def _aladhan_get(session, date_str, params):
        async with session.get(
            f"{ALADHAN_URL}/{date_str}", params=params, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            resp.raise_for_status()
            payload = await resp.json()
            if payload.get("code") != 200:
                raise ValueError(f"Aladhan returned {payload.get('code')}: {payload.get('status')}")
            return payload["data"]

    @staticmethod
    def convert_to_local_12time(time):
        dt = datetime.fromtimestamp(time, ZoneInfo("Asia/Kuala_Lumpur"))
        return dt.strftime("%-I:%M %p")

    @staticmethod
    def convert_to_local_24time(time):
        dt = datetime.fromtimestamp(time, ZoneInfo("Asia/Kuala_Lumpur"))
        return dt.strftime("%H:%M:%S")



class _HttpError(Exception):
    """Non-200 from waktusolat.app."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body = body
