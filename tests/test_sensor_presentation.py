"""Presentation-only sensor behavior with a minimal Home Assistant entity stub."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "dvbviewer_dms"


def _module(name: str, **attributes):
    value = types.ModuleType(name)
    value.__dict__.update(attributes)
    sys.modules[name] = value
    return value


def _load_sensor_module():
    for name in ("homeassistant", "homeassistant.components", "homeassistant.helpers"):
        if name not in sys.modules:
            package = _module(name)
            package.__path__ = []

    if "homeassistant.components.sensor" not in sys.modules:
        sensor_component = _module("homeassistant.components.sensor")
        sensor_component.SensorDeviceClass = SimpleNamespace(TIMESTAMP="timestamp")
        sensor_component.SensorEntity = type("SensorEntity", (), {})
    if "homeassistant.helpers.entity" not in sys.modules:
        entity = _module("homeassistant.helpers.entity")
        entity.EntityCategory = SimpleNamespace(DIAGNOSTIC="diagnostic")
        entity.DeviceInfo = lambda **kwargs: kwargs
    if "homeassistant.helpers.update_coordinator" not in sys.modules:
        coordinator = _module("homeassistant.helpers.update_coordinator")
        coordinator.CoordinatorEntity = type(
            "CoordinatorEntity",
            (),
            {"__init__": lambda self, value: setattr(self, "coordinator", value)},
        )

    package_name = "_dvbviewer_sensor_test"
    if package_name not in sys.modules:
        package = _module(package_name)
        package.__path__ = [str(INTEGRATION)]
    module_name = f"{package_name}.sensor"
    if module_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(module_name, INTEGRATION / "sensor.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    return sys.modules[module_name]


sensor_module = _load_sensor_module()
DmsTimer = sys.modules["_dvbviewer_sensor_test.api"].DmsTimer
LOCAL_TIMEZONE = sys.modules["_dvbviewer_sensor_test.api"].LOCAL_TIMEZONE
WakeScheduleManager = __import__("_dvbviewer_sensor_test.wake", fromlist=["WakeScheduleManager"]).WakeScheduleManager


class MemoryStore:
    def __init__(self):
        self.value = None

    async def async_load(self):
        return self.value

    async def async_save(self, value):
        self.value = value

    async def async_remove(self):
        self.value = None


def _coordinator(timers):
    return SimpleNamespace(
        config_entry=SimpleNamespace(entry_id="test-entry"),
        data=SimpleNamespace(timers=timers),
        last_update_success=True,
        api=SimpleNamespace(async_get_data=lambda: (_ for _ in ()).throw(AssertionError("DMS call"))),
    )


def _timer(timer_id, title, channel, start):
    return DmsTimer(timer_id, title, channel, start, start + timedelta(minutes=80), 80, False, {})


class FrozenDateTime:
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 15, 12, 0, tzinfo=tz or LOCAL_TIMEZONE)


def test_timestamp_sensor_contract_and_diagnostic_category_are_preserved():
    now = FrozenDateTime.now(LOCAL_TIMEZONE)
    soon = _timer("soon", "Il Duce e Margherita", "Rai 3 HD (AC3,oth)", now + timedelta(hours=1))
    later = _timer("later", "Più tardi", "Rai 1", now + timedelta(hours=2))
    coordinator = _coordinator([later, soon])
    prior_datetime = sensor_module.datetime
    sensor_module.datetime = FrozenDateTime
    try:
        sensor = sensor_module.DmsNextTimerSensor(coordinator, "next_recording")
        assert sensor._attr_translation_key == "next_recording"
        assert sensor._attr_unique_id == "test-entry_next_recording"
        assert sensor._attr_device_class == "timestamp"
        assert sensor._attr_entity_category == "diagnostic"
        assert sensor.native_value is soon.start
        assert sensor.extra_state_attributes == soon.as_dict()
    finally:
        sensor_module.datetime = prior_datetime


def test_display_sensor_formats_soonest_future_timer_and_exposes_its_attributes():
    now = FrozenDateTime.now(LOCAL_TIMEZONE)
    soon = _timer("soon", "Il Duce e Margherita", "Rai 3 HD (AC3,oth)", now + timedelta(hours=1))
    later = _timer("later", "Più tardi", "Rai 1", now + timedelta(hours=2))
    coordinator = _coordinator([later, soon])
    prior_datetime = sensor_module.datetime
    sensor_module.datetime = FrozenDateTime
    try:
        sensor = sensor_module.DmsNextTimerDisplaySensor(coordinator)
        assert sensor._attr_translation_key == "next_recording_display"
        assert sensor._attr_unique_id == "test-entry_next_recording_display"
        assert sensor._attr_device_class is None
        assert sensor._attr_entity_category is None
        assert sensor.native_value == "Il Duce e Margherita · Rai 3 HD (AC3,oth) · 13:00"
        assert sensor.extra_state_attributes == soon.as_dict()
    finally:
        sensor_module.datetime = prior_datetime


def test_display_sensor_returns_no_value_when_no_future_timer_exists():
    past = _timer("past", "Già trasmesso", "Rai 1", FrozenDateTime.now(LOCAL_TIMEZONE) - timedelta(hours=1))
    coordinator = _coordinator([past])
    prior_datetime = sensor_module.datetime
    sensor_module.datetime = FrozenDateTime
    try:
        sensor = sensor_module.DmsNextTimerDisplaySensor(coordinator)
        assert sensor.native_value is None
        assert sensor.extra_state_attributes == {}
    finally:
        sensor_module.datetime = prior_datetime


def test_wake_sensor_value_survives_offline_coordinator_and_store_restore():
    now = FrozenDateTime.now(LOCAL_TIMEZONE)
    timer = _timer("wake", "Programma", "Canale", now + timedelta(hours=2))
    store = MemoryStore()
    manager = WakeScheduleManager(store, 10)
    asyncio.run(manager.async_update_from_timers([timer], now))
    expected = manager.schedule.wake_at
    coordinator = _coordinator([timer])
    wake_sensor = sensor_module.DmsNextWakeSensor(coordinator, manager)
    assert wake_sensor.native_value == expected
    persisted = store.value.copy()

    coordinator.last_update_success = False
    coordinator.data = None
    assert wake_sensor.native_value == expected
    assert store.value == persisted

    restored_manager = WakeScheduleManager(store, 10)
    asyncio.run(restored_manager.async_restore())
    restored_sensor = sensor_module.DmsNextWakeSensor(coordinator, restored_manager)
    assert restored_sensor.native_value == expected
    assert restored_sensor.extra_state_attributes == store.value
