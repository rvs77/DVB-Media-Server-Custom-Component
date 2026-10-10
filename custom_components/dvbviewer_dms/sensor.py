from __future__ import annotations

from datetime import datetime
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import ATTR_CHANNEL, ATTR_DURATION_MINUTES, ATTR_END, ATTR_RECORDING, ATTR_RECORDING_FILES, ATTR_RECORDING_COUNT, ATTR_RECORDING_TUNER_COUNT, ATTR_START, ATTR_TIMER_COUNT, ATTR_TIMER_ID, ATTR_TITLE, ATTR_TUNER_COUNT
from .entity import DmsEntity
from .api import LOCAL_TIMEZONE, public_recording


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["dvbviewer_dms"][entry.entry_id]
    async_add_entities([DmsStateSensor(coordinator), DmsVersionSensor(coordinator), DmsNextTimerSensor(coordinator), DmsCurrentRecordingSensor(coordinator), DmsTimerCountSensor(coordinator), DmsRecordingCountSensor(coordinator), DmsArchiveSensor(coordinator), DmsChannelsSensor(coordinator), DmsTunersSensor(coordinator)])


class DmsStateSensor(DmsEntity, SensorEntity):
    _attr_name = "Status"
    _attr_icon = "mdi:server-network"

    @property
    def native_value(self):
        status_count = self.coordinator.data.status.get("reccount", 0)
        try:
            dms_reports_recording = int(status_count) > 0
        except (TypeError, ValueError):
            dms_reports_recording = False
        return "recording" if dms_reports_recording or any(t.recording for t in self.coordinator.data.timers) else "idle"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data.status
        return {key: data.get(key) for key in ("timercount", "reccount", "nexttimer", "nextrec", "standbyblock", "tunercount", "rectunercount", "rights", "recfiles", "recfolders", "last_update") if key in data}


class DmsVersionSensor(DmsEntity, SensorEntity):
    _attr_name = "Version"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self): return self.coordinator.data.version


class DmsNextTimerSensor(DmsEntity, SensorEntity):
    _attr_name = "Next recording"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-clock"

    @property
    def _next(self):
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
    _attr_name = "Current recording"
    _attr_icon = "mdi:record-rec"

    @property
    def _recording(self): return next((t for t in self.coordinator.data.timers if t.recording), None)
    @property
    def native_value(self): return self._recording.title if self._recording else "none"
    @property
    def extra_state_attributes(self):
        timer = self._recording
        return {} if not timer else timer.as_dict()


class DmsTimerCountSensor(DmsEntity, SensorEntity):
    _attr_name = "Timer count"
    _attr_icon = "mdi:timer-outline"
    @property
    def native_value(self): return len(self.coordinator.data.timers)
    @property
    def extra_state_attributes(self):
        return {"timers": [timer.as_dict() for timer in self.coordinator.data.timers[:50]], "truncated": len(self.coordinator.data.timers) > 50}


class DmsRecordingCountSensor(DmsEntity, SensorEntity):
    _attr_name = "Recording files"
    _attr_icon = "mdi:archive-check"
    @property
    def native_value(self): return int(self.coordinator.data.status.get("recfiles", 0) or 0)


class DmsArchiveSensor(DmsEntity, SensorEntity):
    _attr_name = "Recording archive"
    _attr_icon = "mdi:archive"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self): return len(self.coordinator.data.recordings)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        latest = max(data.recordings, key=lambda item: item.get("start", ""), default=None)
        recent = sorted(data.recordings, key=lambda item: item.get("start", ""), reverse=True)[:25]
        return {
            "latest_recording": public_recording(latest) if latest else None,
            "recent_recordings": [public_recording(item) for item in recent],
            "truncated": len(data.recordings) > 25,
        }


class DmsChannelsSensor(DmsEntity, SensorEntity):
    _attr_name = "Channels"
    _attr_icon = "mdi:television-classic"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    @property
    def native_value(self): return self.coordinator.data.channels


class DmsTunersSensor(DmsEntity, SensorEntity):
    _attr_name = "Tuners"
    _attr_icon = "mdi:antenna"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    @property
    def native_value(self): return int(self.coordinator.data.status.get("tunercount", 0) or 0)
    @property
    def extra_state_attributes(self):
        status = self.coordinator.data.status
        return {"recording_tuners": status.get("rectunercount"), "stream_tuners": status.get("streamtunercount"), "stream_clients": status.get("streamclientcount"), "rtsp_clients": status.get("rtspclientcount")}
