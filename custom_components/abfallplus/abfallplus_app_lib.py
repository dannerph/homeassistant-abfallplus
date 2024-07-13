# %%
import asyncio
import datetime
import logging
import plistlib as plist
import uuid

import aiohttp
from bs4 import BeautifulSoup
from dateutil.parser import parse

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "user-agent": "Android",
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "Keep-Alive",
}
BASE_URL = "https://app.abfallplus.de/"


class AbfallplusApp:
    """Abfallplus API class."""

    config = {}

    def __init__(self, config=None) -> None:
        """Instantiate a new abfallplus.Api object."""

        if config is not None:
            self.config = config
        else:
            self.config["client_id"] = str(uuid.uuid1())
            self.config["cookie"] = None
            self.config["app"] = None
            self.config["community"] = None
            self.config["street"] = None
            self.config["hnr"] = None
            self.config["abfallarten"] = []

    def _createPostData(self, additional_post_data=None):
        c = self.config
        post_data = [
            ("id_bezirk", ""),
            ("f_id_bezirk", ""),
        ]
        if c["app"] is not None:
            post_data.append(("id_landkreis", c["app"]["landkreis_id"]))
            post_data.append(("f_id_landkreis", c["app"]["landkreis_id"]))
            post_data.append(("f_id_bundesland", c["app"]["bundesland_id"]))
        if c["community"] is not None:
            post_data.append(("id_kommune", c["community"]["data"]))
            post_data.append(("f_id_kommune", c["community"]["data"]))
        if c["street"] is not None:
            post_data.append(("id_strasse", c["street"]["data"]))
            post_data.append(("f_id_strasse", c["street"]["data"]))
        if c["hnr"] is not None:
            post_data.append(("f_hnr", c["hnr"]["data"]))
        for e in c["abfallarten"]:
            post_data.append(("f_id_abfallart[]", e["data"]))
        if additional_post_data is not None:
            for e in additional_post_data:
                post_data.append((e[0], e[1]))
        return post_data

    def get_apps(self):
        """Return all supported app IDs covered by the waste management company.

        Returns:
            list: A sequence of app ID instances.

        """
        apps_mapping = []
        apps_mapping.append(
            {
                "name": "ZAW-DW",
                "app_id": "de.k4systems.zawdw",
                "landkreis_id": "633|0|AWG Donau-Wald",
                "bundesland_id": "247",
            }
        )
        # TODO: Add all the other apps

        return apps_mapping

    def set_app(self, app) -> None:
        """Set the app to be used for the API."""

        self.config["app"] = app
        _LOGGER.debug("Set app to be %s", app)

    async def get_communities(self):
        """Return all communities covered by the waste management company."""

        return await self._request(url="assistent/kommune/")

    def set_community(self, community):
        """Set the community to be used for the API."""

        self.config["community"] = community
        _LOGGER.debug("Set community to be %s", community)

    async def get_streets(self):
        """Return all streets covered by the waste management company."""

        return await self._request(url="assistent/strasse/")

    def set_street(self, street) -> None:
        """Set the street to be used for the API."""

        self.config["street"] = street
        _LOGGER.debug("Set street to be %s", street)

    async def get_hnr(self):
        """Return all house numbers covered by the waste management company."""

        return await self._request(url="assistent/hnr/")

    def set_hnr(self, hnr) -> None:
        """Set the house number to be used for the API."""

        self.config["hnr"] = hnr
        _LOGGER.debug("Set hnr to be %s", hnr)

    async def get_abfallarten(self):
        """Return all waste types covered by the waste management company."""

        return await self._request(url="assistent/abfallarten/")

    def add_abfallart(self, abfallart) -> None:
        """Add a waste type to be used for the API."""

        self.config["abfallarten"].append(abfallart)
        _LOGGER.debug("Appended abfallart %s", abfallart)

    async def finalize_assistant(self) -> dict:
        """Finalize the assistant and return the configuration."""
        await asyncio.sleep(3)
        post = [
            ("f_uhrzeit_tag", "86400|0"),
            ("f_uhrzeit_stunden", "57600"),
            ("f_uhrzeit_minuten", "2100"),
            ("f_anonym", "1"),
            ("f_ausgangspunkt", "start"),
            ("f_ueberspringen", "0"),
            ("f_datenschutz", datetime.datetime.now().strftime("%Y%m%d%H%M%S")),
        ]
        await self._request(url="assistent/finish/", additional_post_data=post)
        return self.config

    async def get_pickup_times(self) -> dict | None:
        """Return the pickup times for the configured waste types."""

        post_data = {
            "client": self.config["client_id"],
            "app_id": self.config["app"]["app_id"],
        }

        async with aiohttp.ClientSession() as session:
            await session.post(
                url=BASE_URL + "login",
                data=post_data,
                cookies=self.config["cookie"],
                headers=HEADERS,
            )
            await session.post(
                url=BASE_URL + "version.xml?renew=1",
                data=post_data,
                cookies=self.config["cookie"],
                headers=HEADERS,
            )
            async with session.post(
                url=BASE_URL + "struktur.xml.zip",
                data=post_data,
                headers=HEADERS,
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Error in fetching pickup times")
                    return None

                # Parse pickup data
                received_data = await resp.content.read()
                content = plist.loads(received_data, fmt=plist.FMT_XML)
                extracted_data = {}
                for a in self.config["abfallarten"]:
                    dates = []
                    i = 0
                    for d in content["dates"]:
                        if d["category_id"].split("-")[1] == a["data"]:
                            date_only = parse(d["pickup_date"]).date()
                            dates.append(date_only)
                            i = i + 1
                        if i > 1:
                            break
                    extracted_data[a["name"]] = dates
                return extracted_data

    async def _login(self) -> None:
        """Login to the API."""

        if self.config["app"]["app_id"] is None:
            raise ValueError("Set app first")

        # Return if cookie already set
        if self.config["cookie"] is not None:
            return

        post_data = {
            "client": self.config["client_id"],
            "app_id": self.config["app"]["app_id"],
        }

        _LOGGER.debug("Starting login")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=BASE_URL + "config.xml",
                data=post_data,
                headers=HEADERS,
            ) as resp:
                self.config["cookie"] = session.cookie_jar.filter_cookies(BASE_URL)
                status = resp.status

            if status != 200:
                _LOGGER.warning("Cookie fetching failed")
            else:
                async with session.post(
                    url=BASE_URL + "login/",
                    data=post_data,
                    headers=HEADERS,
                ) as resp:
                    if resp.status != 200:
                        _LOGGER.warning("Login failed")
                    _LOGGER.debug("Login sucessfull")

    async def _request(self, url, additional_post_data=None) -> list:
        """Request data from the API."""

        await self._login()

        _LOGGER.debug("Starting request to %s", BASE_URL + url)

        # Request data
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                url=BASE_URL + url,
                data=self._createPostData(additional_post_data),
                cookies=self.config["cookie"],
                headers=HEADERS,
            ) as resp,
        ):
            received_data = await resp.text(encoding="utf-8")
            status = resp.status

        if status != 200:
            _LOGGER.warning("Error in request: %s", status)
        else:
            return self._parseConfigEntries(received_data)

    def _parseConfigEntries(self, received_data) -> list:
        """Parse the received data and return the config entries."""

        if "OK|Yeah" in received_data:
            _LOGGER.info("Sucessfully registered")

        extracted_data = []
        html = BeautifulSoup(received_data, "html.parser")

        if not html.find("input"):
            for li in html.find_all("li"):
                onclick = li.a.attrs["onclick"]
                onclick = onclick[onclick.find("step_fertig('") + 12 : -1]
                onclick_split = onclick.replace("'", "").split(",")
                extracted_data.append(
                    {"name": onclick_split[1], "data": onclick_split[0]}
                )
            return extracted_data
        for li in html.find_all("li"):
            name = li.contents[2].replace("\n", "").replace(" ", "")
            input_id = li.input.attrs["id"][15:]
            extracted_data.append({"name": name, "data": input_id})

        # Abfallarten
        if html.find("ion-list"):
            for item in html.find_all("ion-item"):
                name = item.find("ion-text").contents[0]
                onclick = item.contents[1].attrs["onclick"]
                input_id = onclick[4:].split("'")[0][15:]
                extracted_data.append({"name": name, "data": input_id})
        return extracted_data


# async def main():
#     api = AbfallplusApp()

#     apps = api.get_apps()
#     api.set_app(apps[0])

#     communities = await api.get_communities()
#     api.set_community(communities[85])

#     streets = await api.get_streets()
#     api.set_street(streets[117])

#     hnr = await api.get_hnr()
#     api.set_hnr(hnr[11])

#     abfallart = await api.get_abfallarten()
#     api.add_abfallart(abfallart[0])
#     api.add_abfallart(abfallart[1])

#     config = await api.finalize_assistant()

#     # Reset API and use config
#     api = AbfallplusApp(config)
#     pickup_times = await api.get_pickup_times()
#     print(pickup_times)


# if __name__ == "__main__":
#     logging.basicConfig()
#     _LOGGER.setLevel(logging.INFO)

#     loop = asyncio.new_event_loop()
#     loop.create_task(main())
#     loop.run_forever()
