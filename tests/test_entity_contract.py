"""Static contract checks for entity registration where HA is not installed in tests."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "dvbviewer_dms"))

from api import public_recording


def test_only_requested_sensors_are_registered_and_removed_classes_are_absent():
    source = (ROOT / "custom_components/dvbviewer_dms/sensor.py").read_text()
    setup = source.split("async def async_setup_entry", 1)[1].split("class DmsStateSensor", 1)[0]
    for name in ("DmsStateSensor", "DmsNextTimerSensor", "DmsCurrentRecordingSensor", "DmsArchiveSensor", "DmsNextWakeSensor"):
        assert name in setup
    for removed in ("DmsVersionSensor", "DmsTimerCountSensor", "DmsRecordingCountSensor", "DmsChannelsSensor", "DmsTunersSensor"):
        assert removed not in source


def test_coordinator_entities_receive_unique_id_keys():
    sensor_source = (ROOT / "custom_components/dvbviewer_dms/sensor.py").read_text()
    for call in (
        'DmsStateSensor(coordinator, "status")',
        'DmsNextTimerSensor(coordinator, "next_recording")',
        'DmsCurrentRecordingSensor(coordinator, "current_recording")',
        'DmsArchiveSensor(coordinator, "recording_archive")',
    ):
        assert call in sensor_source

    binary_source = (ROOT / "custom_components/dvbviewer_dms/binary_sensor.py").read_text()
    assert 'DmsConnectivitySensor(coordinator, "connected")' in binary_source


def test_device_info_builder_does_not_shadow_home_assistant_entity_property():
    entity_source = (ROOT / "custom_components/dvbviewer_dms/entity.py").read_text()
    sensor_source = (ROOT / "custom_components/dvbviewer_dms/sensor.py").read_text()
    number_source = (ROOT / "custom_components/dvbviewer_dms/number.py").read_text()

    assert "def device_info(" not in entity_source
    assert "def build_device_info(" in entity_source
    assert "self._attr_device_info = self.build_device_info(coordinator)" in entity_source
    assert "DmsEntity.build_device_info(coordinator)" in sensor_source
    assert "DmsEntity.build_device_info(coordinator)" in number_source
    assert "DmsEntity.device_info(coordinator)" not in sensor_source
    assert "DmsEntity.device_info(coordinator)" not in number_source


def test_sensor_binary_and_number_platforms_are_loaded():
    source = (ROOT / "custom_components/dvbviewer_dms/__init__.py").read_text()
    for platform in ("Platform.SENSOR", "Platform.BINARY_SENSOR", "Platform.NUMBER"):
        assert platform in source


def test_diagnostics_uses_stored_coordinator():
    source = (ROOT / "custom_components/dvbviewer_dms/diagnostics.py").read_text()
    assert 'entry_data = hass.data[DOMAIN][entry.entry_id]' in source
    assert 'coordinator = entry_data["coordinator"]' in source


def test_config_numbers_have_expected_defaults_ranges_and_are_available_offline():
    source = (ROOT / "custom_components/dvbviewer_dms/number.py").read_text()
    const = (ROOT / "custom_components/dvbviewer_dms/const.py").read_text()
    for item in ("DEFAULT_WAKE_ADVANCE = 10", "MIN_WAKE_ADVANCE = 1", "MAX_WAKE_ADVANCE = 120", "DEFAULT_NEARBY_TIMER_THRESHOLD = 30", "MIN_NEARBY_TIMER_THRESHOLD = 0", "MAX_NEARBY_TIMER_THRESHOLD = 240"):
        assert item in const
    assert "async_update_entry(self.entry, options=options)" in source
    assert "async_set_advance(value)" in source
    assert "def available(self):\n        return True" in source
    assert "EntityCategory.CONFIG" in source
    assert "must be a whole number" in source


def test_all_translations_have_entity_names_for_public_entities():
    base = ROOT / "custom_components/dvbviewer_dms"
    for filename in ("strings.json", "translations/en.json", "translations/it.json"):
        data = json.loads((base / filename).read_text(encoding="utf-8"))
        entities = data["entity"]
        assert set(entities["sensor"]) == {"status", "next_recording", "current_recording", "recording_archive", "next_dms_wake"}
        assert set(entities["number"]) == {"wake_advance", "nearby_timer_threshold"}
        assert "connected" in entities["binary_sensor"]


def test_removed_private_contract_is_absent():
    base = ROOT / "custom_components/dvbviewer_dms"
    private_marker = "video" + "rec"
    probe_marker = "ff" + "probe"
    for path in base.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".json"}:
            text = path.read_text(encoding="utf-8").lower()
            assert private_marker not in text
            assert probe_marker not in text


def test_public_archive_metadata_excludes_paths_and_descriptions():
    public = public_recording({
        "id": "x", "start": "20261012", "duration": "30", "lastmodified": "t",
        "channel": "TV", "title": "Title", "file": "C:\\private\\secret.ts",
        "description": "Long description", "info": "Details",
    })
    assert set(public) == {"id", "start", "duration", "lastmodified", "channel", "title"}
    assert "private" not in repr(public)


def test_archive_remains_capped_at_25_records():
    source = (ROOT / "custom_components/dvbviewer_dms/sensor.py").read_text()
    assert "[:25]" in source
    assert '"truncated": len(recordings) > 25' in source
