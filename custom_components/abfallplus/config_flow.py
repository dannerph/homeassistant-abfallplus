"""Config flow for Abfallplus integration."""
import voluptuous as vol

from typing import Any, Dict, Optional
from .abfallplus_app_lib import AbfallplusApp

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN  # pylint:disable=unused-import


class AbfallPlusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Abfallplus."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    api = AbfallplusApp()

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        if user_input is not None:
            for app in self.api.get_apps():
                if user_input["app_id"] == app["name"]:
                    self.api.set_app(app)
                    break
            return await self.async_step_community()

        # create form
        data_schema = vol.Schema(
            {vol.Required("app_id"): vol.In([a["name"] for a in self.api.get_apps()])}
        )
        return self.async_show_form(step_id="user", data_schema=data_schema)

    async def async_step_community(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step in config flow to add a repo to watch."""
        communities = await self.api.get_communities()
        if user_input is not None:
            for com in communities:
                if user_input["community_id"] == com["name"]:
                    self.api.set_community(com)
                    break
            return await self.async_step_street()

        # create form
        data_schema = vol.Schema(
            {vol.Required("community_id"): vol.In([a["name"] for a in communities])}
        )
        return self.async_show_form(step_id="community", data_schema=data_schema)

    async def async_step_street(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step in config flow to add a repo to watch."""
        streets = await self.api.get_streets()
        if user_input is not None:
            for st in streets:
                if user_input["street_id"] == st["name"]:
                    self.api.set_street(st)
                    break
            return await self.async_step_hnr()

        # create form
        data_schema = vol.Schema(
            {vol.Required("street_id"): vol.In([a["name"] for a in streets])}
        )
        return self.async_show_form(
            step_id="street", data_schema=data_schema, errors={}
        )

    async def async_step_hnr(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step in config flow to add a repo to watch."""
        hnr = await self.api.get_hnr()
        if user_input is not None:
            for h in hnr:
                if user_input["hnr_id"] == h["name"]:
                    self.api.set_hnr(h)
                    break
            return await self.async_step_abfallarten()

        # create form
        data_schema = vol.Schema(
            {vol.Required("hnr_id"): vol.In([a["name"] for a in hnr])}
        )
        return self.async_show_form(step_id="hnr", data_schema=data_schema)

    async def async_step_abfallarten(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step in config flow to add a repo to watch."""
        abfallarten = await self.api.get_abfallarten()
        if user_input is not None:
            for ab in user_input["abfallarten_id"]:
                for a in abfallarten:
                    if ab == a["name"]:
                        self.api.add_abfallart(a)
            config_json = await self.api.finalize_assistant()
            return self.async_create_entry(title="Abfallplus", data=config_json)

        # create form
        all_abfallarten = {a["name"]: a["name"] for a in abfallarten}
        data_schema = vol.Schema(
            {
                vol.Optional(
                    "abfallarten_id", default=list(all_abfallarten.keys())
                ): cv.multi_select(all_abfallarten),
            }
        )

        return self.async_show_form(
            step_id="abfallarten", data_schema=data_schema, errors={}
        )
