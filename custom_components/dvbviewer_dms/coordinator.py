from __future__ import annotations

from datetime import datetime, timezone
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DmsApi, DmsData, DmsApiError
from .const import CONF_PASSWORD, CONF_PORT, CONF_USERNAME, CONF_VIDEOREC_URL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)
MAX_RECORDINGS_TO_VERIFY_PER_UPDATE = 3


class DmsCoordinator(DataUpdateCoordinator[DmsData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.session = async_get_clientsession(hass)
        base_url = f"http://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"
        self.api = DmsApi(self.session, base_url, entry.data.get(CONF_USERNAME, ""), entry.data.get(CONF_PASSWORD, ""))
        self._verified_recordings: dict[str, dict[str, object]] = {}
        self._known_recording_ids: set[str] = set()
        self._pending_verification_ids: set[str] = set()
        self._archive_initialized = False
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=DEFAULT_SCAN_INTERVAL)

    async def _async_update_data(self) -> DmsData:
        try:
            data = await self.api.async_get_data()
            videorec_url = self.entry.options.get(CONF_VIDEOREC_URL, self.entry.data.get(CONF_VIDEOREC_URL, ""))
            if videorec_url:
                await self._verify_recordings(data, videorec_url)
            data.status["last_update"] = datetime.now(timezone.utc).isoformat()
            return data
        except DmsApiError as err:
            raise UpdateFailed(err) from err

    async def _verify_recordings(self, data: DmsData, videorec_url: str) -> None:
        """Verify only new/recent archive entries; VideoREC remains optional."""
        recordings_by_id = {
            str(item.get("id")): item
            for item in data.recordings
            if item.get("id") and item.get("file")
        }
        current_ids = set(recordings_by_id)
        new_ids = current_ids - self._known_recording_ids
        self._known_recording_ids = current_ids

        # At first startup consider only the latest archive item. Thereafter,
        # queue newly observed entries. This avoids ffprobe calls for a whole
        # historical archive while allowing a restart-time recovery check.
        if current_ids and not self._archive_initialized:
            candidate_ids = current_ids
            limit = 1
            self._archive_initialized = True
        else:
            candidate_ids = new_ids
            limit = MAX_RECORDINGS_TO_VERIFY_PER_UPDATE
        if candidate_ids:
            ordered_candidates = sorted(
                candidate_ids,
                key=lambda item_id: str(recordings_by_id[item_id].get("start", "")),
                reverse=True,
            )
            self._pending_verification_ids.update(ordered_candidates[:limit])

        self._pending_verification_ids.intersection_update(current_ids)
        candidates = [
            recordings_by_id[item_id]
            for item_id in sorted(
                self._pending_verification_ids,
                key=lambda pending_id: str(recordings_by_id[pending_id].get("start", "")),
                reverse=True,
            )[:MAX_RECORDINGS_TO_VERIFY_PER_UPDATE]
        ]
        results = await asyncio.gather(
            *(self.api.async_verify_recording(videorec_url, str(item["file"])) for item in candidates),
            return_exceptions=True,
        )
        for item, result in zip(candidates, results):
            key = str(item.get("id", item.get("file", "")))
            if isinstance(result, dict) and result.get("duration_source") == "ffprobe":
                self._verified_recordings[key] = result
                self._pending_verification_ids.discard(key)
            if key in self._verified_recordings:
                item.update(self._verified_recordings[key])

        # Re-apply retained successful checks when DMS or VideoREC is briefly
        # unavailable. An archive record alone is never a verified recording.
        for key, item in recordings_by_id.items():
            if key in self._verified_recordings:
                item.update(self._verified_recordings[key])
