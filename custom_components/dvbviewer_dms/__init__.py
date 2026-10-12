from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .coordinator import DmsCoordinator
from .const import (
    CONF_WAKE_ADVANCE, DEFAULT_WAKE_ADVANCE, DOMAIN, WAKE_STORAGE_VERSION,
)
from .wake import WakeScheduleManager

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    options = entry.options
    wake_advance = int(options.get(CONF_WAKE_ADVANCE, DEFAULT_WAKE_ADVANCE))
    if not 1 <= wake_advance <= 120:
        wake_advance = DEFAULT_WAKE_ADVANCE
    wake_store = Store(hass, WAKE_STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}_wake")
    wake_manager = WakeScheduleManager(
        wake_store,
        wake_advance,
    )
    await wake_manager.async_restore()
    coordinator = DmsCoordinator(hass, entry, wake_manager)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "wake_manager": wake_manager,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # A first-refresh failure must not hide persistent wake and local config
    # entities when the server is intentionally powered down.
    await coordinator.async_refresh()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
