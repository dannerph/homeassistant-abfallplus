"""Abfallplus sensor platform."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, ENTRY_COORDINATOR


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry created in the integrations UI."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry[ENTRY_COORDINATOR]

    # coordinator = entry[ENTRY_COORDINATOR]
    device_info = DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, "abfallplus")},
        manufacturer="Abfallplus",
        name="Abfallplus",
    )
    async_add_entities(
        [
            WasteSensor(
                coordinator,
                device_info,
                SensorEntityDescription(
                    key=waster_type["name"],
                    name=waster_type["name"],
                    icon="mdi:trash-can",
                ),
            )
            for waster_type in config_entry.data["abfallarten"]
        ]
    )


class WasteSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Abfallsplus sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_info: DeviceInfo,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, context=description.key)
        self._attr_device_info = device_info
        self.entity_description = description
        self._attr_unique_id = description.key

        #  Set initial data
        self._attr_native_value = self.coordinator.data[self.entity_description.key][0]
        self._attributes = {
            "übernächstes Mal": self.coordinator.data[self.entity_description.key][1]
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        if (
            self.coordinator.data is not None
            and len(self.coordinator.data[self.entity_description.key]) >= 2
        ):
            self._attr_native_value = self.coordinator.data[
                self.entity_description.key
            ][0]
            self._attributes = {
                "übernächstes Mal": self.coordinator.data[self.entity_description.key][
                    1
                ]
            }
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the binary sensor."""
        return self._attributes
