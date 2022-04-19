"""Platform for sensor integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    PLATFORM_SCHEMA
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

import requests
import logging
import time  
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)
ICON = "mdi:propane-tank"

DOMAIN = "OilFox_api"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"


# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_EMAIL): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
})

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    email = config[CONF_EMAIL]
    _LOGGER.info("OilFox: Setup User:"+email)
    password = config[CONF_PASSWORD] 

    OilFoxs_items = OilFoxApiWrapper(email,password).getItems()
    entities = [ ]
    
    for item in OilFoxs_items:
        _LOGGER.info("OilFox: Found Device in API:"+item['hwid'])
        entities.append(OilFoxSensor(OilFox(email, password, item['hwid'])))

    add_entities(entities)


class OilFox:
    #https://github.com/foxinsights/customer-api
    hwid = None
    password = None
    email = None
    access_token = None
    refresh_token = None
    update_token = None

    def __init__(self,email, password, hwid):
        self.email = email
        self.password = password
        self.hwid = hwid

        self.getTokens()
    
    def updateStats(self):
        if self.refresh_token is None:
            self.getTokens()
        
        if int(time.time())-self.update_token > 800:
            self.getAccessToken()

        headers = { 'Authorization': "Bearer " + self.access_token }
        response = requests.get('https://api.oilfox.io/customer-api/v1/device/'+self.hwid, headers=headers)

        self.currentMeteringAt = response.json()['currentMeteringAt']
        self.daysReach = response.json()['daysReach']
        self.batteryLevel = response.json()['batteryLevel']
        self.fillLevelPercent = response.json()['fillLevelPercent']
        self.fillLevelQuantity = response.json()['fillLevelQuantity']
        self.quantityUnit = response.json()['quantityUnit']

    def getTokens(self):
        headers = { 'Content-Type': 'application/json' }
        json_data = {
            'password': self.password,
            'email': self.email,
        }

        response = requests.post("https://api.oilfox.io/customer-api/v1/login", headers=headers, json=json_data)
        self.access_token = response.json()['access_token']
        self.refresh_token = response.json()['refresh_token']
        self.update_token = int(time.time())

    def getAccessToken(self):
        headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
        response = requests.get("https://api.oilfox.io/customer-api/v1/token?refresh_token="+self.refresh_token, headers=headers)
        self.access_token = response.json()['access_token']
        self.refresh_token = response.json()['refresh_token']
        self.update_token = int(time.time())

class OilFoxApiWrapper:
    ## Wrapper to collect all Devices attached to the Account and Create OilFox 
    loginUrl = "https://api.oilfox.io/customer-api/v1/login"
    deviceUrl = "https://api.oilfox.io/customer-api/v1/device"

    def __init__(self, email, password):
        self.email = email
        self.password = password
        
    def getItems(self):
        headers = { 'Content-Type': 'application/json' }
        json_data = {
            'password': self.password,
            'email': self.email,
        }

        response = requests.post("https://api.oilfox.io/customer-api/v1/login", headers=headers, json=json_data)
        self.access_token = response.json()['access_token']
        self.refresh_token = response.json()['refresh_token']

        headers = { 'Authorization': "Bearer " + self.access_token }
        response = requests.get('https://api.oilfox.io/customer-api/v1/device', headers=headers)

        items = response.json()['items']
        
        return items

class OilFoxSensor(SensorEntity):
    OilFox = None
    _attr_icon = ICON

    def __init__(self, element):
        self._state = None
        self.OilFox = element
        self.OilFox.updateStats()
        self._state = self.OilFox.fillLevelQuantity

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "OilFox-"+self.OilFox.hwid

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self.OilFox.quantityUnit
    
    @property
    def extra_state_attributes(self):
        """Return the attributes of the sensor."""
        additional_attributes={
            "battery": self.OilFox.batteryLevel,
            "fillLevelPercent": self.OilFox.fillLevelPercent,
            "daysReach": self.OilFox.daysReach
        }

        return additional_attributes

    def update(self) -> None:
        self.OilFox.updateStats()
        _LOGGER.info("OilFox: Update OilFox Value:"+str(self.OilFox.fillLevelQuantity))
        self._state = self.OilFox.fillLevelQuantity