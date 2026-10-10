from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .entity import DmsEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["dvbviewer_dms"][entry.entry_id]
    async_add_entities([DmsConnectivitySensor(coordinator)])


class DmsConnectivitySensor(DmsEntity, BinarySensorEntity):
    _attr_name = "Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self): return self.coordinator.last_update_success
