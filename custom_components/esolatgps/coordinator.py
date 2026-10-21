import logging
import aiohttp
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry
from .const import PRAYER_NAMES, ALADHAN_URL, NOMINATIM_UA, CONF_ALADHAN_METHOD, FLAG_LOCAL, FLAG_OUTSIDE

_LOGGER = logging.getLogger(__name__)

class EsolatGPSCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the coordinator with the user-configured scan interval."""
        super().__init__(
            hass,
            _LOGGER,
            name="eSolat GPS",
            update_interval=timedelta(minutes=entry.data.get("scan_interval", 15)),
        )
        self.config_entry = entry
        self.url = "https://mpt.i906.my/api/prayer/"
        self.geo = "https://nominatim.openstreetmap.org/reverse?format=json&"
        self._tracked_entities = set()
        self._geo_cache = {}

    async def _async_update_data(self):
        """Fetch data from API."""
        async with aiohttp.ClientSession() as session:
            data = {}
            current_entities = set()

            for entity_id in self.hass.states.async_entity_ids("person"):
                entity = self.hass.states.get(entity_id)
                latitude = entity.attributes.get("latitude")
                longitude = entity.attributes.get("longitude")
                if latitude and longitude:
                    current_entities.add(entity_id)
                    data[entity_id] = await self._fetch_prayer_times(session, latitude, longitude, entity_id)
                else:
                    _LOGGER.info(f"Skipping {entity_id} as it lacks GPS coordinates.")

            # Home zone processing
            home = self.hass.states.get("zone.home")
            home_latitude = home.attributes.get("latitude")
            home_longitude = home.attributes.get("longitude")
            data["zone.home"] = await self._fetch_prayer_times(session, home_latitude, home_longitude, "zone.home")
            current_entities.add("zone.home")

            # Cleanup stale entities
            entities_to_remove = self._tracked_entities - current_entities
            self._tracked_entities = current_entities

            if entities_to_remove:
                self.hass.async_create_task(self._remove_stale_entities(entities_to_remove))

            return data

    async def fetch_hijri_date(self):
        """Fetch Hijri date from API."""
        url = "https://www.e-solat.gov.my/index.php"
        params = {
            "r": "esolatApi/tarikhtakwim",
            "period": "today",
            "datetype": "miladi"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
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

    async def _remove_stale_entities(self, entities_to_remove):
        """Remove entities that no longer have GPS coordinates."""
        ent_reg = entity_registry.async_get(self.hass)
        for entity_id in entities_to_remove:
            entity_name = entity_id.split('.')[1]
            sensor_id = f"sensor.esolat_{entity_name}"
            if ent_reg.async_get(sensor_id):  # Check if entity exists before removing
                _LOGGER.info(f"Removing stale entity {sensor_id} due to missing GPS coordinates")
                ent_reg.async_remove(sensor_id)

    async def _fetch_prayer_times(self, session, latitude, longitude, entity_id):
        """Fetch prayer times from the API and handle out-of-country cases."""
        today = datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).date()
        day_index = 0 if today.day == 1 else today.day - 1

        try:
            async with session.get(f"{self.url}{latitude},{longitude}") as response:
                if response.status == 404:
                    # Outside Malaysia (MPT/JAKIM has no zone here) -> fall back to Aladhan
                    return await self._fetch_aladhan(session, latitude, longitude, entity_id)
                elif response.status == 200:
                    data = await response.json()
                    prayer_times_data = data["data"]["times"][day_index]
                    prayer_times = {}

                    for i, prayer_name in enumerate(PRAYER_NAMES):
                        prayer_time = prayer_times_data[i]
                        utc_prayer_time = self.timestamp_to_utc(prayer_time).astimezone(ZoneInfo("UTC"))
                        prayer_times[prayer_name.lower()] = utc_prayer_time.isoformat()
                        prayer_times[f"{prayer_name.lower()}_12h"] = self.convert_to_local_12time(prayer_time)
                        prayer_times[f"{prayer_name.lower()}_24h"] = self.convert_to_local_24time(prayer_time)

                        # Additional times: Imsak, Isyraq, Dhuha
                        if prayer_name.lower() == "subuh":
                            imsak_time = utc_prayer_time - timedelta(minutes=10)
                            prayer_times["imsak"] = imsak_time.isoformat()
                            prayer_times["imsak_12h"] = self.convert_to_local_12time(imsak_time.timestamp())
                            prayer_times["imsak_24h"] = self.convert_to_local_24time(imsak_time.timestamp())

                        if prayer_name.lower() == "syuruk":
                            isyraq_time = utc_prayer_time + timedelta(minutes=12)
                            dhuha_time = utc_prayer_time + timedelta(minutes=15)
                            prayer_times["isyraq"] = isyraq_time.isoformat()
                            prayer_times["isyraq_12h"] = self.convert_to_local_12time(isyraq_time.timestamp())
                            prayer_times["isyraq_24h"] = self.convert_to_local_24time(isyraq_time.timestamp())
                            prayer_times["dhuha"] = dhuha_time.isoformat()
                            prayer_times["dhuha_12h"] = self.convert_to_local_12time(dhuha_time.timestamp())
                            prayer_times["dhuha_24h"] = self.convert_to_local_24time(dhuha_time.timestamp())

                    zone_place = data["data"]["place"]
                    geo = await self._reverse_geocode(session, latitude, longitude) or {}
                    return {
                        "state": geo.get("name") or zone_place,
                        "attributes": {
                            "gps": f"{latitude},{longitude}",
                            "flag": FLAG_LOCAL,
                            "zone": zone_place,
                            "region": geo.get("state"),
                            "country": geo.get("country") or "Malaysia",
                            "provider": "JAKIM (MPT)",
                            "timezone": "Asia/Kuala_Lumpur",
                            **prayer_times,
                        }
                    }
                else:
                    _LOGGER.error(f"Error retrieving prayer times for {entity_id}: Status {response.status}")
                    return {
                        "state": "unavailable",
                        "attributes": {
                            "location": f"ERROR CODE:{response.status}",
                            "gps": f"{latitude},{longitude}"
                        }
                    }
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Client error retrieving prayer times for {entity_id}: {e}")
            return {
                "state": "unavailable",
                "attributes": {
                    "location": "Client error",
                    "gps": f"{latitude},{longitude}"
                }
            }
        except Exception as e:
            _LOGGER.error(f"Unexpected error retrieving prayer times for {entity_id}: {e}")
            return {
                "state": "unavailable",
                "attributes": {
                    "location": "Unexpected error",
                    "gps": f"{latitude},{longitude}"
                }
            }


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
        if method not in (None, "", "auto"):
            params["method"] = method  # otherwise Aladhan picks the nearest authority

        # Ask for "today" in UTC first, then re-ask with the location's local date
        try:
            today_utc = datetime.now(ZoneInfo("UTC")).strftime("%d-%m-%Y")
            data = await self._aladhan_get(session, today_utc, params)
            tz_name = data["meta"]["timezone"]
            tz = ZoneInfo(tz_name)
            local_today = datetime.now(tz).strftime("%d-%m-%Y")
            if local_today != today_utc:
                data = await self._aladhan_get(session, local_today, params)
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
        local["isyraq"] = local["syuruk"] + timedelta(minutes=12)
        local["dhuha"] = local["syuruk"] + timedelta(minutes=15)

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
    def timestamp_to_utc(timestamp):
        return datetime.fromtimestamp(timestamp, ZoneInfo("UTC"))

    @staticmethod
    def convert_to_local_12time(time):
        dt = datetime.fromtimestamp(time, ZoneInfo("Asia/Kuala_Lumpur"))
        return dt.strftime("%-I:%M %p")

    @staticmethod
    def convert_to_local_24time(time):
        dt = datetime.fromtimestamp(time, ZoneInfo("Asia/Kuala_Lumpur"))
        return dt.strftime("%H:%M:%S")

