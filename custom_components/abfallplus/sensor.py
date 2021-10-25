"""GitHub sensor platform."""
import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries, core
from homeassistant.helpers.entity import Entity


from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    sensors = []
    for waster_type in config.api.config["abfallarten"]:
        sensors.append(WasteSensor(waster_type["name"], config))
    async_add_entities(sensors, update_before_add=True)


class WasteSensor(Entity):
    """Representation of a Abfallsplus sensor."""

    def __init__(self, name, api):
        super().__init__()
        self.api = api
        self.attrs = {}
        self._name = name
        self._state = None
        self._available = True

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.api.api.config["community"]["name"] + "_" + self.name

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:trash-can"

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.
        False if entity pushes its state to HA.
        """
        return False

    async def async_update(self):
        """Get latest cached states from the device."""

        if self.api.data is not None and len(self.api.data[self._name]) >= 2:
            self._state = str(self.api.data[self._name][0])
            self.attrs = {"übernächstes Mal": str(self.api.data[self._name][1])}

    def update_callback(self):
        """Schedule a state update."""
        self.async_schedule_update_ha_state(True)

    async def async_added_to_hass(self):
        """Add update callback after being added to hass."""
        self.api.add_update_listener(self.update_callback)
