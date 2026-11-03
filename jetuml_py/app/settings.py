"""Preferências do usuário persistidas em JSON (arquivos recentes, modo escuro, grade)."""
from __future__ import annotations

import json
import os
from pathlib import Path

MAX_RECENT = 10


def default_config_path() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "JetUMLPy" / "settings.json"


class Settings:
    DEFAULT_FONT = ("Helvetica", 12)
    DEFAULTS = {"recent_files": [], "dark_mode": False, "show_grid": True,
                "show_tool_hint": False, "verbose_tooltips": False, "auto_edit_node": False,
                "notification_duration": 5, "diagram_width": None, "diagram_height": None,
                "font_family": "Helvetica", "font_size": 12}

    def __init__(self, path=None):
        self.path = Path(path) if path else default_config_path()
        self._data = dict(self.DEFAULTS)
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self._data.update({k: v for k, v in loaded.items() if k in self.DEFAULTS})
        except (OSError, json.JSONDecodeError):
            pass  # primeira execução ou arquivo corrompido: usa os padrões
        if not isinstance(self._data["recent_files"], list):
            self._data["recent_files"] = []

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except OSError:
            pass  # preferências são best-effort

    @property
    def recent_files(self) -> list[str]:
        return list(self._data["recent_files"])

    def add_recent(self, path) -> None:
        p = os.path.abspath(path)
        files = [f for f in self._data["recent_files"] if f != p]
        self._data["recent_files"] = ([p] + files)[:MAX_RECENT]
        self._save()

    def remove_recent(self, path) -> None:
        p = os.path.abspath(path)
        self._data["recent_files"] = [f for f in self._data["recent_files"] if f != p]
        self._save()

    @property
    def dark_mode(self) -> bool:
        return bool(self._data["dark_mode"])

    @dark_mode.setter
    def dark_mode(self, value: bool) -> None:
        self._data["dark_mode"] = bool(value)
        self._save()

    @property
    def show_grid(self) -> bool:
        return bool(self._data["show_grid"])

    @show_grid.setter
    def show_grid(self, value: bool) -> None:
        self._data["show_grid"] = bool(value)
        self._save()

    @property
    def show_tool_hint(self) -> bool:
        return bool(self._data["show_tool_hint"])

    @show_tool_hint.setter
    def show_tool_hint(self, value: bool) -> None:
        self._data["show_tool_hint"] = bool(value)
        self._save()

    @property
    def verbose_tooltips(self) -> bool:
        return bool(self._data["verbose_tooltips"])

    @verbose_tooltips.setter
    def verbose_tooltips(self, value: bool) -> None:
        self._data["verbose_tooltips"] = bool(value)
        self._save()

    @property
    def auto_edit_node(self) -> bool:
        return bool(self._data["auto_edit_node"])

    @auto_edit_node.setter
    def auto_edit_node(self, value: bool) -> None:
        self._data["auto_edit_node"] = bool(value)
        self._save()

    @property
    def notification_duration(self) -> float:
        value = self._data["notification_duration"]
        return value if isinstance(value, (int, float)) and 0 <= value <= 10 else 5

    @notification_duration.setter
    def notification_duration(self, value: float) -> None:
        if not 0 <= value <= 10:
            raise ValueError("Notification duration must be between 0 and 10 seconds")
        self._data["notification_duration"] = value
        self._save()

    @property
    def diagram_size(self):
        """(largura, altura) configuradas, ou None para usar o padrão relativo à tela."""
        w, h = self._data["diagram_width"], self._data["diagram_height"]
        ok = all(isinstance(v, int) and 250 <= v <= 4000 for v in (w, h))
        return (w, h) if ok else None

    @diagram_size.setter
    def diagram_size(self, size) -> None:
        if size is None:
            self._data["diagram_width"] = self._data["diagram_height"] = None
        else:
            w, h = size
            if not all(isinstance(v, int) and 250 <= v <= 4000 for v in (w, h)):
                raise ValueError("Diagram size must be between 250 and 4000 pixels")
            self._data["diagram_width"], self._data["diagram_height"] = w, h
        self._save()

    @property
    def font(self) -> tuple[str, int]:
        family, size = self._data["font_family"], self._data["font_size"]
        return (family if isinstance(family, str) and family else "Helvetica",
                size if isinstance(size, int) and 6 <= size <= 48 else 12)

    @font.setter
    def font(self, value) -> None:
        family, size = value
        if not isinstance(family, str) or not family or not isinstance(size, int) or not 6 <= size <= 48:
            raise ValueError("Invalid font")
        self._data["font_family"], self._data["font_size"] = family, size
        self._save()
