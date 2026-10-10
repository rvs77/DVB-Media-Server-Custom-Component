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
CONF_VIDEOREC_URL = "videorec_url"
DEFAULT_VIDEOREC_URL = ""

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
