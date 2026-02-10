from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup sensors using the coordinator."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    prayer_map = {
        "fajr": "Subuh", "syuruk": "Syuruk", "dhuhr": "Zohor",
        "asr": "Asar", "maghrib": "Maghrib", "isha": "Isyak"
    }

    async_add_entities([
        EsolatPrayerSensor(coordinator, key, name) 
        for key, name in prayer_map.items()
    ])

class EsolatPrayerSensor(CoordinatorEntity, SensorEntity):
    """Sensor that maintains all original attributes."""

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"eSolat GPS {name}"
        self._attr_unique_id = f"esolat_gps_{key}_{coordinator.config_entry.entry_id}"
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self):
        """Current prayer time string."""
        return self.coordinator.data.get(self._key)

    @property
    def extra_state_attributes(self):
        """Attributes for 12h, 24h, UTC, and Location."""
        return {
            f"{self._key}_12h": self.coordinator.data.get(f"{self._key}_12h"),
            f"{self._key}_24h": self.coordinator.data.get(f"{self._key}_24h"),
            "datetime_utc": self.coordinator.data.get(f"{self._key}_utc"),
            "location_name": self.coordinator.data.get("location"),
            "api_source": self.coordinator.data.get("source"),
        }
