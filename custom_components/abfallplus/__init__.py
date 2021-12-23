"""The Abfallplus integration."""
import logging
import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_utc_time_change

from .const import DOMAIN

from .abfallplus_app_lib import AbfallplusApp

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Abfallplus from a config entry."""

    # Create and store handler
    abfallplus = AbfllaplusAppHandler(hass, AbfallplusApp(entry.data))
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = abfallplus

    # Register force update service
    hass.services.async_register(DOMAIN, "update_sensors", abfallplus.update_sensors)

    # Setup sensors
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    # Start periodic updates
    abfallplus.start_periodic_request()

    # Initial request
    await abfallplus.update_sensors()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class AbfllaplusAppHandler:
    def __init__(self, hass, api):
        """Initialize charging station connection."""

        self._update_listeners = []
        self._hass = hass
        self.api = api
        self.device_name = "abfallplus"  # correct device name will be set in setup()
        self.device_id = "abfallplus_"  # correct device id will be set in setup()
        self.data = None

    def start_periodic_request(self):
        """Start periodic data polling."""

        now = datetime.datetime.now()
        async_track_utc_time_change(
            self._hass,
            self.update_sensors,
            hour=0,
            minute=now.minute,
            second=now.second,
            local=True,
        )

    async def update_sensors(self, *args):
        """Fetch new data and update listeners."""
        _LOGGER.debug("Update waste collection sensors")

        self.data = await self.api.get_pickup_times()

        # Inform entities about updated values
        for listener in self._update_listeners:
            listener()

        _LOGGER.debug("Notifying %d listeners", len(self._update_listeners))

    def add_update_listener(self, listener):
        """Add a listener for update notifications."""
        self._update_listeners.append(listener)

        # initial data is already loaded, thus update the component
        listener()

    async def async_fetch(self, param=None):
        """Set failsafe mode in async way."""
        await self.update_sensors()
