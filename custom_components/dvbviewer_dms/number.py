"""GUI configuration entities for energy scheduling."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.entity import EntityCategory

from .const import (
    CONF_NEARBY_TIMER_THRESHOLD, CONF_WAKE_ADVANCE, DEFAULT_NEARBY_TIMER_THRESHOLD,
    DEFAULT_WAKE_ADVANCE, DOMAIN, MAX_NEARBY_TIMER_THRESHOLD, MAX_WAKE_ADVANCE,
    MIN_NEARBY_TIMER_THRESHOLD, MIN_WAKE_ADVANCE,
)
from .entity import DmsEntity


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        DmsConfigNumber(hass, entry, data["coordinator"], data["wake_manager"], CONF_WAKE_ADVANCE),
        DmsConfigNumber(hass, entry, data["coordinator"], data["wake_manager"], CONF_NEARBY_TIMER_THRESHOLD),
    ])


class DmsConfigNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _attr_mode = NumberMode.BOX

    def __init__(self, hass, entry, coordinator, wake_manager, key):
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.wake_manager = wake_manager
        self.key = key
        self._attr_device_info = DmsEntity.device_info(coordinator)
        if key == CONF_WAKE_ADVANCE:
            self._attr_translation_key = "wake_advance"
            self._attr_unique_id = f"{entry.entry_id}_wake_advance"
            self._attr_native_min_value = MIN_WAKE_ADVANCE
            self._attr_native_max_value = MAX_WAKE_ADVANCE
            self.default = DEFAULT_WAKE_ADVANCE
        else:
            self._attr_translation_key = "nearby_timer_threshold"
            self._attr_unique_id = f"{entry.entry_id}_nearby_timer_threshold"
            self._attr_native_min_value = MIN_NEARBY_TIMER_THRESHOLD
            self._attr_native_max_value = MAX_NEARBY_TIMER_THRESHOLD
            self.default = DEFAULT_NEARBY_TIMER_THRESHOLD

    @property
    def native_value(self):
        return int(self.entry.options.get(self.key, self.default))

    @property
    def available(self):
        return True

    async def async_set_native_value(self, value: float) -> None:
        if not float(value).is_integer():
            raise ValueError(f"{self.key} must be a whole number of minutes")
        value = int(value)
        if value < self._attr_native_min_value or value > self._attr_native_max_value:
            raise ValueError(f"{self.key} is outside the allowed range")
        options = {**self.entry.options, self.key: value}
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        if self.key == CONF_WAKE_ADVANCE:
            await self.wake_manager.async_set_advance(value)
        self.async_write_ha_state()
