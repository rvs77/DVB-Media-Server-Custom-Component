from __future__ import annotations

from datetime import datetime, timezone
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DmsApi, DmsData, DmsApiError, LOCAL_TIMEZONE
from .const import CONF_PASSWORD, CONF_PORT, CONF_USERNAME, DEFAULT_SCAN_INTERVAL, DOMAIN
from .wake import WakeScheduleManager

_LOGGER = logging.getLogger(__name__)


class DmsCoordinator(DataUpdateCoordinator[DmsData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, wake_manager: WakeScheduleManager) -> None:
        self.entry = entry
        self.wake_manager = wake_manager
        self.session = async_get_clientsession(hass)
        base_url = f"http://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"
        self.api = DmsApi(
            self.session,
            base_url,
            entry.data.get(CONF_USERNAME, ""),
            entry.data.get(CONF_PASSWORD, ""),
        )
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=DEFAULT_SCAN_INTERVAL)

    async def _async_update_data(self) -> DmsData:
        try:
            data = await self.api.async_get_data()
            await self.wake_manager.async_update_from_timers(data.timers, datetime.now(LOCAL_TIMEZONE))
            data.status["last_update"] = datetime.now(timezone.utc).isoformat()
            return data
        except DmsApiError as err:
            raise UpdateFailed(err) from err
