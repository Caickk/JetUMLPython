"""Serviço de notificações temporárias (RF41, RF42). A UI apenas assina e desenha."""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Notification:
    kind: str          # "error" (vermelho) ou "success" (verde)
    message: str
    created_at: float
    duration: float

    def expired(self, now: float) -> bool:
        return now >= self.created_at + self.duration


class NotificationService:
    MIN_DURATION, MAX_DURATION, DEFAULT_DURATION = 0, 10, 5

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._duration = self.DEFAULT_DURATION
        self._items: list[Notification] = []
        self._listeners = []

    @property
    def duration(self) -> float:
        return self._duration

    @duration.setter
    def duration(self, value: float) -> None:
        if not self.MIN_DURATION <= value <= self.MAX_DURATION:
            raise ValueError("Notification duration must be between 0 and 10 seconds")
        self._duration = value

    def restore_default(self) -> None:
        self._duration = self.DEFAULT_DURATION

    def subscribe(self, callback) -> None:
        self._listeners.append(callback)

    def error(self, message: str):
        return self._post("error", message)

    def success(self, message: str):
        return self._post("success", message)

    def _post(self, kind: str, message: str):
        if self._duration == 0:  # 0 desativa todas as notificações
            return None
        item = Notification(kind, message, self._clock(), self._duration)
        self._items.append(item)
        for cb in list(self._listeners):
            cb(item)
        return item

    def active(self) -> list[Notification]:
        now = self._clock()
        self._items = [n for n in self._items if not n.expired(now)]
        return list(self._items)
