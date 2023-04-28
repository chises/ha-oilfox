"""Oilfox API Class"""
import time
import logging
import aiohttp

_LOGGER = logging.getLogger(__name__)


class OilFox:
    """OilFox Python Class"""

    # https://github.com/foxinsights/customer-api
    TIMEOUT = 15
    TOKEN_VALID = 900
    hwid = None
    password = None
    email = None
    access_token = None
    refresh_token = None
    update_token = None
    baseUrl = "https://api.oilfox.io"
    loginUrl = baseUrl + "/customer-api/v1/login"
    deviceUrl = baseUrl + "/customer-api/v1/device/"
    tokenUrl = baseUrl + "/customer-api/v1/token"

    def __init__(self, email, password, hwid):
        self.email = email
        self.password = password
        self.hwid = hwid
        self.state = None

    async def test_connection(self):
        """Test connection to OilFox Api"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.baseUrl) as response:
                if response.status == 200:
                    return True
                return False

    async def test_authentication(self):
        """Test authentication with OilFox Api"""
        return await self.get_tokens()

    async def update_stats(self):
        """Update OilFox API Values"""
        not_error = True
        if self.refresh_token is None:
            not_error = await self.get_tokens()
            _LOGGER.debug("Update Refresh Token: %s", not_error)

        if int(time.time()) - self.update_token > self.TOKEN_VALID:
            not_error = await self.get_access_token()
            _LOGGER.debug("Update Access Token: %s", not_error)

        if not not_error:
            _LOGGER.debug("Update Access Token failed, Refresh all Tokens!")
            not_error = await self.get_tokens()
            _LOGGER.debug("Update Tokens: %s", not_error)

        if not_error:
            headers = {"Authorization": "Bearer " + self.access_token}
            async with aiohttp.ClientSession(timeout=self.TIMEOUT) as session:
                try:
                    async with session.get(
                        self.deviceUrl + self.hwid,
                        headers=headers,
                        timeout=self.TIMEOUT,
                    ) as response:
                        if response.status == 200:
                            self.state = await response.json()
                            return True
                        _LOGGER.debug(repr(response))
                        return False
                except Exception as err:
                    _LOGGER.error("Update values failed: %s", repr(err))
                    return False
        return False

    async def get_tokens(self):
        """Update Refresh and Access Token"""
        headers = {"Content-Type": "application/json"}
        json_data = {
            "password": self.password,
            "email": self.email,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.loginUrl, headers=headers, json=json_data, timeout=self.TIMEOUT
            ) as response:
                if response.status == 200:
                    json_response = await response.json()
                    self.access_token = json_response["access_token"]
                    self.refresh_token = json_response["refresh_token"]
                    self.update_token = int(time.time())
                    _LOGGER.debug("Update Refresh and Access Token: ok")
                    return True
                _LOGGER.error("Get Refresh Token: failed")
                return False

    async def get_access_token(self):
        """Update Access Token"""
        data = {
            "refresh_token": self.refresh_token,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.tokenUrl, data=data, timeout=self.TIMEOUT
            ) as response:
                if response.status == 200:
                    json_response = await response.json()
                    self.access_token = json_response["access_token"]
                    self.refresh_token = json_response["refresh_token"]
                    self.update_token = int(time.time())
                    _LOGGER.debug("Update Access Token: ok")
                    return True
                _LOGGER.error("Get Access Token: failed")
                return False
