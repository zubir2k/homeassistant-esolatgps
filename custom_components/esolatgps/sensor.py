"""
EsolatGPS Integration for Home Assistant
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from .const import DOMAIN
from .coordinator import EsolatGPSCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the EsolatGPS sensors from a config entry."""
    coordinator = EsolatGPSCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    sensors = []
    for person_entity in hass.states.async_entity_ids("person"):
        if (hass.states.get(person_entity).attributes.get("latitude") is not None
            and hass.states.get(person_entity).attributes.get("longitude") is not None):
            sensors.append(EsolatGPSSensor(coordinator, person_entity))

    sensors.append(EsolatGPSSensor(coordinator, "zone.home", is_home=True))
    sensors.append(EsolatNowSensor(coordinator, hass))

    async_add_entities(sensors)

class EsolatGPSSensor(CoordinatorEntity, SensorEntity):
    """Representation of an EsolatGPS Sensor."""

    def __init__(self, coordinator, entity_id, is_home=False):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._is_home = is_home
        
        entity_name = entity_id.split('.')[1]
        
        self._attr_unique_id = f"esolat_{entity_name}"
        self.entity_id = f"sensor.esolat_{entity_name}"
        
        self._attr_icon = "mdi:home-clock" if is_home else "mdi:account-clock"

    @property
    def name(self):
        """Return the name of the sensor."""
        if self._is_home:
            return "Home Prayer Time"
        entity = self.hass.states.get(self._entity_id)
        if entity:
            return f"{entity.attributes.get('friendly_name', 'Unknown')} Prayer Time"
        return "Unknown Prayer Time"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._entity_id, {}).get("state", "unavailable")

    @property
    def extra_state_attributes(self):
        """Return the state attributes, including the source of GPS data."""
        attributes = self.coordinator.data.get(self._entity_id, {}).get("attributes", {}).copy()
        attributes["source"] = self._entity_id
        return attributes

class EsolatNowSensor(CoordinatorEntity, SensorEntity):
    """Representation of an eSolatNow Sensor that shows current prayer times."""

    def __init__(self, coordinator, hass):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.hass = hass
        self._attr_unique_id = "esolatnow"
        self.entity_id = "sensor.esolatnow"
        self._attr_icon = "mdi:calendar-clock"
        self._hijri_date = None
        self._last_hijri_update = None

    async def async_get_hijri_date(self):
        """Get Hijri date from API."""
        # Update only once per day
        now = datetime.now()
        if self._last_hijri_update and self._last_hijri_update.date() == now.date() and self._hijri_date:
            return self._hijri_date

        self._hijri_date = await self.coordinator.fetch_hijri_date()
        self._last_hijri_update = now
        return self._hijri_date

    def get_current_prayer_info(self, entity_data):
        """Get current prayer information based on time."""
        now = datetime.now(ZoneInfo("UTC"))
        prayer_times = {
            "imsak": ("Imsak", "Subuh"),
            "subuh": ("Subuh", "Syuruk"),
            "syuruk": ("Syuruk", "Isyraq"),
            "isyraq": ("Isyraq", "Dhuha"),
            "dhuha": ("Dhuha", "Zohor"),
            "zohor": ("Zohor", "Asar"),
            "asar": ("Asar", "Maghrib"),
            "maghrib": ("Maghrib", "Isyak"),
            "isyak": ("Isyak", "Imsak")
        }

        attributes = entity_data.get("attributes", {})
        for current_prayer, (current_name, next_name) in prayer_times.items():
            current_time = datetime.fromisoformat(attributes.get(current_prayer, ""))
            next_prayer = next_name.lower()
            
            # Handle Isyak to Imsak transition
            if next_prayer == "imsak":
                next_time = datetime.fromisoformat(attributes.get(next_prayer, "")) + timedelta(days=1)
            else:
                next_time = datetime.fromisoformat(attributes.get(next_prayer, ""))

            if current_time <= now < next_time:
                return {
                    "current": current_name,
                    "next": next_name,
                    "datetime": attributes.get(current_prayer),
                    "location": entity_data.get("state")
                }

        return None

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Current Prayer Time"

    @property
    def state(self):
        """Return the number of prayer time sensors."""
        return len(self.extra_state_attributes["array"])

    async def async_update(self):
        """Update the sensor."""
        await super().async_update()
        # Ensure the Hijri date is updated daily
        await self.async_get_hijri_date()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attributes = {
            "hijri": self._hijri_date or "unavailable",
            "array": {}
        }

        # Update Hijri date when accessing attributes
        self.hass.async_create_task(self.async_get_hijri_date())

        for entity_id, entity_data in self.coordinator.data.items():
            if entity_data.get("state") != "Outside Malaysia":
                prayer_info = self.get_current_prayer_info(entity_data)
                if prayer_info:
                    entity_name = entity_id.split('.')[1]
                    attributes["array"][entity_name] = prayer_info

        return attributes
