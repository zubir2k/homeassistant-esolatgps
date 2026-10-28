"""
Constants for the EsolatGPS integration.
"""
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

DOMAIN = "esolatgps"

# Default scan interval in minutes
DEFAULT_SCAN_INTERVAL = 15

# Minimum scan interval in minutes (5 minutes)
MIN_SCAN_INTERVAL = 5

# Maximum scan interval in minutes (60 minutes = 1 hour)
MAX_SCAN_INTERVAL = 60

# Prayer names
PRAYER_NAMES = ["Subuh", "Syuruk", "Zohor", "Asar", "Maghrib", "Isyak"]

# Malaysia provider: JAKIM times via waktusolat.app, one month per zone.
# The GPS -> zone step is done offline from data/jakim_zones.json (see zones.py).
WAKTUSOLAT_ZONE_URL = "https://api.waktusolat.app/v2/solat/{zone}"
# Only used by the config flow to check the provider is reachable
WAKTUSOLAT_ZONES_URL = "https://api.waktusolat.app/zones"

# waktusolat.app field -> sensor attribute key
WAKTUSOLAT_FIELDS = {
    "imsak": "imsak",
    "fajr": "subuh",
    "syuruk": "syuruk",
    "dhuha": "dhuha",
    "dhuhr": "zohor",
    "asr": "asar",
    "maghrib": "maghrib",
    "isha": "isyak",
}

# Derived times, minutes after Syuruk
ISYRAQ_OFFSET_MINUTES = 12  # not published by JAKIM; calculated
DHUHA_OFFSET_MINUTES = 25   # JAKIM's Dhuha; used for Aladhan and if the API omits it

# Fallback provider for locations outside Malaysia
ALADHAN_URL = "https://api.aladhan.com/v1/timings"
# Optional config key: Aladhan calculation method id, or "auto" for nearest authority
CONF_ALADHAN_METHOD = "aladhan_method"
# Aladhan method ids offered in the options flow (labels live in translations)
# Method 17 (JAKIM) is left out on purpose: inside Malaysia times always come from JAKIM via
# waktusolat.app, so the Aladhan method only ever applies outside Malaysia.
ALADHAN_METHODS = ["auto", "0", "1", "2", "3", "4", "5", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "18", "19", "20", "21", "22", "23"]
# Nominatim requires an identifying User-Agent
NOMINATIM_UA = "homeassistant-esolatgps (+https://github.com/zubir2k/homeassistant-esolatgps)"

# "flag" attribute on every prayer time sensor
FLAG_LOCAL = "local"
FLAG_OUTSIDE = "outside_malaysia"


def get_device_info(entry_id: str) -> DeviceInfo:
    """Shared service device for all eSolat GPS entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="eSolat GPS",
        manufacturer="JAKIM (waktusolat.app) / Aladhan",
        model="Prayer Times Service",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://github.com/zubir2k/homeassistant-esolatgps",
    )
