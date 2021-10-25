# %%
import datetime
import plistlib as plist

from dateutil.parser import parse
import aiohttp
import asyncio
import uuid
from bs4 import BeautifulSoup
import logging

_LOGGER = logging.getLogger(__name__)


class AbfallplusApp:

    HEADERS = {
        "user-agent": "Android",
        "Content-Type": "application/x-www-form-urlencoded",
        "Connection": "Keep-Alive",
    }
    BASE_URL = "https://app.abfallplus.de/"

    config = {}

    def __init__(self, config=None):
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

    def __createPostData(self, additional_post_data=None):
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
        """Return all supported app IDs covered by the waste management company

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

    def set_app(self, app):
        self.config["app"] = app
        _LOGGER.debug("Set app to be %s", app)

    async def get_communities(self):
        return await self.__request(url="assistent/kommune/")

    def set_community(self, community):
        self.config["community"] = community
        _LOGGER.debug("Set community to be %s", community)

    async def get_streets(self):
        return await self.__request(url="assistent/strasse/")

    def set_street(self, street):
        self.config["street"] = street
        _LOGGER.debug("Set street to be %s", street)

    async def get_hnr(self):
        return await self.__request(url="assistent/hnr/")

    def set_hnr(self, hnr):
        self.config["hnr"] = hnr
        _LOGGER.debug("Set hnr to be %s", hnr)

    async def get_abfallarten(self):
        return await self.__request(url="assistent/abfallarten/")

    def add_abfallart(self, abfallart):
        self.config["abfallarten"].append(abfallart)
        _LOGGER.debug("Appended abfallart %s", abfallart)

    async def finalize_assistant(self):

        post = [
            ("f_uhrzeit_tag", "86400|0"),
            ("f_uhrzeit_stunden", "57600"),
            ("f_uhrzeit_minuten", "2100"),
            ("f_anonym", "1"),
            ("f_ausgangspunkt", "start"),
            ("f_ueberspringen", "0"),
            ("f_datenschutz", datetime.datetime.now().strftime("%Y%m%d%H%M%S")),
        ]
        await self.__request(url="assistent/finish/", additional_post_data=post)
        return self.config

    async def get_pickup_times(self):

        post_data = {
            "client": self.config["client_id"],
            "app_id": self.config["app"]["app_id"],
        }

        async with aiohttp.ClientSession() as session:
            await session.post(
                url=self.BASE_URL + "login",
                data=post_data,
                cookies=self.config["cookie"],
                headers=self.HEADERS,
            )
            await session.post(
                url=self.BASE_URL + "version.xml?renew=1",
                data=post_data,
                cookies=self.config["cookie"],
                headers=self.HEADERS,
            )
            async with session.post(
                url=self.BASE_URL + "struktur.xml.zip",
                data=post_data,
                headers=self.HEADERS,
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Error in fetching pickup times")
                    return

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

    async def __login(self):

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
                url=self.BASE_URL + "config.xml",
                data=post_data,
                headers=self.HEADERS,
            ) as resp:
                self.config["cookie"] = session.cookie_jar.filter_cookies(self.BASE_URL)
                status = resp.status

            if status != 200:
                _LOGGER.warning("Cookie fetching failed")
            else:
                async with session.post(
                    url=self.BASE_URL + "login/",
                    data=post_data,
                    headers=self.HEADERS,
                ) as resp:
                    if resp.status != 200:
                        _LOGGER.warning("Login failed")
                    _LOGGER.debug("Login sucessfull")

    async def __request(self, url, additional_post_data=None):

        await self.__login()

        _LOGGER.debug("Starting request to %s", self.BASE_URL + url)

        # Request data
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self.BASE_URL + url,
                data=self.__createPostData(additional_post_data),
                cookies=self.config["cookie"],
                headers=self.HEADERS,
            ) as resp:
                received_data = await resp.content.read()
                status = resp.status

        if status != 200:
            _LOGGER.warning("Error in request: %s", status)
        else:
            return self.__parseConfigEntries(received_data)

    def __parseConfigEntries(self, received_data):

        if b"OK|Yeah" in received_data:
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
        else:
            for li in html.find_all("li"):
                name = li.contents[2].replace("\n", "").replace(" ", "")
                input_id = li.input.attrs["id"][15:]
                extracted_data.append({"name": name, "data": input_id})
            return extracted_data


async def main():
    api = AbfallplusApp()

    apps = api.get_apps()
    api.set_app(apps[0])

    communities = await api.get_communities()
    api.set_community(communities[0])

    streets = await api.get_streets()
    api.set_street(streets[0])

    hnr = await api.get_hnr()
    api.set_hnr(hnr[0])

    abfallart = await api.get_abfallarten()
    api.add_abfallart(abfallart[0])
    api.add_abfallart(abfallart[1])

    config = await api.finalize_assistant()
    print(config)

    # Reset API and use config
    api = AbfallplusApp(config)
    pickup_times = await api.get_pickup_times()
    print(pickup_times)


if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
