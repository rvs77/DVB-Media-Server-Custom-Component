from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD, DOMAIN

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
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]
    data = coordinator.data

    diagnostics = {
        "entry": {"data": dict(entry.data), "options": dict(entry.options)},
    }
    if data is not None:
        diagnostics.update(
            {
                "status": data.status,
                "version": data.version,
                "channels": data.channels,
                "timers": [timer.as_dict() for timer in data.timers],
                "recording_count": len(data.recordings),
            }
        )

    return async_redact_data(diagnostics, TO_REDACT)
