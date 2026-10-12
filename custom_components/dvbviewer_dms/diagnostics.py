from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD

TO_REDACT = {
    CONF_PASSWORD,
    "host",
    "file",
    "description",
    "info",
    "server_url",
    "recfolders",
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = hass.data["dvbviewer_dms"][entry.entry_id]
    data = coordinator.data
    return async_redact_data(
        {
            "entry": {"data": dict(entry.data), "options": dict(entry.options)},
            "status": data.status,
            "version": data.version,
            "channels": data.channels,
            "timers": [timer.as_dict() for timer in data.timers],
            "recording_count": len(data.recordings),
        },
        TO_REDACT,
    )
