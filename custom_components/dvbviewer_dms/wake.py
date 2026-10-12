"""Persistent, testable scheduling state for the next DMS wake."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

try:
    from .api import DmsTimer
except ImportError:  # Support direct-module unit tests without importing HA.
    from api import DmsTimer


class AsyncStore(Protocol):
    async def async_load(self): ...
    async def async_save(self, data): ...
    async def async_remove(self): ...


@dataclass(frozen=True, slots=True)
class WakeSchedule:
    timer_id: str
    recording_start: datetime
    recording_end: datetime | None
    wake_at: datetime
    wake_advance_minutes: int

    def as_storage(self) -> dict[str, object]:
        return {
            "timer_id": self.timer_id,
            "recording_start": self.recording_start.isoformat(),
            "recording_end": self.recording_end.isoformat() if self.recording_end else None,
            "wake_at": self.wake_at.isoformat(),
            "wake_advance_minutes": self.wake_advance_minutes,
        }

    @classmethod
    def from_storage(cls, value: object) -> WakeSchedule | None:
        if not isinstance(value, dict):
            return None
        try:
            start = datetime.fromisoformat(str(value["recording_start"]))
            wake = datetime.fromisoformat(str(value["wake_at"]))
            end_value = value.get("recording_end")
            end = datetime.fromisoformat(str(end_value)) if end_value else None
            advance = int(value["wake_advance_minutes"])
            if start.tzinfo is None or wake.tzinfo is None or (end and end.tzinfo is None):
                return None
            return cls(str(value.get("timer_id", "")), start, end, wake, advance)
        except (KeyError, TypeError, ValueError, OverflowError):
            return None

    def with_advance(self, minutes: int) -> WakeSchedule:
        return WakeSchedule(
            self.timer_id,
            self.recording_start,
            self.recording_end,
            self.recording_start - timedelta(minutes=minutes),
            minutes,
        )


def next_future_timer(timers: list[DmsTimer], now: datetime) -> DmsTimer | None:
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    future = [timer for timer in timers if timer.start and timer.start > now]
    return min(future, key=lambda timer: timer.start) if future else None


class WakeScheduleManager:
    """Keep timer data independently available when the DMS coordinator fails."""

    def __init__(self, store: AsyncStore, advance_minutes: int) -> None:
        self.store = store
        self.advance_minutes = advance_minutes
        self.schedule: WakeSchedule | None = None
        self._listeners = set()

    async def async_restore(self) -> None:
        self.schedule = WakeSchedule.from_storage(await self.store.async_load())
        if self.schedule:
            self.schedule = self.schedule.with_advance(self.advance_minutes)
            await self._async_save()
        self._notify()

    async def async_update_from_timers(self, timers: list[DmsTimer], now: datetime) -> None:
        timer = next_future_timer(timers, now)
        if timer is None:
            self.schedule = None
            await self.store.async_remove()
        else:
            assert timer.start is not None
            self.schedule = WakeSchedule(
                timer.timer_id,
                timer.start,
                timer.end,
                timer.start - timedelta(minutes=self.advance_minutes),
                self.advance_minutes,
            )
            await self._async_save()
        self._notify()

    async def async_set_advance(self, minutes: int) -> None:
        self.advance_minutes = minutes
        if self.schedule:
            self.schedule = self.schedule.with_advance(minutes)
            await self._async_save()
        self._notify()

    def add_listener(self, listener) -> None:
        self._listeners.add(listener)

    def remove_listener(self, listener) -> None:
        self._listeners.discard(listener)

    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    async def _async_save(self) -> None:
        assert self.schedule is not None
        await self.store.async_save(self.schedule.as_storage())
