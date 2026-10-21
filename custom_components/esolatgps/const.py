"""
Constants for the EsolatGPS integration.
"""
from homeassistant.const import CONF_SCAN_INTERVAL

DOMAIN = "esolatgps"

# Default scan interval in minutes
DEFAULT_SCAN_INTERVAL = 15

# Minimum scan interval in minutes (5 minutes)
MIN_SCAN_INTERVAL = 5

# Maximum scan interval in minutes (60 minutes = 1 hour)
MAX_SCAN_INTERVAL = 60

# Prayer names
PRAYER_NAMES = ["Subuh", "Syuruk", "Zohor", "Asar", "Maghrib", "Isyak"]

# Fallback provider for locations outside Malaysia
ALADHAN_URL = "https://api.aladhan.com/v1/timings"
# Optional config key: Aladhan calculation method id, or "auto" for nearest authority
CONF_ALADHAN_METHOD = "aladhan_method"
# Nominatim requires an identifying User-Agent
NOMINATIM_UA = "homeassistant-esolatgps (+https://github.com/zubir2k/homeassistant-esolatgps)"

# "flag" attribute on every prayer time sensor
FLAG_LOCAL = "local"
FLAG_OUTSIDE = "outside_malaysia"
