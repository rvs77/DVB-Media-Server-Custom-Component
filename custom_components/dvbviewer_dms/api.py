from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from pathlib import PureWindowsPath
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import aiohttp
import asyncio

LOCAL_TIMEZONE = ZoneInfo("Europe/Rome")


class DmsApiError(Exception):
    """Raised when DMS cannot be queried or returns invalid XML."""


@dataclass(slots=True)
class DmsTimer:
    timer_id: str
    title: str
    channel: str
    start: datetime | None
    end: datetime | None
    duration_minutes: float | None
    recording: bool
    raw: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        """Return timer metadata intended for the Home Assistant UI."""
        return {
            "id": self.timer_id, "title": self.title, "channel": self.channel,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "duration_minutes": self.duration_minutes, "recording": self.recording,
        }


@dataclass(slots=True)
class DmsData:
    status: dict[str, object]
    timers: list[DmsTimer]
    version: str
    channels: int | None
    recordings: list[dict[str, object]]
    recordings_server_url: str | None


def _text(node: ET.Element, name: str, default: str = "") -> str:
    child = node.find(name)
    return (child.text or default).strip() if child is not None else default


def _parse_datetime(day: str, clock: str) -> datetime | None:
    if not day or not clock:
        return None
    try:
        return datetime.strptime(f"{day} {clock}", "%d.%m.%Y %H:%M:%S").replace(tzinfo=LOCAL_TIMEZONE)
    except ValueError:
        return None


def _parse_duration_minutes(value: str | None) -> float | None:
    """Parse DMS duration as non-authoritative metadata only."""
    try:
        return float(value) if value else None
    except ValueError:
        return None


def parse_timers(payload: bytes) -> list[DmsTimer]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as err:
        raise DmsApiError("DMS returned invalid timer XML") from err

    result: list[DmsTimer] = []
    for node in root.findall("Timer"):
        channel = node.find("Channel")
        channel_id = channel.attrib.get("ID", "") if channel is not None else ""
        channel_name = channel_id.split("|", 1)[1] if "|" in channel_id else channel_id
        start = _parse_datetime(node.attrib.get("Date", ""), node.attrib.get("Start", ""))
        end = _parse_datetime(node.attrib.get("Date", ""), node.attrib.get("End", ""))
        if start and end and end <= start:
            end += timedelta(days=1)
        result.append(
            DmsTimer(
                timer_id=node.attrib.get("IntID") or node.attrib.get("ID", ""),
                title=_text(node, "Title") or _text(node, "Descr"),
                channel=channel_name,
                start=start,
                end=end,
                duration_minutes=_parse_duration_minutes(node.attrib.get("Dur")),
                recording=node.findtext("Recording", "0") not in {"", "0", "false", "False"},
                raw={**node.attrib, "description": _text(node, "Descr")},
            )
        )
    return result


def parse_status(payload: bytes) -> dict[str, object]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as err:
        raise DmsApiError("DMS returned invalid status XML") from err
    data: dict[str, object] = {}
    for child in root:
        if child.tag == "recfolders":
            data[child.tag] = [dict(folder.attrib) for folder in child.findall("folder")]
        else:
            data[child.tag] = (child.text or "").strip()
    return data


def parse_recordings(payload: bytes) -> tuple[list[dict[str, object]], str | None]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as err:
        raise DmsApiError("DMS returned invalid recordings XML") from err
    recordings = []
    for node in root.findall("recording"):
        recordings.append(
            {
                "id": node.attrib.get("id", ""),
                "start": node.attrib.get("start", ""),
                "duration": node.attrib.get("duration", ""),
                "lastmodified": node.attrib.get("lastmodified", ""),
                "channel": _text(node, "channel"),
                "file": _text(node, "file"),
                "title": _text(node, "title"),
                "info": _text(node, "info"),
                "description": _text(node, "desc"),
            }
        )
    return recordings, root.findtext("serverURL")


def parse_channels(payload: bytes) -> int:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as err:
        raise DmsApiError("DMS returned invalid channels XML") from err
    return len(root.findall(".//channel")) + len(root.findall(".//subchannel"))


def public_recording(recording: dict[str, object]) -> dict[str, object]:
    """Return archive metadata without local paths or extended programme text."""
    result = {key: recording.get(key, "") for key in ("id", "start", "duration", "lastmodified", "channel", "title")}
    for key in ("verified_duration_seconds", "duration_source"):
        if key in recording:
            result[key] = recording[key]
    return result


def recording_file_name(value: object) -> str | None:
    """Return only a plain Windows file name from a DMS archive value."""
    if not isinstance(value, str) or not value.strip():
        return None
    name = PureWindowsPath(value.replace("/", "\\")).name
    if not name or name in {".", ".."} or any(ord(char) < 32 for char in name):
        return None
    return name


def verified_duration(payload: object, expected_file_name: str) -> float | None:
    """Accept only a complete, self-consistent ffprobe verification response."""
    if not isinstance(payload, dict):
        return None
    if payload.get("available") is not True or payload.get("durationSource") != "ffprobe":
        return None
    if payload.get("fileName") != expected_file_name:
        return None
    duration = payload.get("verifiedDurationSeconds")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        return None
    duration = float(duration)
    return duration if isfinite(duration) and duration > 0 else None


def parse_version(payload: bytes) -> str:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as err:
        raise DmsApiError("DMS returned invalid version XML") from err
    return (root.text or "").strip()


class DmsApi:
    def __init__(self, session: aiohttp.ClientSession, base_url: str, username: str = "", password: str = "") -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._auth = aiohttp.BasicAuth(username, password) if username else None

    async def _get(self, path: str, params: dict[str, str] | None = None) -> bytes:
        try:
            async with self._session.get(path, params=params, auth=self._auth, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                return await response.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise DmsApiError(str(err)) from err

    async def async_verify_recording(self, videorec_url: str, file_name: str) -> dict[str, object] | None:
        """Ask VideoREC for ffprobe metadata without making it a DMS dependency."""
        safe_name = recording_file_name(file_name)
        if not videorec_url or safe_name is None:
            return None
        try:
            async with self._session.get(
                f"{videorec_url.rstrip('/')}/api/v1/recordings/verify",
                params={"fileName": safe_name},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                payload = await response.json()
                duration = verified_duration(payload, safe_name)
                return (
                    {"verified_duration_seconds": duration, "duration_source": "ffprobe"}
                    if duration is not None
                    else None
                )
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            return None

    async def async_get_data(self) -> DmsData:
        status_payload, timer_payload, version_payload, recordings_payload, channels_payload = await asyncio.gather(
            self._get(f"{self._base_url}/api/status2.html"),
            self._get(f"{self._base_url}/api/timerlist.html", {"utf8": "2"}),
            self._get(f"{self._base_url}/api/version.html"),
            self._get(f"{self._base_url}/api/recordings.html"),
            self._get(f"{self._base_url}/api/getchannelsxml.html", {"subchannels": "1"}),
        )
        status = parse_status(status_payload)
        timers = parse_timers(timer_payload)
        recordings, recordings_server_url = parse_recordings(recordings_payload)
        return DmsData(status, timers, parse_version(version_payload), parse_channels(channels_payload), recordings, recordings_server_url)
