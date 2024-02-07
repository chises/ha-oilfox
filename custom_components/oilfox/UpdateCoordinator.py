"""Coordinator for OilFox."""

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import update_coordinator

from .const import DOMAIN
from .OilFox import OilFox

_LOGGER = logging.getLogger(__name__)


class UpdateCoordinator(update_coordinator.DataUpdateCoordinator):
    """Class to manage fetching Opengarage data."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        oilfox_api: OilFox,
    ) -> None:
        """Initialize global OilFox data updater."""
        self.oilfox_api = oilfox_api

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )

    async def _async_update_data(self) -> None:
        """Fetch data."""
        # _LOGGER.debug("UpdateCoordinator _async_update_data")
        try:
            await self.oilfox_api.update_stats()
        except Exception as err:
            raise ConfigEntryNotReady(repr(err)) from err
        return self.oilfox_api.state
