"""
EsolatGPS Integration for Home Assistant
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.core import callback
from .coordinator import EsolatGPSConfigEntry, EsolatGPSCoordinator
from .entity import EsolatGPSEntity

_LOGGER = logging.getLogger(__name__)

# Coordinator-based: the coordinator does all fetching, so no limit is needed
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: EsolatGPSConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the EsolatGPS sensors from a config entry."""
    coordinator = entry.runtime_data

    async_add_entities([
        EsolatGPSSensor(coordinator, "zone.home", is_home=True),
        EsolatNowSensor(coordinator),
    ])

    # Everything else follows the coordinator after every update:
    #  * a prayer sensor per person with GPS (sensor.esolat_<person>), added when GPS appears
    #    and removed when it goes, including people who lost GPS while HA was down;
    #  * a diagnostic sensor per JAKIM zone in use (sensor.esolat_sgr01) and one for Aladhan.
    # Removal goes through the entity registry by unique_id, so renamed entities are caught too.
    added: set[str] = set()  # unique_ids this platform created during this run

    @callback
    def _sync() -> None:
        if not coordinator.last_update_success or not coordinator.data:
            return  # never remove anything on the strength of a failed update

        people = {e for e in coordinator.data if e.startswith("person.")}
        sources = set(coordinator.diag["zones"])
        if coordinator.diag.get("aladhan"):
            sources.add(ALADHAN_KEY)
        wanted = {f"esolat_{p.split('.', 1)[1]}" for p in people} | {
            f"{DIAG_PREFIX}{k.lower()}" for k in sources
        }

        new = []
        for person in sorted(people):
            uid = f"esolat_{person.split('.', 1)[1]}"
            if uid not in added:
                new.append(EsolatGPSSensor(coordinator, person))
                added.add(uid)
        for key in sorted(sources):
            uid = f"{DIAG_PREFIX}{key.lower()}"
            if uid not in added:
                new.append(EsolatSourceSensor(coordinator, key))
                added.add(uid)
        if new:
            async_add_entities(new)

        ent_reg = er.async_get(hass)
        for reg in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            uid = reg.unique_id
            if uid in FIXED_UNIQUE_IDS or uid in wanted or not uid.startswith("esolat_"):
                continue
            _LOGGER.info("Removing %s: no longer tracked", reg.entity_id)
            ent_reg.async_remove(reg.entity_id)
            added.discard(uid)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


FIXED_UNIQUE_IDS = {"esolat_home", "esolatnow"}
DIAG_PREFIX = "esolat_source_"
ALADHAN_KEY = "ALADHAN"


class EsolatGPSSensor(EsolatGPSEntity, SensorEntity):
    """Prayer times for one person, or for the Home zone."""

    def __init__(self, coordinator: EsolatGPSCoordinator, entity_id: str, is_home: bool = False) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._is_home = is_home

        entity_name = entity_id.split('.')[1]

        # Kept from earlier versions so existing entities, history and dashboards carry over
        self._attr_unique_id = f"esolat_{entity_name}"
        self.entity_id = f"sensor.esolat_{entity_name}"

        if is_home:
            self._attr_translation_key = "home"
        else:
            self._attr_translation_key = "person"
            person = coordinator.hass.states.get(entity_id)
            self._attr_translation_placeholders = {
                "person": person.attributes.get("friendly_name", entity_name) if person else entity_name
            }

    @property
    def _data(self) -> dict:
        return (self.coordinator.data or {}).get(self._entity_id) or {}

    @property
    def available(self) -> bool:
        """Unavailable when the last update failed or this location could not be resolved."""
        return super().available and self._data.get("state") not in (None, "unavailable")

    @property
    def native_value(self):
        """Place name, e.g. 'Saujana Impian, Hulu Langat'."""
        return self._data.get("state")

    @property
    def extra_state_attributes(self):
        """Return the state attributes, including the source of GPS data."""
        attributes = self._data.get("attributes", {}).copy()
        attributes["source"] = self._entity_id
        return attributes

class EsolatNowSensor(EsolatGPSEntity, SensorEntity):
    """Current and next prayer for every tracked location, plus today's Hijri date."""

    _attr_translation_key = "current"

    def __init__(self, coordinator: EsolatGPSCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = "esolatnow"
        self.entity_id = "sensor.esolatnow"

    def get_current_prayer_info(self, entity_data):
        """Get current prayer information based on time."""
        now = datetime.now(ZoneInfo("UTC"))
        prayer_times = {
            "imsak":   ("Imsak",   "Subuh"),
            "subuh":   ("Subuh",   "Syuruk"),
            "syuruk":  ("Syuruk",  "Isyraq"),
            "isyraq":  ("Isyraq",  "Dhuha"),
            "dhuha":   ("Dhuha",   "Zohor"),
            "zohor":   ("Zohor",   "Asar"),
            "asar":    ("Asar",    "Maghrib"),
            "maghrib": ("Maghrib", "Isyak"),
            "isyak":   ("Isyak",   "Imsak"),
        }

        attributes = entity_data.get("attributes", {})
        isyak_time = None
        imsak_time = None

        for current_prayer, (current_name, next_name) in prayer_times.items():
            current_time_str = attributes.get(current_prayer, "")
            next_prayer_key = next_name.lower()

            if not current_time_str or not attributes.get(next_prayer_key, ""):
                continue

            current_time = datetime.fromisoformat(current_time_str)

            # Handle Isyak to Imsak transition (crosses midnight)
            if next_prayer_key == "imsak":
                imsak_time = datetime.fromisoformat(attributes.get(next_prayer_key, ""))
                next_time = imsak_time + timedelta(days=1)
                isyak_time = current_time
            else:
                next_time = datetime.fromisoformat(attributes.get(next_prayer_key, ""))

            if current_time <= now < next_time:
                return {
                    "current": current_name,
                    "next": next_name,
                    "datetime": attributes.get(current_prayer),
                    "location": entity_data.get("state"),
                    **self._countdown(next_time, now),
                }

        # Fallback: after midnight but before today's Imsak
        # (now has passed all stored prayer times but Imsak hasn't arrived yet)
        if imsak_time is not None and isyak_time is not None and now < imsak_time:
            return {
                "current": "Isyak",
                "next": "Imsak",
                "datetime": attributes.get("isyak"),
                "location": entity_data.get("state"),
                **self._countdown(imsak_time, now),
            }

        return None

    @staticmethod
    def _countdown(next_time, now):
        """Countdown attributes to the next prayer."""
        total_seconds = max(int((next_time - now).total_seconds()), 0)
        minutes = total_seconds // 60
        hours, mins = divmod(minutes, 60)
        parts = []
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        parts.append(f"{mins} minute{'s' if mins != 1 else ''}")
        return {
            "next_datetime": next_time.isoformat(),
            "time_minutes": minutes,
            "time_remaining": ", ".join(parts),
        }

    async def async_added_to_hass(self):
        """Re-render every minute so the countdown stays current between API polls."""
        await super().async_added_to_hass()

        @callback
        def _tick(_now):
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_time_interval(self.hass, _tick, timedelta(minutes=1))
        )

    def _current(self) -> dict:
        """Current/next prayer per location, keyed by person (or 'home')."""
        current = {}
        for entity_id, entity_data in (self.coordinator.data or {}).items():
            if entity_data.get("attributes", {}).get("subuh"):
                prayer_info = self.get_current_prayer_info(entity_data)
                if prayer_info:
                    current[entity_id.split('.')[1]] = prayer_info
        return current

    @property
    def native_value(self):
        """Number of locations with a current prayer."""
        return len(self._current())

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "hijri": self.coordinator.hijri or "unavailable",
            "array": self._current(),
        }



class EsolatSourceSensor(EsolatGPSEntity, SensorEntity):
    """Diagnostic: when a JAKIM zone's timetable (or Aladhan) was last fetched, and who uses it."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: EsolatGPSCoordinator, key: str) -> None:
        """key is a JAKIM code such as "SGR01", or ALADHAN_KEY."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{DIAG_PREFIX}{key.lower()}"
        self.entity_id = f"sensor.esolat_{key.lower()}"
        if key == ALADHAN_KEY:
            self._attr_translation_key = "aladhan"
        else:
            self._attr_translation_key = "jakim_zone"
            self._attr_translation_placeholders = {"zone": key}

    @property
    def _info(self) -> dict | None:
        diag = self.coordinator.diag
        return diag.get("aladhan") if self._key == ALADHAN_KEY else diag["zones"].get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self._info is not None

    @property
    def native_value(self):
        return (self._info or {}).get("fetched")

    @property
    def extra_state_attributes(self):
        return {k: v for k, v in (self._info or {}).items() if k != "fetched"}
