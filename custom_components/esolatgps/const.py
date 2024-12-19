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
