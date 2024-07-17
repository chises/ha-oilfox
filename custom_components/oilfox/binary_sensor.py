"""Platform for binary sensor integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from datetime import timedelta
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    TIMEOUT,
    POLL_INTERVAL,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_HTTP_TIMEOUT,
    DOMAIN,
    CONF_POLL_INTERVAL,
)
from .OilFox import OilFox

_LOGGER = logging.getLogger(__name__)

BINARY_SENSORS = {
    # index 0 = API Name & unique ID
    # index 1 = units of measurement
    # index 2 = icon
    # index 3 = HA friendly name
    # index 4 = device class
    # index 5 = state class
    "validationErrorStatus": [
        "validationErrorStatus",
        None,
        "mdi:alert-circle",
        "validationError",
        BinarySensorDeviceClass.PROBLEM,
        None,
    ],
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize OilFox Integration config entry."""

    _LOGGER.info("OilFox: Setup User: %s", config_entry.data[CONF_EMAIL])
    email = config_entry.data[CONF_EMAIL]
    password = config_entry.data[CONF_PASSWORD]

    if CONF_HTTP_TIMEOUT in config_entry.options:
        timeout = config_entry.options[CONF_HTTP_TIMEOUT]
        _LOGGER.info(
            "Load custom timeout value: %s", config_entry.options[CONF_HTTP_TIMEOUT]
        )
    else:
        timeout = TIMEOUT
        _LOGGER.info("Load default timeout value: %s", timeout)

    if CONF_POLL_INTERVAL in config_entry.options:
        poll_interval = config_entry.options[CONF_POLL_INTERVAL]
        _LOGGER.info(
            "Load custom poll interval: %s", config_entry.options[CONF_POLL_INTERVAL]
        )
    else:
        poll_interval = POLL_INTERVAL
        _LOGGER.info("Load default poll intervall: %s", poll_interval)

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    coordinator.update_interval = timedelta(minutes=poll_interval)
    _LOGGER.debug("OilFox Coordinator Data Result: %s", repr(coordinator.data))
    if coordinator.data is None or coordinator.data is False:
        raise ConfigEntryNotReady(
            "Error on Coordinator Data Result: " + repr(coordinator.data)
        )
    oilfox_devices = coordinator.data["items"]
    entities = []
    for oilfox_device in oilfox_devices:
        _LOGGER.info("OilFox: Found Device in API: %s", oilfox_device["hwid"])
        for sensor in BINARY_SENSORS.items():
            _LOGGER.debug(
                "OilFox: Create Sensor %s for Device %s",
                sensor[0],
                oilfox_device["hwid"],
            )
            oilfox_sensor = OilFoxBinarySensor(
                coordinator,
                OilFox(
                    email,
                    password,
                    oilfox_device["hwid"],
                    timeout=timeout,
                    poll_interval=poll_interval,
                ),
                sensor[1],
                hass,
            )
            oilfox_sensor.set_api_response(oilfox_device)
            if sensor[0] == "validationErrorStatus":
                if "validationError" in oilfox_device:
                    _LOGGER.debug(
                        "Prefill entity %s with %s",
                        sensor[0],
                        "True",
                    )
                    oilfox_sensor.set_state(True)

            elif sensor[0] in oilfox_device:
                _LOGGER.debug(
                    "Prefill entity %s with %s",
                    sensor[0],
                    oilfox_device[sensor[0]],
                )
                oilfox_sensor.set_state(oilfox_device[sensor[0]])
            elif sensor[0] == "validationError":
                _LOGGER.debug(
                    'Prefill entity %s with "No Error"',
                    sensor[0],
                )
                oilfox_sensor.set_state("No Error")
            elif sensor[0] == "validationErrorStatus":
                _LOGGER.debug(
                    'Prefill entity %s with "False"',
                    sensor[0],
                )
                oilfox_sensor.set_state(False)
            else:
                _LOGGER.debug(
                    "Prefill entity %s with empty value",
                    sensor[0],
                )
            oilfox_sensor.set_state("")
            entities.append(oilfox_sensor)
    async_add_entities(entities)

class OilFoxBinarySensor(CoordinatorEntity, BinarySensorEntity, RestoreEntity):
    """OilFox BinarySensor Class."""

    api_response: str = ""
    oilfox: OilFox
    sensor: list[SensorStateClass]
    battery_mapping = {
        "FULL": 100,
        "GOOD": 70,
        "MEDIUM": 50,
        "WARNING": 20,
        "CRITICAL": 0,
    }
    validation_error_mapping = {
        "NO_METERING": "No measurement yet",
        "EMPTY_METERING": "Incorrect Measurement",
        "NO_EXTRACTED_VALUE": "No fill level detected",
        "SENSOR_CONFIG": "Faulty measurement",
        "MISSING_STORAGE_CONFIG": "Storage configuration missing",
        "INVALID_STORAGE_CONFIG": "Incorrect storage configuration",
        "DISTANCE_TOO_SHORT": "Measured distance too small",
        "ABOVE_STORAGE_MAX": "Storage full",
        "BELOW_STORAGE_MIN": "Calculated filling level implausible",
    }

    def __init__(self, coordinator, element, sensor, hass):
        """Init for OilFoxSensor."""
        super().__init__(coordinator)
        self._hass = hass
        self._attr_device_class = sensor[4]
        self.sensor = sensor
        self.oilfox = element
        self._state = None
        self.api_response: list[SensorStateClass]
        self._extra_state_attributes = {}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        oilfox_devices = self.coordinator.data["items"]
        for oilfox_device in oilfox_devices:
            if oilfox_device["hwid"] == self.oilfox.hwid:
                self.set_api_response(oilfox_device)
                if self.sensor[0] == "validationErrorStatus":
                    self._state = False
                    if "validationError" in oilfox_device:
                        self._state = True
                    else:
                        self._state = False
            _LOGGER.debug(
                "Update entity %s for HWID %s with value: %s",
                self.sensor[0],
                self.oilfox.hwid,
                self._state,
            )
            self.async_write_ha_state()
            return None

    @property
    def extra_state_attributes(self):
        """Get extra Attribute."""
        return self._extra_state_attributes

    def set_api_response(self, response):
        """Set API response manual."""
        self.api_response = response

    @property
    def extra_state_attributes(self):
        """Get extra Attribute."""
        return self._extra_state_attributes

    def set_api_response(self, response):
        """Set API response manual."""
        self.api_response = response

    def set_state(self, state):
        """Set state manual."""
        if state is not None and state != "":
            if self.sensor[0] == "batteryLevel":
                self._state = self.battery_mapping[state]
            elif self.sensor[0] == "validationError":
                self._state = state + ":" + self.validation_error_mapping[state]
            else:
                self._state = state
            _LOGGER.debug("Set new state %s for sensor %s", self._state, self.sensor[0])

    @property
    def icon(self) -> str:
        """Return the name of the sensor."""
        return self.sensor[2]

    @property
    def unique_id(self) -> str:
        """Return the unique_id of the sensor."""

        """Dirty workaround: entites meteringAt did use self.sensor[3] instead of self.sensor[0] as ID before ha-oilfox version 0.1.8"""
        if self.sensor[0] == "currentMeteringAt":
            return "OilFox-" + self.oilfox.hwid + "-" + self.sensor[3]
        if self.sensor[0] == "nextMeteringAt":
            return "OilFox-" + self.oilfox.hwid + "-" + self.sensor[3]
        return "OilFox-" + self.oilfox.hwid + "-" + self.sensor[0]

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "OilFox-" + self.oilfox.hwid + "-" + self.sensor[3]

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self.sensor[1]

    @property
    def state_class(self) -> SensorStateClass:
        """Return the state class."""
        return self.sensor[5]

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.oilfox.hwid)},
            name="OilFox-" + self.oilfox.hwid,
        )
