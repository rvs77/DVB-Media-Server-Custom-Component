from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.storage import Store

from .api import LOCAL_TIMEZONE, public_recording
from .const import DOMAIN
from .entity import DmsEntity


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    async_add_entities([
        DmsStateSensor(coordinator, "status"),
        DmsNextTimerSensor(coordinator, "next_recording"),
        DmsNextTimerDisplaySensor(coordinator),
        DmsLastRecordingSensor(coordinator),
        DmsCurrentRecordingSensor(coordinator, "current_recording"),
        DmsArchiveSensor(coordinator, "recording_archive"),
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


class DmsNextTimerSensor(DmsEntity, SensorEntity, RestoreEntity):
    _attr_translation_key = "next_recording"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, description_key: str) -> None:
        super().__init__(coordinator, description_key)
        self._stored_value = None
        self._stored_attributes = {}
        self._store = Store(coordinator.hass, 1, f"{DOMAIN}_{coordinator.config_entry.entry_id}_{description_key}_state")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        restored = await self.async_get_last_state()
        if restored and restored.state not in ("unknown", "unavailable", ""):
            self._stored_value = datetime.fromisoformat(restored.state)
            self._stored_attributes = dict(restored.attributes)
        persisted = await self._store.async_load()
        if persisted and persisted.get("value"):
            try:
                self._stored_value = datetime.fromisoformat(persisted["value"])
                self._stored_attributes = persisted.get("attributes", {})
            except (TypeError, ValueError):
                pass
    def _handle_coordinator_update(self) -> None:
        value = self._next.start if self._next else None
        if value:
            self._stored_value = value
            self._stored_attributes = self._next.as_dict()
            self.hass.async_create_task(self._async_persist())
        self.async_write_ha_state()

    @property
    def available(self):
        return True

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
        if timer and timer.start:
            self._stored_value = timer.start
            self._stored_attributes = timer.as_dict()
            return timer.start
        return self._stored_value

    @property
    def extra_state_attributes(self):
        timer = self._next
        if timer:
            return timer.as_dict()
        return self._stored_attributes

    async def async_update(self) -> None:
        value = self.native_value
        if value is None:
            return
        self._stored_value = value
        self._stored_attributes = self.extra_state_attributes
        await self._async_persist()

    async def _async_persist(self) -> None:
        value = self._stored_value
        if value is None:
            return
        await self._store.async_save({
            "value": value.isoformat(),
            "attributes": self._stored_attributes,
        })


class DmsLastRecordingSensor(DmsEntity, SensorEntity, RestoreEntity):
    _attr_translation_key = "last_recording"
    _attr_icon = "mdi:history"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "last_recording")
        self._stored_recording = None
        self._store = Store(coordinator.hass, 1, f"{DOMAIN}_{coordinator.config_entry.entry_id}_last_recording_state")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        restored = await self.async_get_last_state()
        if restored and restored.state not in ("unknown", "unavailable", ""):
            self._stored_recording = dict(restored.attributes)
            self._stored_recording.setdefault("title", restored.state)
        persisted = await self._store.async_load()
        if persisted and self._valid_recording(persisted):
            self._stored_recording = persisted
    def _handle_coordinator_update(self) -> None:
        recording = self._latest
        if recording:
            self._stored_recording = recording
            self.hass.async_create_task(self._store.async_save(recording))
        self.async_write_ha_state()

    @staticmethod
    def _valid_recording(recording):
        return isinstance(recording, dict) and any(
            isinstance(recording.get(key), str) and recording[key].strip()
            for key in ("title", "channel", "start")
        )

    @property
    def available(self):
        return True

    @property
    def _latest(self):
        recordings = self.coordinator.data.recordings if self.coordinator.data else []
        latest = max(recordings, key=lambda item: item.get("start", ""), default=None)
        recording = public_recording(latest) if latest else None
        return recording if self._valid_recording(recording) else None

    @property
    def native_value(self):
        recording = self._latest or self._stored_recording
        return recording.get("title") if recording else None

    @property
    def extra_state_attributes(self):
        recording = self._latest or self._stored_recording
        return recording or {}

    async def async_update(self) -> None:
        recording = self._latest
        if recording:
            self._stored_recording = recording
            await self._store.async_save(recording)


class DmsNextTimerDisplaySensor(DmsNextTimerSensor):
    """Human-readable view of the next timer, using coordinator data only."""

    _attr_translation_key = "next_recording_display"
    _attr_device_class = None
    _attr_entity_category = None

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "next_recording_display")

    @property
    def native_value(self):
        timer = self._next
        if not timer or not timer.start:
            return None
        local_start = timer.start.astimezone(LOCAL_TIMEZONE)
        return f"{timer.title} · {timer.channel} · {local_start:%H:%M}"


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
        self._attr_device_info = DmsEntity.build_device_info(coordinator)

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
