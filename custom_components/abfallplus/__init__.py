"""The Abfallplus integration."""

from datetime import timedelta
import logging

from babel import dates

from homeassistant.config_entries import ConfigEntry, ConfigEntryError
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .abfallplus_app_lib import AbfallplusApp
from .const import DOMAIN, ENTRY_COORDINATOR

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMA Sunny Beam from a config entry."""

    abfallplus = AbfallplusApp(entry.data)
    try:
        await abfallplus.get_pickup_times()
    except BaseException as err:
        raise ConfigEntryError("Could not connect to Abfallplus") from err

    async def async_update_data():
        """Fetch data from API endpoint."""
        try:
            data = await abfallplus.get_pickup_times()
        except BaseException as error:
            raise UpdateFailed("Could not fetch data from Sunny Beam") from error
        _LOGGER.debug("Data fetched from Sunny Beam: %s", data)

        # Format dates
        data_formatted = {}
        for key, value in data.items():
            dates_formaated = []
            for date_unformated in value:
                formated = await hass.async_add_executor_job(
                    lambda d=date_unformated: dates.format_datetime(
                        d, "EEE d. MMM", locale="de_DE"
                    )
                )
                dates_formaated.append(formated)
            data_formatted[key] = dates_formaated
        return data_formatted

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=ENTRY_COORDINATOR,
        update_method=async_update_data,
        update_interval=timedelta(hours=1),
    )

    await coordinator.async_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {ENTRY_COORDINATOR: coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
