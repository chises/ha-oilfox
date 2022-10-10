"""Platform for sensor integration."""

from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.const import (
    PERCENTAGE,
    VOLUME_LITERS,
    TIME_DAYS,
    EVENT_HOMEASSISTANT_START,
)
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD
from .OilFox import OilFox

_LOGGER = logging.getLogger(__name__)

SENSORS = {
    "fillLevelPercent": [
        "fillLevelPercent",
        PERCENTAGE,
        "mdi:percent",
        "fillLevelPercent",
    ],
    "fillLevelQuantity": [
        "fillLevelQuantity",
        VOLUME_LITERS,
        "mdi:hydraulic-oil-level",
        "fillLevelQuantity",
    ],
    "daysReach": [
        "daysReach",
        TIME_DAYS,
        "mdi:calendar-range",
        "daysReach",
    ],
    "batteryLevel": ["batteryLevel", PERCENTAGE, "mdi:battery", "batteryLevel"],
    "validationError": [
        "validationError",
        None,
        "mdi:message-alert",
        "validationError",
    ],
    "currentMeteringAt": [
        "currentMeteringAt",
        None,
        "mdi:calendar-arrow-left",
        "lastMeasurement",
    ],
    "nextMeteringAt": [
        "nextMeteringAt",
        None,
        "mdi:calendar-arrow-right",
        "nextMeasurement",
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
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    oilfox_devices = coordinator.data["items"]
    if not oilfox_devices:
        _LOGGER.error(
            "OilFox: Could not fetch information through API, invalid credentials?"
        )
        return False

    entities = []
    _LOGGER.debug("OilFox: Full API response: %s", oilfox_devices)
    for oilfox_device in oilfox_devices:
        _LOGGER.info("OilFox: Found Device in API: %s", oilfox_device["hwid"])
        for sensor in SENSORS.items():
            _LOGGER.debug(
                "OilFox: Create Sensor %s for Device %s",
                sensor[0],
                oilfox_device["hwid"],
            )
            oilfox_sensor = OilFoxSensor(
                coordinator, OilFox(email, password, oilfox_device["hwid"]), sensor[1]
            )
            oilfox_sensor.set_api_response(oilfox_device)
            if sensor[0] in oilfox_device:
                _LOGGER.debug(
                    "Prefill entity %s with %s",
                    sensor[0],
                    oilfox_device[sensor[0]],
                )
                oilfox_sensor.set_state(oilfox_device[sensor[0]])
            else:
                if sensor[0] == "validationError":
                    _LOGGER.debug(
                        'Prefill entity %s with "No Error"',
                        sensor[0],
                    )
                    oilfox_sensor.set_state("No Error")
                else:
                    _LOGGER.debug(
                        "Prefill entity %s with empty value",
                        sensor[0],
                    )
                    oilfox_sensor.set_state("")
            entities.append(oilfox_sensor)
    async_add_entities(entities)


class OilFoxSensor(CoordinatorEntity, SensorEntity):
    """OilFox Sensor Class"""

    api_response = None
    oilfox = None
    sensor = None
    battery_mapping = {
        "FULL": 100,
        "GOOD": 70,
        "MEDIUM": 50,
        "WARNING": 20,
        "CRITICAL": 0,
    }
    validationError_mapping = {
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

    def __init__(self, coordinator, element, sensor):
        super().__init__(coordinator)

        self.sensor = sensor
        self.oilfox = element
        self._state = None
        self.api_response = {}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        oilfox_devices = self.coordinator.data["items"]
        for oilfox_device in oilfox_devices:
            if oilfox_device["hwid"] == self.oilfox.hwid:
                self.set_api_response(oilfox_device)
                my_data = ""
                if self.sensor[0] in oilfox_device:
                    if self.sensor[0] == "batteryLevel":
                        my_data = self.battery_mapping[oilfox_device[self.sensor[0]]]
                    else:
                        my_data = oilfox_device[self.sensor[0]]
                elif self.sensor[0] == "validationError":
                    my_data = "No Error"

                _LOGGER.debug(
                    "Update entity %s for HWID %s with value: %s",
                    self.sensor[0],
                    self.oilfox.hwid,
                    my_data,
                )
                self._state = my_data
                self.async_write_ha_state()

    def set_api_response(self, response):
        """Set API response manual"""
        self.api_response = response

    def set_state(self, state):
        """Set state manual"""
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
        """Return the name of the sensor."""
        return "OilFox-" + self.oilfox.hwid + "-" + self.sensor[3]

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
    def extra_state_attributes(self):
        """Return the attributes of the sensor."""
        """_LOGGER.debug(
           'Extra stats: %s"',
            self.api_response,
        )"""
        additional_attributes = {
            "Last Measurement": self.api_response.get("currentMeteringAt"),
            "Next Measurement": self.api_response.get("nextMeteringAt"),
            "Battery": self.api_response.get("batteryLevel"),
        }
        return additional_attributes
