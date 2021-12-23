"""Abfallplus sensor platform."""
from homeassistant import config_entries, core
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)

from .const import DOMAIN


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    api_handler = hass.data[DOMAIN][config_entry.entry_id]
    sensors = []
    for waster_type in api_handler.api.config["abfallarten"]:
        sensors.append(
            WasteSensor(
                api_handler,
                SensorEntityDescription(
                    key=waster_type["name"], name=waster_type["name"]
                ),
            )
        )
    async_add_entities(sensors, update_before_add=True)


class WasteSensor(SensorEntity):
    """Representation of a Abfallsplus sensor."""

    _attr_should_poll = False

    def __init__(self, api_handler, description):
        super().__init__()
        self.api_handler = api_handler
        self.entity_description = description

        self._attr_name = description.name
        self._attr_unique_id = (
            self.api_handler.api.config["community"]["name"] + "_" + description.name
        )

        self._attributes: dict[str, str] = {}

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:trash-can"

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the binary sensor."""
        return self._attributes

    async def async_update(self):
        """Get latest cached states from the device."""

        if (
            self.api_handler.data is not None
            and len(self.api_handler.data[self._attr_name]) >= 2
        ):
            self._attr_native_value = str(self.api_handler.data[self._attr_name][0])
            self._attributes = {
                "übernächstes Mal": str(self.api_handler.data[self._attr_name][1])
            }

    def update_callback(self):
        """Schedule a state update."""
        self.async_schedule_update_ha_state(True)

    async def async_added_to_hass(self):
        """Add update callback after being added to hass."""
        self.api_handler.add_update_listener(self.update_callback)
