"""Oilfox API Class."""
import asyncio
import logging
import time

import aiohttp

from homeassistant.exceptions import ConfigEntryNotReady

_LOGGER = logging.getLogger(__name__)


class OilFox:
    """OilFox Python Class."""

    # https://github.com/foxinsights/customer-api
    TIMEOUT = 300
    POLL_INTERVAL = 30
    TOKEN_VALID = 900
    hwid: str = ""
    password: str = ""
    email: str = ""
    access_token: str = ""
    refresh_token: str = ""
    update_token: int = 0
    base_url = "https://api.oilfox.io"
    login_url = base_url + "/customer-api/v1/login"
    device_url = base_url + "/customer-api/v1/device"
    token_url = base_url + "/customer-api/v1/token"

    def __init__(self, email, password, hwid, timeout=300, poll_interval=30):
        """Init Method for OilFox Class."""
        self.email = email
        self.password = password
        self.hwid = hwid
        self.TIMEOUT = timeout
        self.POLL_INTERVAL = poll_interval
        self.state = None
        #if self.hwid is None or self.hwid == "":
        #    _LOGGER.info(
        #        "Init OilFox with Username %s",
        #        self.email,
        #        self.TIMEOUT,
        #        self.POLL_INTERVAL,
        #    )

    async def test_connection(self):
        """Test connection to OilFox Api."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.TIMEOUT)
        ) as session, session.get(self.base_url) as response:
            if response.status == 200:
                return True
            return False

    async def test_authentication(self):
        """Test authentication with OilFox Api."""
        return await self.get_tokens()

    async def update_stats(self):
        """Update OilFox API Values."""

        not_error = True
        if self.refresh_token == "":
            not_error = await self.get_tokens()
            # _LOGGER.debug("Update Refresh Token: %s", not_error)

        if int(time.time()) - self.update_token > self.TOKEN_VALID:
            not_error = await self.get_access_token()
            _LOGGER.debug("Update Access Token: %s", not_error)

        if not not_error:
            _LOGGER.debug("Update Access Token failed, Refresh all Tokens!")
            not_error = await self.get_tokens()
            _LOGGER.debug("Update Tokens: %s", not_error)

        if not_error:
            headers = {"Authorization": "Bearer " + self.access_token}
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT)
            ) as session:
                try:
                    async with session.get(
                        self.device_url + self.hwid, headers=headers
                    ) as response:
                        if response.status == 200:
                            self.state = await response.json()
                # except asyncio.TimeoutError:
                #    raise ConfigEntryNotReady(  # noqa: TRY200
                #        f"Update values failed because of http timeout (waited for {self.TIMEOUT} s)!"
                #    )

                except Exception as err:
                    _LOGGER.error(
                        "Update values failed for unknown reason! %s", repr(err)
                    )
                    _LOGGER.error(repr(response))
                    return False

                return True
        else:
            _LOGGER.debug("Could not get Refresh and Access Token:")
        return False

    async def get_tokens(self):
        """Update Refresh and Access Token."""
        headers = {"Content-Type": "application/json"}
        json_data = {
            "password": self.password,
            "email": self.email,
        }

        async with aiohttp.ClientSession() as session, session.post(
            self.login_url,
            headers=headers,
            json=json_data,
            timeout=aiohttp.ClientTimeout(total=self.TIMEOUT),
        ) as response:
            if response.status == 200:
                json_response = await response.json()
                self.access_token = json_response["access_token"]
                self.refresh_token = json_response["refresh_token"]
                self.update_token = int(time.time())
                _LOGGER.debug(
                    "Update Refresh and Access Token: ok [%s]", response.status
                )
                return True
            _LOGGER.error("Get Refresh Token: failed [%s]", response.status)
            return False

    async def get_access_token(self):
        """Update Access Token."""
        data = {
            "refresh_token": self.refresh_token,
        }
        async with aiohttp.ClientSession() as session, session.post(
            self.token_url, data=data, timeout=aiohttp.ClientTimeout(total=self.TIMEOUT)
        ) as response:
            _LOGGER.debug("Get Access Token:%s", response.status)
            if response.status == 200:
                json_response = await response.json()
                self.access_token = json_response["access_token"]
                self.refresh_token = json_response["refresh_token"]
                self.update_token = int(time.time())
                _LOGGER.debug("Update Access Token: ok [%s]", response.status)
                return True
            _LOGGER.error("Get Access Token: failed [%s]", response.status)
            return False
