"""Coordinator for OilFox"""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import update_coordinator
from datetime import timedelta
from .const import DOMAIN
from .OilFox import OilFox

import logging

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
            update_interval=timedelta(minutes=10),
        )

    async def _async_update_data(self) -> None:
        """Fetch data."""
        try:
            await self.oilfox_api.update_stats()
        finally:
            return self.oilfox_api.state
