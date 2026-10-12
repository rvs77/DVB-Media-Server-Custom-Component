from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import EntityCategory

from .api import LOCAL_TIMEZONE, public_recording
from .const import DOMAIN
from .entity import DmsEntity


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    async_add_entities([
        DmsStateSensor(coordinator),
        DmsNextTimerSensor(coordinator),
        DmsCurrentRecordingSensor(coordinator),
        DmsArchiveSensor(coordinator),
        DmsNextWakeSensor(coordinator, data["wake_manager"]),
    ])


class DmsStateSensor(DmsEntity, SensorEntity):
    _attr_translation_key = "status"
    _attr_icon = "mdi:server-network"

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        status_count = self.coordinator.data.status.get("reccount", 0)
        try:
            dms_reports_recording = int(status_count) > 0
        except (TypeError, ValueError):
            dms_reports_recording = False
        return "recording" if dms_reports_recording or any(t.recording for t in self.coordinator.data.timers) else "idle"

    @property
    def extra_state_attributes(self):
        if self.coordinator.data is None:
            return {}
        data = self.coordinator.data.status
        return {
            key: data.get(key)
            for key in (
                "timercount", "reccount", "nexttimer", "nextrec", "standbyblock",
                "tunercount", "rectunercount", "rights", "recfiles", "recfolders", "last_update",
            )
            if key in data
        }


class DmsNextTimerSensor(DmsEntity, SensorEntity):
    _attr_translation_key = "next_recording"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-clock"

    @property
    def _next(self):
        if self.coordinator.data is None:
            return None
        now = datetime.now(LOCAL_TIMEZONE)
        future = [t for t in self.coordinator.data.timers if t.start and t.start > now]
        return min(future, key=lambda t: t.start) if future else None

    @property
    def native_value(self):
        timer = self._next
        return timer.start if timer and timer.start else None

    @property
    def extra_state_attributes(self):
        timer = self._next
        return {} if not timer else timer.as_dict()


class DmsCurrentRecordingSensor(DmsEntity, SensorEntity):
    _attr_translation_key = "current_recording"
    _attr_icon = "mdi:record-rec"

    @property
    def _recording(self):
        return next((t for t in self.coordinator.data.timers if t.recording), None) if self.coordinator.data else None

    @property
    def native_value(self):
        return self._recording.title if self._recording else "none"

    @property
    def extra_state_attributes(self):
        timer = self._recording
        return {} if not timer else timer.as_dict()


class DmsArchiveSensor(DmsEntity, SensorEntity):
    _attr_translation_key = "recording_archive"
    _attr_icon = "mdi:archive"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        return len(self.coordinator.data.recordings) if self.coordinator.data else None

    @property
    def extra_state_attributes(self):
        if self.coordinator.data is None:
            return {}
        recordings = self.coordinator.data.recordings
        latest = max(recordings, key=lambda item: item.get("start", ""), default=None)
        recent = sorted(recordings, key=lambda item: item.get("start", ""), reverse=True)[:25]
        return {
            "latest_recording": public_recording(latest) if latest else None,
            "recent_recordings": [public_recording(item) for item in recent],
            "truncated": len(recordings) > 25,
        }


class DmsNextWakeSensor(SensorEntity):
    """Wake sensor that stays available independently of the DMS coordinator."""

    _attr_has_entity_name = True
    _attr_translation_key = "next_dms_wake"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:power-sleep"

    def __init__(self, coordinator, manager) -> None:
        self.coordinator = coordinator
        self.manager = manager
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_next_dms_wake"
        self._attr_device_info = DmsEntity.device_info(coordinator)

    @property
    def available(self):
        return True

    @property
    def native_value(self):
        return self.manager.schedule.wake_at if self.manager.schedule else None

    @property
    def extra_state_attributes(self):
        schedule = self.manager.schedule
        return schedule.as_storage() if schedule else {}

    async def async_added_to_hass(self):
        self.manager.add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self.manager.remove_listener(self.async_write_ha_state)
