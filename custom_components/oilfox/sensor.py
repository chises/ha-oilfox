"""Platform for sensor integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_EMAIL,
    CONF_HTTP_TIMEOUT,
    CONF_PASSWORD,
    CONF_POLL_INTERVAL,
    DOMAIN,
    POLL_INTERVAL,
    TIMEOUT,
)
from .OilFox import OilFox

_LOGGER = logging.getLogger(__name__)

KWH_PER_L_OIL = 9.8

SENSORS = {
    "fillLevelPercent": {
        "id": "fillLevelPercent",
        "api": "fillLevelPercent",
        "native_unit": PERCENTAGE,
        "suggested_unit": None,
        "icon": "mdi:percent",
        "name": "fillLevelPercent",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL,
    },
    "fillLevelQuantity": {
        "id": "fillLevelQuantity",
        "api": "fillLevelQuantity",
        "native_unit": UnitOfVolume.LITERS,
        "suggested_unit": UnitOfVolume.LITERS,
        "icon": "mdi:hydraulic-oil-level",
        "name": "fillLevelQuantity",
        "device_class": SensorDeviceClass.VOLUME_STORAGE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "daysReach": {
        "id": "daysReach",
        "api": "daysReach",
        "native_unit": UnitOfTime.DAYS,
        "suggested_unit": UnitOfTime.DAYS,
        "icon": "mdi:calendar-range",
        "name": "daysReach",
        "device_class": SensorDeviceClass.DURATION,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "batteryLevel": {
        "id": "batteryLevel",
        "api": "batteryLevel",
        "native_unit": PERCENTAGE,
        "suggested_unit": None,
        "icon": "mdi:battery",
        "name": "batteryLevel",
        "device_class": SensorDeviceClass.BATTERY,
        "state_class": None,
    },
    "validationError": {
        "id": "validationError",
        "api": "validationError",
        "native_unit": None,
        "suggested_unit": None,
        "icon": "mdi:message-alert",
        "name": "validationError",
        "device_class": None,
        "state_class": None,
    },
    "currentMeteringAt": {
        "id": "lastMeasurement",
        "api": "currentMeteringAt",
        "native_unit": None,
        "suggested_unit": None,
        "icon": "mdi:calendar-arrow-left",
        "name": "lastMeasurement",
        "device_class": SensorDeviceClass.TIMESTAMP,
        "state_class": None,
    },
    "nextMeteringAt": {
        "id": "nextMeasurement",
        "api": "nextMeteringAt",
        "native_unit": None,
        "suggested_unit": None,
        "icon": "mdi:calendar-arrow-right",
        "name": "nextMeasurement",
        "device_class": SensorDeviceClass.TIMESTAMP,
        "state_class": None,
    },
    "usageCounter": {
        "id": "usageCounter",
        "api": None,
        "native_unit": UnitOfEnergy.KILO_WATT_HOUR,
        "suggested_unit": None,
        "icon": "mdi:barrel",
        "name": "energyConsumption",
        # "device_class": SensorDeviceClass.ENERGY,
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "usageCounterQuantity": {
        "id": "usageCounterQuantity",
        "api": None,
        "native_unit": UnitOfVolume.LITERS,
        "suggested_unit": None,
        "icon": "mdi:barrel-outline",
        "name": "usageCounterQuantity",
        # "device_class": SensorDeviceClass.VOLUME,
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
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

    timeout = config_entry.options.get(CONF_HTTP_TIMEOUT, TIMEOUT)
    _LOGGER.info("Timeout value: %s", timeout)

    poll_interval = config_entry.options.get(CONF_POLL_INTERVAL, POLL_INTERVAL)
    _LOGGER.info("Poll interval: %s", poll_interval)

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    coordinator.update_interval = timedelta(minutes=poll_interval)
    _LOGGER.debug("OilFox Coordinator Data Result: %s", repr(coordinator.data))

    if not coordinator.data:
        raise ConfigEntryNotReady(
            f"Error on Coordinator Data Result: {repr(coordinator.data)}"
        )

    oilfox_devices = coordinator.data["items"]
    entities = []

    for oilfox_device in oilfox_devices:
        _LOGGER.debug("OilFox: Found Device in API: %s", oilfox_device["hwid"])
        for sensor_key, sensor_details in SENSORS.items():
            _LOGGER.info(
                "OilFox: Create Sensor %s for Device %s",
                sensor_key,
                oilfox_device["hwid"],
            )
            oilfox_sensor = OilFoxSensor(
                coordinator,
                OilFox(
                    email,
                    password,
                    oilfox_device["hwid"],
                    timeout=timeout,
                    poll_interval=poll_interval,
                ),
                sensor_details,
            )
            oilfox_sensor.set_api_response(oilfox_device)

            # Prefill sensor state based on the device data
            if sensor_details["api"] in oilfox_device:
                _LOGGER.debug(
                    "Prefill entity %s with %s",
                    sensor_key,
                    oilfox_device[sensor_details["api"]],
                )
                oilfox_sensor.set_state(oilfox_device[sensor_key])
            elif sensor_key == "validationError":
                _LOGGER.debug('Prefill entity %s with "No Error"', sensor_key)
                oilfox_sensor.set_state("No Error")
            elif sensor_key in {"usageCounter", "usageCounterQuantity"}:
                _LOGGER.debug('Prefill entity %s with "0"', sensor_key)
                oilfox_sensor.set_state(float(0))
            else:
                _LOGGER.debug("Prefill entity %s with empty value", sensor_key)
                oilfox_sensor.set_state(None)

            entities.append(oilfox_sensor)

    async_add_entities(entities)


class OilFoxSensor(CoordinatorEntity, RestoreSensor):
    """OilFox Sensor Class."""

    battery_mapping = {
        "FULL": 100,
        "GOOD": 70,
        "MEDIUM": 50,
        "WARNING": 20,
        "CRITICAL": 0,
    }

    def __init__(
        self,
        coordinator: CoordinatorEntity,
        oilfox: OilFox,
        sensor_details: dict,
    ) -> None:
        """Initialize the OilFox sensor."""
        super().__init__(coordinator)
        self.sensor_details = sensor_details
        self.oilfox = oilfox
        self.api_response = ""

        self._attr_unique_id = f"OilFox-{self.oilfox.hwid}-{sensor_details['id']}"
        self._attr_name = f"OilFox-{self.oilfox.hwid}-{sensor_details['name']}"
        self._attr_device_class = sensor_details["device_class"]
        self._attr_state_class = sensor_details["state_class"]
        self._attr_icon = sensor_details["icon"]
        self._attr_native_unit_of_measurement = sensor_details["native_unit"]
        self._attr_suggested_unit_of_measurement = sensor_details["suggested_unit"]
        self._extra_state_attributes = {}

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        last_sensor_data = await self.async_get_last_sensor_data()
        if last_sensor_data:
            self._attr_native_value = last_sensor_data.native_value
        if last_state:
            _LOGGER.debug(
                "Restoring state for %s: %s",
                self.sensor_details["id"],
                last_state.attributes,
            )
            self._extra_state_attributes = dict(last_state.attributes)
        #    self._attr_native_unit_of_measurement = last_state.attributes.get(
        #        "unit_of_measurement"
        #    )
        else:
            _LOGGER.debug("No previous state found for %s", self.sensor_details["id"])
            self._extra_state_attributes = {}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        oilfox_devices = self.coordinator.data["items"]
        for oilfox_device in oilfox_devices:
            if oilfox_device["hwid"] == self.oilfox.hwid:
                self.set_api_response(oilfox_device)
                if self.sensor_details["api"] in oilfox_device:
                    self.set_state(oilfox_device[self.sensor_details["api"]])
                    self._extra_state_attributes = {
                        "Last Measurement": self.api_response.get("currentMeteringAt"),
                        "Next Measurement": self.api_response.get("nextMeteringAt"),
                        "Battery": self.api_response.get("batteryLevel"),
                    }
                elif self.sensor_details["id"] == "validationError":
                    self._attr_native_value = "No Error"
                self.async_write_ha_state()
                return

    def set_api_response(self, response: dict) -> None:
        """Set API response manually."""
        self.api_response = response

    def set_state(self, state: str | float | None) -> None:
        """Set state manually."""
        if (
            state == self._attr_native_value
            or (
                self.sensor_details["api"] == "batteryLevel"
                and self._attr_native_value == self.battery_mapping.get(state, None)
            )
            or (
                self.sensor_details["api"] in {"currentMeteringAt", "nextMeteringAt"}
                and self._attr_native_value == datetime.fromisoformat(state)
            )
        ):
            _LOGGER.debug(
                "Old and new state (%s) for sensor %s same, skip",
                self._attr_native_value,
                self.sensor_details["id"],
            )
            return
        if state is not None and state != "":
            if self.sensor_details["api"] == "batteryLevel":
                self._attr_native_value = self.battery_mapping.get(state, None)
            elif self.sensor_details["api"] in {"currentMeteringAt", "nextMeteringAt"}:
                self._attr_native_value = datetime.fromisoformat(state)
            else:
                self._attr_native_value = state
            _LOGGER.debug(
                "Set new state %s for sensor %s", state, self.sensor_details["id"]
            )

    @property
    def extra_state_attributes(self) -> dict:
        """Get extra attributes."""
        return self._extra_state_attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.oilfox.hwid)},
            name=f"OilFox-{self.oilfox.hwid}",
        )
