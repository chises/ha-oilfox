"""Platform for sensor integration."""

from __future__ import annotations
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from homeassistant.components.sensor import (
    SensorEntity,
    PLATFORM_SCHEMA
)

from homeassistant.const import (
    PERCENTAGE,
    VOLUME_LITERS,
    TIME_DAYS
)

import requests
import logging
import time  
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "OilFox_api"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
SCAN_INTERVAL = timedelta(minutes=10)
TOKEN_VALID = 900

SENSORS = {
    "fillLevelPercent": [
        "fillLevelPercent",
        PERCENTAGE,
        "mdi:percent",
    ],
    "fillLevelQuantity": [
        "fillLevelQuantity",
        VOLUME_LITERS,
        "mdi:hydraulic-oil-level",
    ],
    "daysReach": [
        "daysReach",
        TIME_DAYS,
        "mdi:calendar-range",
    ],
}

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
    if OilFoxs_items == False:
        _LOGGER.info("OilFox: Could not fetch informationn through API, invalid credentials?")
        return False

    entities = [ ]
    for item in OilFoxs_items:
        _LOGGER.info("OilFox: Found Device in API:"+item['hwid'])
        for key in SENSORS.keys():
            if not item.get(key) == None:
                _LOGGER.info("OilFox: Create Sensor "+SENSORS[key][0]+" for Device"+item['hwid'])
                entities.append(OilFoxSensor(OilFox(email, password, item['hwid']),SENSORS[key]))
            else:
                _LOGGER.info("OilFox: Device "+item['hwid']+" missing sensor "+SENSORS[key][0])

    add_entities(entities, True)

class OilFoxSensor(SensorEntity):
    OilFox = None
    sensor = None

    def __init__(self, element, sensor):

        self.sensor = sensor
        self.OilFox = element
        self.OilFox.updateStats()
        self._state = None

    @property
    def icon(self) -> str:
        """Return the name of the sensor."""
        return self.sensor[2]

    @property
    def unique_id(self) -> str:
        """Return the name of the sensor."""
        return "OilFox-"+self.OilFox.hwid+"-"+self.sensor[0]

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "OilFox-"+self.OilFox.hwid+"-"+self.sensor[0]

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self.sensor[1]

    @property
    def extra_state_attributes(self):
        """Return the attributes of the sensor."""
        additional_attributes={
            "Last Measurement": self.OilFox.state.get("currentMeteringAt"),
            "Next Measurement": self.OilFox.state.get("nextMeteringAt"),
            "Battery": self.OilFox.state.get("batteryLevel")
        }
        return additional_attributes

    def update(self) -> None:
        if self.OilFox.updateStats()  == False:
            _LOGGER.info("OilFox: Error Updating Values from Class!:"+str(self.OilFox.state))
        elif not self.OilFox.state == None and not self.OilFox.state.get(self.sensor[0]) == None:        
            self._state = self.OilFox.state.get(self.sensor[0])
        else:
            _LOGGER.info("OilFox: Error Updating Values!:"+str(self.OilFox.state))


class OilFoxApiWrapper:
    ## Wrapper to collect all Devices attached to the Account and Create OilFox 
    loginUrl = "https://api.oilfox.io/customer-api/v1/login"
    deviceUrl = "https://api.oilfox.io/customer-api/v1/device"
    
    def __init__(self, email, password):
        self.email = email
        self.password = password
        
    def getItems(self):
        items = [ ]
        headers = { 'Content-Type': 'application/json' }
        json_data = {
            'password': self.password,
            'email': self.email,
        }

        response = requests.post(self.loginUrl, headers=headers, json=json_data)
        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            self.refresh_token = response.json()['refresh_token']
            headers = { 'Authorization': "Bearer " + self.access_token }
            response = requests.get(self.deviceUrl, headers=headers)
            if response.status_code == 200:
                items = response.json()['items']
                return items
        return False

        

class OilFox:
    #https://github.com/foxinsights/customer-api
    hwid = None
    password = None
    email = None
    access_token = None
    refresh_token = None
    update_token = None
    loginUrl = "https://api.oilfox.io/customer-api/v1/login"
    deviceUrl = "https://api.oilfox.io/customer-api/v1/device/"
    tokenUrl = "https://api.oilfox.io/customer-api/v1/token"

    def __init__(self,email, password, hwid):
        self.email = email
        self.password = password
        self.hwid = hwid
        self.state = None
        self.getTokens()
    
    def updateStats(self):
        error = False
        if self.refresh_token is None:
            error = self.getTokens()
        
        if int(time.time())-self.update_token > TOKEN_VALID:
            error = self.getAccessToken()
            return True
        
        if not error:
            headers = { 'Authorization': "Bearer " + self.access_token }
            response = requests.get(self.deviceUrl+self.hwid, headers=headers)
            if response.status_code == 200:
                self.state = response.json()
                return True
        _LOGGER.info("Error in Update Access Token")
        return False

    def getTokens(self):
        headers = { 'Content-Type': 'application/json' }
        json_data = {
            'password': self.password,
            'email': self.email,
        }

        response = requests.post(self.loginUrl, headers=headers, json=json_data)
        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            self.refresh_token = response.json()['refresh_token']
            self.update_token = int(time.time())
            return True
        
        return False

    def getAccessToken(self):  
        data = {
            'refresh_token': self.refresh_token,
        }
        response = requests.post(self.tokenUrl, data=data)
        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            self.refresh_token = response.json()['refresh_token']
            self.update_token = int(time.time())
            return True
        _LOGGER.info("Update Access Token: failed")
        return False
