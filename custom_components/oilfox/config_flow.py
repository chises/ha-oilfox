"""Config flow for OilFox integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, TIMEOUT, CONF_HTTP_TIMEOUT, CONF_EMAIL, CONF_PASSWORD
from .OilFox import OilFox

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HTTP_TIMEOUT, default=TIMEOUT): vol.All(
            vol.Coerce(int), vol.Clamp(min=5, max=60)
        )
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    my_oilfox = OilFox(data[CONF_EMAIL], data[CONF_PASSWORD], "")

    if not await my_oilfox.test_connection():
        _LOGGER.info("Tests for OilFox: Connection failed")
        raise CannotConnect
    _LOGGER.debug("Tests for OilFox: Connection successful")

    if not await my_oilfox.test_authentication():
        _LOGGER.info("Tests for OilFox: Authentication failed")
        raise InvalidAuth
    _LOGGER.debug("Tests for OilFox: Authentication successful")

    return {"title": "OilFox", "email": data[CONF_EMAIL]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OilFox."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        await self.async_set_unique_id(user_input[CONF_EMAIL])
        self._abort_if_unique_id_configured()

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(
                title=info["title"] + ":" + info[CONF_EMAIL], data=user_input
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_import(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Import a config entry from configuration.yaml."""
        _LOGGER.warning(
            "OilFox Account from yaml File imported to Config Flow. Please remove your config from yaml file. It is not longer needed and yaml support will be removed in future!"
        )
        return await self.async_step_user(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_import(self, import_info: dict[str, Any]) -> FlowResult:
        """Set the config entry up from yaml."""
        return self.async_create_entry(title="", data=import_info)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        timeout = TIMEOUT
        if user_input is not None:
            # _LOGGER.info("Option Flow 2:%s", repr(user_input))
            return self.async_create_entry(title="", data=user_input)

        if "http-timeout" in self.options:
            timeout = self.options["http-timeout"]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HTTP_TIMEOUT,
                        default=timeout,
                    ): int
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
