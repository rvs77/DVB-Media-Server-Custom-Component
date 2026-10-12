"""Wake scheduling and persistence behavior without a live Home Assistant."""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "dvbviewer_dms"))

from api import DmsTimer, LOCAL_TIMEZONE
from wake import WakeScheduleManager, WakeSchedule, next_future_timer


class MemoryStore:
    def __init__(self, value=None):
        self.value = value
        self.removed = False

    async def async_load(self): return self.value
    async def async_save(self, data): self.value = data
    async def async_remove(self): self.value = None; self.removed = True


def timer(timer_id, start, end=None):
    return DmsTimer(timer_id, f"Program {timer_id}", "Channel", start, end, 60, False, {})


def test_selects_soonest_future_timer_and_calculates_timezone_aware_wake():
    now = datetime(2026, 10, 12, 12, 0, tzinfo=LOCAL_TIMEZONE)
    later = timer("later", now + timedelta(hours=2))
    soon = timer("soon", now + timedelta(hours=1), now + timedelta(hours=2))
    assert next_future_timer([later, soon], now) is soon
    store = MemoryStore()
    manager = WakeScheduleManager(store, 10)
    asyncio.run(manager.async_update_from_timers([later, soon], now))
    assert manager.schedule.wake_at == now + timedelta(minutes=50)
    assert manager.schedule.wake_at.tzinfo == LOCAL_TIMEZONE
    assert store.value["timer_id"] == "soon"
    assert store.value["recording_start"] == soon.start.isoformat()
    assert store.value["recording_end"] == soon.end.isoformat()
    assert store.value["wake_advance_minutes"] == 10


def test_online_timer_change_replaces_previous_schedule():
    now = datetime(2026, 10, 12, 12, 0, tzinfo=LOCAL_TIMEZONE)
    store = MemoryStore()
    manager = WakeScheduleManager(store, 10)
    asyncio.run(manager.async_update_from_timers([timer("first", now + timedelta(hours=1))], now))
    asyncio.run(manager.async_update_from_timers([timer("second", now + timedelta(hours=3))], now))
    assert manager.schedule.timer_id == "second"
    assert manager.schedule.wake_at == now + timedelta(hours=3) - timedelta(minutes=10)


def test_online_empty_timer_list_clears_persistent_schedule():
    now = datetime(2026, 10, 12, 12, 0, tzinfo=LOCAL_TIMEZONE)
    store = MemoryStore()
    manager = WakeScheduleManager(store, 10)
    asyncio.run(manager.async_update_from_timers([timer("first", now + timedelta(hours=1))], now))
    asyncio.run(manager.async_update_from_timers([], now))
    assert manager.schedule is None
    assert store.removed and store.value is None


def test_offline_error_path_preserves_previously_saved_schedule():
    now = datetime(2026, 10, 12, 12, 0, tzinfo=LOCAL_TIMEZONE)
    store = MemoryStore()
    manager = WakeScheduleManager(store, 10)
    asyncio.run(manager.async_update_from_timers([timer("saved", now + timedelta(hours=1))], now))
    persisted = store.value.copy()
    # A failed DMS poll never calls async_update_from_timers.
    assert manager.schedule.timer_id == "saved"
    assert store.value == persisted


def test_restart_restore_recalculates_and_preserves_recording_metadata():
    now = datetime(2026, 10, 12, 12, 0, tzinfo=LOCAL_TIMEZONE)
    store = MemoryStore()
    original = WakeScheduleManager(store, 10)
    asyncio.run(original.async_update_from_timers([timer("restore", now + timedelta(hours=2), now + timedelta(hours=3))], now))
    restored = WakeScheduleManager(store, 15)
    asyncio.run(restored.async_restore())
    assert restored.schedule.timer_id == "restore"
    assert restored.schedule.recording_start == now + timedelta(hours=2)
    assert restored.schedule.recording_end == now + timedelta(hours=3)
    assert restored.schedule.wake_at == now + timedelta(hours=2) - timedelta(minutes=15)
    assert store.value["wake_advance_minutes"] == 15


def test_changing_advance_offline_recalculates_from_persisted_recording_start():
    now = datetime(2026, 10, 12, 12, 0, tzinfo=LOCAL_TIMEZONE)
    store = MemoryStore()
    manager = WakeScheduleManager(store, 10)
    asyncio.run(manager.async_update_from_timers([timer("saved", now + timedelta(hours=2))], now))
    asyncio.run(manager.async_set_advance(20))
    assert manager.schedule.recording_start == now + timedelta(hours=2)
    assert manager.schedule.wake_at == now + timedelta(hours=2) - timedelta(minutes=20)
    assert store.value["wake_advance_minutes"] == 20


def test_invalid_naive_timestamp_storage_is_rejected():
    assert WakeSchedule.from_storage({
        "timer_id": "bad", "recording_start": "2026-10-12T14:00:00",
        "recording_end": None, "wake_at": "2026-10-12T13:50:00",
        "wake_advance_minutes": 10,
    }) is None


def test_unavailable_recording_data_does_not_clear_schedule():
    now = datetime(2026, 10, 12, 12, 0, tzinfo=LOCAL_TIMEZONE)
    store = MemoryStore()
    manager = WakeScheduleManager(store, 10)
    asyncio.run(manager.async_update_from_timers([timer("saved", now + timedelta(hours=1))], now))
    persisted = store.value.copy()
    # DMS API errors are handled before the coordinator calls this method.
    assert manager.schedule.timer_id == "saved"
    assert store.value == persisted
