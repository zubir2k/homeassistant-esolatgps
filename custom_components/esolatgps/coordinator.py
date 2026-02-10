import logging
from datetime import datetime, timedelta
import async_timeout
import aiohttp

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class EsolatCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Prayer Time data from MPT and Aladhan APIs."""

    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession, update_interval: int):
        self.session = session
        super().__init__(
            hass,
            _LOGGER,
            name="eSolat GPS Coordinator",
            update_interval=timedelta(minutes=update_interval),
        )

    async def _async_update_data(self):
        """Fetch data from API based on current GPS location."""
        lat = self.hass.config.latitude
        lng = self.hass.config.longitude

        # 1. Primary: MPT (Malaysia) API
        # We try this first as it provides official JAKIM data.
        url_mpt = f"https://mpt.i906.my/api/prayer/{lat},{lng}"
        
        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(url_mpt)
                
                if response.status == 200:
                    raw_data = await response.json()
                    # Basic structure validation
                    if "data" in raw_data and "times" in raw_data["data"]:
                        return self._parse_mpt(raw_data)
                    raise ValueError("Unexpected MPT data structure")
                
                # 404 means coordinate is outside Malaysia. Switch to Aladhan.
                if response.status == 404:
                    _LOGGER.info("Coordinate outside Malaysia (404). Switching to Aladhan API.")
                    return await self._fetch_aladhan(lat, lng)
                
                # Other status codes (500, etc.) trigger fallback
                _LOGGER.warning("MPT API returned status %s. Trying Aladhan fallback.", response.status)
                return await self._fetch_aladhan(lat, lng)

        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.warning("MPT API network error: %s. Trying Aladhan fallback.", err)
            return await self._fetch_aladhan(lat, lng)
        except Exception as err:
            _LOGGER.error("Unexpected error in MPT fetch: %s", err)
            return await self._fetch_aladhan(lat, lng)

    async def _fetch_aladhan(self, lat, lng):
        """Helper to fetch from Aladhan Global API."""
        # Method 3: Muslim World League
        url_aladhan = f"https://api.aladhan.com/v1/timings?latitude={lat}&longitude={lng}&method=3"
        
        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(url_aladhan)
                if response.status == 200:
                    raw_data = await response.json()
                    if "data" in raw_data and "timings" in raw_data["data"]:
                        return self._parse_aladhan(raw_data)
                    raise ValueError("Unexpected Aladhan data structure")
                
                raise UpdateFailed(f"Aladhan API failed with status {response.status}")
        
        except Exception as err:
            # If we are here, BOTH APIs have failed.
            _LOGGER.error("Aladhan API error: %s", err)
            raise UpdateFailed(f"Could not fetch prayer times from any provider: {err}")

    def _format_time_formats(self, time_str):
        """Standardizes time strings to 12h and 24h formats."""
        try:
            dt = datetime.strptime(time_str, "%H:%M")
            return {
                "24h": dt.strftime("%H:%M:%S"),
                "12h": dt.strftime("%I:%M %p").lstrip("0")
            }
        except Exception:
            return {"24h": time_str, "12h": time_str}

    def _parse_mpt(self, data):
        """Parse the Unix timestamp array from MPT."""
        try:
            today = data['data']['times'][0]
            keys = ["fajr", "syuruk", "dhuhr", "asr", "maghrib", "isha"]
            result = {
                "location": data['data'].get('place', 'Unknown'), 
                "source": "JAKIM (MPT)"
            }
            
            for i, key in enumerate(keys):
                t_str = datetime.fromtimestamp(today[i]).strftime("%H:%M")
                formats = self._format_time_formats(t_str)
                result[key] = t_str
                result[f"{key}_12h"] = formats["12h"]
                result[f"{key}_24h"] = formats["24h"]
            return result
        except Exception as err:
            _LOGGER.error("MPT Parse Error: %s", err)
            raise UpdateFailed("Failed to parse MPT data")

    def _parse_aladhan(self, data):
        """Parse the 24h string dictionary from Aladhan."""
        try:
            t = data['data']['timings']
            meta = data['data']['meta']
            keys = {
                "Fajr": "fajr", "Sunrise": "syuruk", "Dhuhr": "dhuhr", 
                "Asr": "asr", "Maghrib": "maghrib", "Isha": "isha"
            }
            result = {
                "location": meta.get('timezone', 'Unknown'), 
                "source": f"Aladhan ({meta['method'].get('name', 'MWL')})"
            }
            
            for api_key, internal_key in keys.items():
                t_str = t[api_key]
                formats = self._format_time_formats(t_str)
                result[internal_key] = t_str
                result[f"{internal_key}_12h"] = formats["12h"]
                result[f"{internal_key}_24h"] = formats["24h"]
            return result
        except Exception as err:
            _LOGGER.error("Aladhan Parse Error: %s", err)
            raise UpdateFailed("Failed to parse Aladhan data")
