import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "dvbviewer_dms"))

from api import DmsApi, parse_channels, parse_recordings, parse_status, parse_timers, parse_version, public_recording


def test_parse_status():
    data = parse_status(b"<status><reccount>1</reccount><recfiles>188</recfiles></status>")
    assert data["reccount"] == "1"
    assert data["recfiles"] == "188"


def test_parse_timer_and_channel():
    payload = b"""
    <Timers>
      <Timer IntID="8" Date="06.09.2026" Start="00:40:00" End="02:00:00" Dur="80">
        <Descr>Test title</Descr>
        <Channel ID="123|Rai Storia HD" />
        <Recording>1</Recording>
      </Timer>
    </Timers>
    """
    timers = parse_timers(payload)
    assert len(timers) == 1
    assert timers[0].timer_id == "8"
    assert timers[0].channel == "Rai Storia HD"
    assert timers[0].recording is True
    assert timers[0].duration_minutes == 80
    assert str(timers[0].start.tzinfo) == "Europe/Rome"


def test_timer_crossing_midnight_has_next_day_end_and_tolerates_bad_duration():
    timers = parse_timers(b'''
    <Timers><Timer IntID="9" Date="06.09.2026" Start="23:45:00" End="00:15:00" Dur="unknown">
    <Descr>Late programme</Descr><Channel ID="9|TV" /><Recording>0</Recording>
    </Timer></Timers>''')
    assert timers[0].end.date().isoformat() == "2026-09-07"
    assert timers[0].duration_minutes is None


def test_parse_recordings():
    payload = b"""
    <recordings Ver="1"><serverURL>http://example:8090/upnp/recordings/</serverURL>
      <recording id="188" start="20260905174001" duration="000300">
        <channel>Rai 2 HD</channel><file>C:\\captures\\test.ts</file><title>Test</title>
        <info>Info</info><desc>Description</desc>
      </recording>
    </recordings>
    """
    recordings, server_url = parse_recordings(payload)
    assert server_url.endswith("/upnp/recordings/")
    assert recordings[0]["id"] == "188"
    assert recordings[0]["channel"] == "Rai 2 HD"
    assert recordings[0]["title"] == "Test"


def test_public_recording_excludes_private_fields():
    recording = {
        "id": "1", "start": "20260101", "duration": "60", "lastmodified": "x",
        "channel": "TV", "title": "News", "file": "C:\\Private\\News.ts",
        "info": "Details", "description": "Long description",
    }
    assert public_recording(recording) == {
        "id": "1", "start": "20260101", "duration": "60", "lastmodified": "x",
        "channel": "TV", "title": "News",
    }


def test_parse_channels_including_subchannels():
    assert parse_channels(b'<channels><channel /><channel><subchannel /></channel></channels>') == 3


def test_parse_version():
    assert parse_version(b'<version iver="1">DVBViewer Media Server 3.3.2.0</version>') == "DVBViewer Media Server 3.3.2.0"
