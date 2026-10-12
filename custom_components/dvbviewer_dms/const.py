from __future__ import annotations

from datetime import timedelta

DOMAIN = "dvbviewer_dms"
DEFAULT_PORT = 8089
DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VERIFY_SSL = "verify_ssl"
CONF_WAKE_ADVANCE = "wake_advance_minutes"
CONF_NEARBY_TIMER_THRESHOLD = "nearby_timer_threshold_minutes"
DEFAULT_WAKE_ADVANCE = 10
MIN_WAKE_ADVANCE = 1
MAX_WAKE_ADVANCE = 120
DEFAULT_NEARBY_TIMER_THRESHOLD = 30
MIN_NEARBY_TIMER_THRESHOLD = 0
MAX_NEARBY_TIMER_THRESHOLD = 240
WAKE_STORAGE_VERSION = 1
DEFAULT_OPTIONS = {
    CONF_WAKE_ADVANCE: DEFAULT_WAKE_ADVANCE,
    CONF_NEARBY_TIMER_THRESHOLD: DEFAULT_NEARBY_TIMER_THRESHOLD,
}

ATTR_TIMER_ID = "timer_id"
ATTR_TITLE = "title"
ATTR_CHANNEL = "channel"
ATTR_START = "start"
ATTR_END = "end"
ATTR_DURATION_MINUTES = "duration_minutes"
ATTR_RECORDING = "recording"
ATTR_TIMER_COUNT = "timer_count"
ATTR_RECORDING_COUNT = "recording_count"
ATTR_RECORDING_FILES = "recording_files"
ATTR_TUNER_COUNT = "tuner_count"
ATTR_RECORDING_TUNER_COUNT = "recording_tuner_count"
ATTR_LAST_UPDATE = "last_update"
