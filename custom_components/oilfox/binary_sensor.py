"""Platform for binary sensor integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
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

BINARY_SENSORS = {
    "validationErrorStatus": {
        "id": "validationErrorStatus",
        "api": "validationErrorStatus",
        "icon": "mdi:alert-circle",
        "name": "ValidationErrorStatus",
        "device_class": BinarySensorDeviceClass.PROBLEM,
    },
    "batteryLevelStatus": {
        "id": "batteryLevelStatus",
        "api": "batteryLevel",
        "icon": "mdi:battery-alert",
        "name": "batteryLevelStatus",
        "device_class": BinarySensorDeviceClass.BATTERY,
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

    if coordinator.data is None or coordinator.data is False:
        raise ConfigEntryNotReady(
            f"Error on Coordinator Data Result: {repr(coordinator.data)}"
        )

    oilfox_devices = coordinator.data["items"]
    entities = []

    for oilfox_device in oilfox_devices:
        _LOGGER.info("OilFox: Found Device in API: %s", oilfox_device["hwid"])
        for sensor_key, sensor_details in BINARY_SENSORS.items():
            _LOGGER.info(
                "OilFox: Create Sensor %s for Device %s",
                sensor_key,
                oilfox_device["hwid"],
            )
            oilfox_binary_sensor = OilFoxBinarySensor(
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

            oilfox_binary_sensor.set_api_response(oilfox_device)

            # Prefill sensor state based on the device data
            if sensor_key == "batteryLevelStatus":
                state = oilfox_device[sensor_details["api"]] in {"WARNING", "CRITICAL"}
            elif sensor_key == "validationErrorStatus":
                state = "validationError" in oilfox_device
            oilfox_binary_sensor.set_state(state)
            _LOGGER.debug(
                "Prefill entity %s with %s",
                sensor_key,
                state,
            )

            entities.append(oilfox_binary_sensor)

    async_add_entities(entities)


class OilFoxBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """OilFox BinarySensor Class."""

    def __init__(
        self,
        coordinator: CoordinatorEntity,
        oilfox: OilFox,
        sensor_details: dict,
    ) -> None:
        """Init for OilFoxBinarySensor."""
        super().__init__(coordinator)
        self.sensor_details = sensor_details
        self.oilfox = oilfox
        self.api_response = ""

        self._attr_unique_id = f"OilFox-{self.oilfox.hwid}-{sensor_details['id']}"
        self._attr_name = f"OilFox-{self.oilfox.hwid}-{sensor_details['name']}"
        self._attr_device_class = sensor_details["device_class"]
        # self._attr_state_class = sensor_details["state_class"]
        self._attr_icon = sensor_details["icon"]
        # self._attr_native_unit_of_measurement = sensor_details["native_unit"]
        # self._attr_suggested_unit_of_measurement = sensor_details["suggested_unit"]
        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        # ToDo - restore old states

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        oilfox_devices = self.coordinator.data["items"]
        for oilfox_device in oilfox_devices:
            if oilfox_device["hwid"] == self.oilfox.hwid:
                if self.sensor_details["api"] == "validationErrorStatus":
                    state = "validationError" in oilfox_device
                elif self.sensor_details["api"] == "batteryLevel":
                    state = oilfox_device[self.sensor_details["api"]] in {
                        "WARNING",
                        "CRITICAL",
                    }
                self.set_state(state)
            self.async_write_ha_state()
            return

    def set_api_response(self, response):
        """Set API response manual."""
        self.api_response = response

    def set_state(self, state: bool) -> None:
        """Set state manually."""
        if state == self._attr_is_on:
            _LOGGER.debug(
                "Old and new state (%s) for sensor %s same, skip",
                self._attr_is_on,
                self.sensor_details["id"],
            )
            return
        if state is not None and state != "":
            _LOGGER.debug(
                "Set new state %s for sensor %s", state, self.sensor_details["id"]
            )
            self._attr_is_on = state

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.oilfox.hwid)},
            name="OilFox-" + self.oilfox.hwid,
        )
