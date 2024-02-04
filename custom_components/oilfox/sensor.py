"""Platform for sensor integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_START,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfTime,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import TIMEOUT, CONF_EMAIL, CONF_PASSWORD, CONF_HTTP_TIMEOUT, DOMAIN
from .OilFox import OilFox

_LOGGER = logging.getLogger(__name__)

KWH_PER_L_OIL = 9.8

SENSORS = {
    # index 0 = API Name & unique ID
    # index 1 = units of measurement
    # index 2 = icon
    # index 3 = HA friendly name
    # index 4 = device class
    # index 5 = state class
    "fillLevelPercent": [
        "fillLevelPercent",
        PERCENTAGE,
        "mdi:percent",
        "fillLevelPercent",
        None,
        SensorStateClass.TOTAL,
    ],
    "fillLevelQuantity": [
        "fillLevelQuantity",
        UnitOfVolume.LITERS,
        "mdi:hydraulic-oil-level",
        "fillLevelQuantity",
        SensorDeviceClass.VOLUME_STORAGE,
        SensorStateClass.TOTAL,
    ],
    "daysReach": [
        "daysReach",
        UnitOfTime.DAYS,
        "mdi:calendar-range",
        "daysReach",
        None,
        None,
    ],
    "batteryLevel": [
        "batteryLevel",
        PERCENTAGE,
        "mdi:battery",
        "batteryLevel",
        SensorDeviceClass.BATTERY,
        None,
    ],
    "validationError": [
        "validationError",
        None,
        "mdi:message-alert",
        "validationError",
        None,
        None,
    ],
    "currentMeteringAt": [
        "currentMeteringAt",
        None,
        "mdi:calendar-arrow-left",
        "lastMeasurement",
        SensorDeviceClass.TIMESTAMP,
        None,
    ],
    "nextMeteringAt": [
        "nextMeteringAt",
        None,
        "mdi:calendar-arrow-right",
        "nextMeasurement",
        SensorDeviceClass.TIMESTAMP,
        None,
    ],
    "usageCounter": [
        "usageCounter",
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:barrel",
        "energyConsumption",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "usageCounterQuantity": [
        "usageCounterQuantity",
        UnitOfVolume.LITERS,
        "mdi:barrel-outline",
        "usageCounterQuantity",
        SensorDeviceClass.VOLUME_STORAGE,
        SensorStateClass.TOTAL_INCREASING,
    ],
}

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up OilFox sensor."""

    @callback
    def schedule_import(_):
        """Schedule delayed import after HA is fully started."""
        async_call_later(hass, 10, do_import)

    @callback
    def do_import(_):
        """Process YAML import."""
        _LOGGER.warning("Import yaml configration settings into config flow")
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=dict(config)
            )
        )

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, schedule_import)


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

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("OilFox Coordinator Data Result: %s", repr(coordinator.data))
    if coordinator.data is None or coordinator.data is False:
        raise ConfigEntryNotReady(
            "Error on Coordinator Data Result: " + repr(coordinator.data)
        )
    oilfox_devices = coordinator.data["items"]
    entities = []
    for oilfox_device in oilfox_devices:
        _LOGGER.info("OilFox: Found Device in API: %s", oilfox_device["hwid"])
        for sensor in SENSORS.items():
            _LOGGER.debug(
                "OilFox: Create Sensor %s for Device %s",
                sensor[0],
                oilfox_device["hwid"],
            )
            oilfox_sensor = OilFoxSensor(
                coordinator,
                OilFox(
                    email,
                    password,
                    oilfox_device["hwid"],
                    timeout=config_entry.options[CONF_HTTP_TIMEOUT],
                ),
                sensor[1],
                hass,
            )
            oilfox_sensor.set_api_response(oilfox_device)
            if sensor[0] in oilfox_device:
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
            elif sensor[0] == "usageCounter":
                _LOGGER.debug(
                    'Prefill entity %s with "0"',
                    sensor[0],
                )
                oilfox_sensor.set_state(float(0))
            elif sensor[0] == "usageCounterQuantity":
                _LOGGER.debug(
                    'Prefill entity %s with "0"',
                    sensor[0],
                )
                oilfox_sensor.set_state(float(0))
            else:
                _LOGGER.debug(
                    "Prefill entity %s with empty value",
                    sensor[0],
                )
            oilfox_sensor.set_state("")
            entities.append(oilfox_sensor)
    async_add_entities(entities)


class OilFoxSensor(CoordinatorEntity, SensorEntity, RestoreEntity):
    """OilFox Sensor Class."""

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

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()

        if self.sensor[0] == "usageCounter":
            if not state:
                _LOGGER.debug("No saved State for %s", self.sensor[0])
                self._state = 0
            else:
                _LOGGER.debug(
                    "Old State %s for %s restored", state.state, self.sensor[0]
                )
                self._state = state.state
            if state is None or state.attributes.get("Previous Value") is None:
                self._extra_state_attributes["Previous Value"] = 0
            else:
                self._extra_state_attributes["Previous Value"] = state.attributes.get(
                    "Previous Value"
                )
            if state is None or state.attributes.get("Current Value") is None:
                self._extra_state_attributes["Current Value"] = 0
            else:
                self._extra_state_attributes["Current Value"] = state.attributes.get(
                    "Current Value"
                )
        if self.sensor[0] == "usageCounterQuantity":
            if not state:
                _LOGGER.debug("No saved State for %s", self.sensor[0])
                self._state = 0
            else:
                _LOGGER.debug(
                    "Old State %s for %s restored", state.state, self.sensor[0]
                )
                self._state = state.state
            if state is None or state.attributes.get("Previous Value") is None:
                self._extra_state_attributes["Previous Value"] = 0
            else:
                self._extra_state_attributes["Previous Value"] = state.attributes.get(
                    "Previous Value"
                )
            if state is None or state.attributes.get("Current Value") is None:
                self._extra_state_attributes["Current Value"] = 0
            else:
                self._extra_state_attributes["Current Value"] = state.attributes.get(
                    "Current Value"
                )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        oilfox_devices = self.coordinator.data["items"]
        for oilfox_device in oilfox_devices:
            if oilfox_device["hwid"] == self.oilfox.hwid:
                self.set_api_response(oilfox_device)
                if self.sensor[0] in oilfox_device:
                    if self.sensor[0] == "batteryLevel":
                        self._state = self.battery_mapping[
                            oilfox_device[self.sensor[0]]
                        ]
                    else:
                        self._state = oilfox_device[self.sensor[0]]

                    self._extra_state_attributes = {
                        "Last Measurement": self.api_response.get("currentMeteringAt"),
                        "Next Measurement": self.api_response.get("nextMeteringAt"),
                        "Battery": self.api_response.get("batteryLevel"),
                    }
                elif self.sensor[0] == "validationError":
                    self._state = "No Error"
                elif self.sensor[0] == "usageCounter":
                    _LOGGER.debug(
                        "Update for usageCounter current val %s and filled: %s",
                        self._extra_state_attributes["Current Value"],
                        oilfox_device.get("fillLevelQuantity"),
                    )
                    if self._extra_state_attributes[
                        "Current Value"
                    ] != oilfox_device.get("fillLevelQuantity"):
                        if (
                            self._extra_state_attributes["Current Value"] is None
                            or self._extra_state_attributes["Current Value"] == 0
                        ):
                            self._extra_state_attributes[
                                "Previous Value"
                            ] = self._extra_state_attributes["Current Value"]
                            self._extra_state_attributes["Current Value"] = float(
                                oilfox_device.get("fillLevelQuantity")
                            )
                            _LOGGER.debug(
                                "Current Value 0 or None, UpdatePrevious Value: %s \tCurrent Value: %s",
                                self._extra_state_attributes["Previous Value"],
                                self._extra_state_attributes["Current Value"],
                            )
                            self._state = 0
                        else:
                            self._extra_state_attributes[
                                "Previous Value"
                            ] = self._extra_state_attributes["Current Value"]
                            self._extra_state_attributes[
                                "Current Value"
                            ] = oilfox_device.get("fillLevelQuantity")

                            if self._extra_state_attributes["Previous Value"] > float(
                                self._extra_state_attributes["Current Value"]
                            ):
                                diff = (
                                    self._extra_state_attributes["Previous Value"]
                                    - self._extra_state_attributes["Current Value"]
                                )
                                self.set_state(
                                    float(self._state) + (KWH_PER_L_OIL * diff)
                                )
                                _LOGGER.debug(
                                    "Set state to %s because of calculated diff %s",
                                    self._state,
                                    diff,
                                )
                        _LOGGER.debug(
                            "Update attribute Previous Value for HWID %s with: %s\tUpdate attribute Current Value for HWID %s with: %s",
                            self.oilfox.hwid,
                            self._extra_state_attributes["Previous Value"],
                            self.oilfox.hwid,
                            self._extra_state_attributes["Current Value"],
                        )
                elif self.sensor[0] == "usageCounterQuantity":
                    _LOGGER.debug(
                        "Update for usageCounterQuantity current val %s and filled: %s",
                        self._extra_state_attributes["Current Value"],
                        oilfox_device.get("fillLevelQuantity"),
                    )
                    if self._extra_state_attributes[
                        "Current Value"
                    ] != oilfox_device.get("fillLevelQuantity"):
                        if (
                            self._extra_state_attributes["Current Value"] is None
                            or self._extra_state_attributes["Current Value"] == 0
                        ):
                            self._extra_state_attributes[
                                "Previous Value"
                            ] = self._extra_state_attributes["Current Value"]
                            self._extra_state_attributes["Current Value"] = float(
                                oilfox_device.get("fillLevelQuantity")
                            )
                            _LOGGER.debug(
                                "Current Value 0 or None, UpdatePrevious Value: %s \tCurrent Value: %s",
                                self._extra_state_attributes["Previous Value"],
                                self._extra_state_attributes["Current Value"],
                            )
                            self._state = 0
                        else:
                            self._extra_state_attributes[
                                "Previous Value"
                            ] = self._extra_state_attributes["Current Value"]
                            self._extra_state_attributes[
                                "Current Value"
                            ] = oilfox_device.get("fillLevelQuantity")

                            if self._extra_state_attributes["Previous Value"] > float(
                                self._extra_state_attributes["Current Value"]
                            ):
                                diff = abs(
                                    self._extra_state_attributes["Previous Value"]
                                    - self._extra_state_attributes["Current Value"]
                                )
                                self.set_state(float(self._state) + (diff))
                                _LOGGER.debug(
                                    "Set state to %s because of calculated diff %s",
                                    self._state,
                                    diff,
                                )
                        _LOGGER.debug(
                            "Update attribute Previous Value for HWID %s with: %s\tUpdate attribute Current Value for HWID %s with: %s",
                            self.oilfox.hwid,
                            self._extra_state_attributes["Previous Value"],
                            self.oilfox.hwid,
                            self._extra_state_attributes["Current Value"],
                        )

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

    def set_state(self, state):
        """Set state manual."""
        if state is not None and state != "":
            _LOGGER.debug("Set new state %s for sensor %s", state, self.sensor[0])
            if self.sensor[0] == "batteryLevel":
                self._state = self.battery_mapping[state]
            else:
                self._state = state

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
