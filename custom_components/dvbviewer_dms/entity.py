from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class DmsEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, description_key: str) -> None:
        super().__init__(coordinator)
        self._attr_device_info = self.build_device_info(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description_key}"

    @staticmethod
    def build_device_info(coordinator) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="DVBViewer Media Server",
            manufacturer="DVBViewer",
            model="Media Server",
        )
