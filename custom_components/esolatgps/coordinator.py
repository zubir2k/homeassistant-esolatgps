import logging
from datetime import datetime, timedelta
import async_timeout
import aiohttp

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class EsolatCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Prayer Time data."""

    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession, update_interval: int):
        self.session = session
        super().__init__(
            hass,
            _LOGGER,
            name="eSolat GPS Coordinator",
            update_interval=timedelta(minutes=update_interval),
        )

    async def _async_update_data(self):
        """Fetch data from MPT (MY) or Aladhan (Global)."""
        lat = self.hass.config.latitude
        lng = self.hass.config.longitude

        # 1. Try Malaysia Prayer Time (MPT) API
        url_mpt = f"https://mpt.i906.my/api/prayer/{lat},{lng}"
        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(url_mpt)
                if response.status == 200:
                    data = await response.json()
                    return self._parse_mpt(data)
                
                # If 404, we are definitely outside Malaysia
                if response.status == 404:
                    _LOGGER.info("Location outside Malaysia. Switching to Aladhan.")
                    return await self._fetch_aladhan(lat, lng)
        except Exception as err:
            _LOGGER.debug("MPT API failed: %s. Falling back to Aladhan.", err)
            return await self._fetch_aladhan(lat, lng)

    async def _fetch_aladhan(self, lat, lng):
        """Fetch from Aladhan using MWL calculation method."""
        url = f"https://api.aladhan.com/v1/timings?latitude={lat}&longitude={lng}&method=3"
        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(url)
                if response.status == 200:
                    return self._parse_aladhan(await response.json())
        except Exception as err:
            raise UpdateFailed(f"Failed to fetch prayer data: {err}")

    def _format_all(self, time_str):
        """Helper to create all formats expected by original sensor.py."""
        now = datetime.now()
        dt_local = datetime.strptime(f"{now.date()} {time_str}", "%Y-%m-%d %H:%M")
        return {
            "24h": dt_local.strftime("%H:%M:%S"),
            "12h": dt_local.strftime("%I:%M %p").lstrip("0"),
            "utc": dt_local.astimezone().isoformat()
        }

    def _parse_mpt(self, data):
        """Parse MPT Unix timestamp format."""
        today = data['data']['times'][0]
        keys = ["fajr", "syuruk", "dhuhr", "asr", "maghrib", "isha"]
        res = {"location": data['data'].get('place', 'Malaysia'), "source": "JAKIM (MPT)"}
        for i, k in enumerate(keys):
            t_str = datetime.fromtimestamp(today[i]).strftime("%H:%M")
            fmt = self._format_all(t_str)
            res.update({k: t_str, f"{k}_12h": fmt["12h"], f"{k}_24h": fmt["24h"], f"{k}_utc": fmt["utc"]})
        return res

    def _parse_aladhan(self, data):
        """Parse Aladhan string format."""
        t = data['data']['timings']
        map_keys = {"Fajr": "fajr", "Sunrise": "syuruk", "Dhuhr": "dhuhr", "Asr": "asr", "Maghrib": "maghrib", "Isha": "isha"}
        res = {"location": data['data']['meta'].get('timezone'), "source": "Aladhan"}
        for api_k, internal_k in map_keys.items():
            t_str = t[api_k]
            fmt = self._format_all(t_str)
            res.update({internal_k: t_str, f"{internal_k}_12h": fmt["12h"], f"{internal_k}_24h": fmt["24h"], f"{internal_k}_utc": fmt["utc"]})
        return res
