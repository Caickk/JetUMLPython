"""Zoom com dois níveis em cada direção (RF37)."""


class ZoomModel:
    MIN_LEVEL, MAX_LEVEL, STEP = -2, 2, 1.25

    def __init__(self):
        self.level = 0

    @property
    def factor(self) -> float:
        return self.STEP ** self.level

    def zoom_in(self) -> bool:
        if self.level >= self.MAX_LEVEL:
            return False
        self.level += 1
        return True

    def zoom_out(self) -> bool:
        if self.level <= self.MIN_LEVEL:
            return False
        self.level -= 1
        return True

    def reset(self) -> bool:
        changed = self.level != 0
        self.level = 0
        return changed
