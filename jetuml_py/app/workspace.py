"""Documentos abertos e operações de arquivo (RF01–RF03). Independente de Tk, portanto testável."""
from __future__ import annotations

import os

from ..editor import DiagramEditor
from ..model.diagram import Diagram, DiagramType
from ..notifications import NotificationService
from ..persistence import DiagramFormatError, create_diagram, duplicate, load, save
from .settings import Settings
from .zoom import ZoomModel

_UNSAVED = object()  # marcador: documento nunca salvo, mas com conteúdo (ex.: duplicata)


class Document:
    def __init__(self, diagram: Diagram, notifier: NotificationService, path=None,
                 untitled: str = "Untitled", unsaved_content: bool = False):
        self.diagram = diagram
        self.editor = DiagramEditor(diagram, notifier)
        self.path = path
        self.untitled = untitled
        self.zoom = ZoomModel()
        self._saved_top = _UNSAVED if unsaved_content else None

    @property
    def title(self) -> str:
        return os.path.basename(self.path) if self.path else self.untitled

    @property
    def dirty(self) -> bool:
        """Alterações desde o último salvamento (desfazer até o ponto salvo volta a 'limpo')."""
        return self.editor.undo_manager.top is not self._saved_top

    def mark_saved(self) -> None:
        self._saved_top = self.editor.undo_manager.top


class Workspace:
    def __init__(self, settings: Settings, notifier: NotificationService | None = None):
        self.settings = settings
        self.notifier = notifier or NotificationService()
        self.documents: list[Document] = []
        self.active: Document | None = None
        self.last_error = ""
        self._counter = 0
        self._listeners = []

    def subscribe(self, callback) -> None:
        self._listeners.append(callback)

    def _fire(self, event: str, doc: Document | None) -> None:
        for cb in list(self._listeners):
            cb(event, doc)

    def _fail(self, message: str):
        self.last_error = message
        self.notifier.error(message)

    def _add(self, doc: Document) -> Document:
        self.documents.append(doc)
        self.active = doc
        self._fire("opened", doc)
        return doc

    # ---------------------------------------------------------------- RF01
    def new(self, dtype: DiagramType) -> Document:
        self._counter += 1
        return self._add(Document(create_diagram(dtype), self.notifier, untitled=f"Untitled {self._counter}"))

    # ---------------------------------------------------------------- RF02
    def open(self, path) -> Document | None:
        path = os.path.abspath(path)
        existing = next((d for d in self.documents if d.path == path), None)
        if existing:
            self.activate(existing)
            return existing
        try:
            diagram = load(path)
        except (DiagramFormatError, OSError) as exc:
            self.settings.remove_recent(path)
            self._fail(f"Cannot open {os.path.basename(path)}: {exc}")
            return None
        self.settings.add_recent(path)
        return self._add(Document(diagram, self.notifier, path=path))

    def save(self, doc: Document) -> bool:
        if doc.path is None:
            raise ValueError("Document has no path; use save_as")
        try:
            save(doc.diagram, doc.path)
        except OSError as exc:
            self._fail(f"Cannot save {doc.title}: {exc}")
            return False
        doc.mark_saved()
        self.settings.add_recent(doc.path)
        self.notifier.success(f"Saved {doc.title}")
        self._fire("saved", doc)
        return True

    def save_as(self, doc: Document, path) -> bool:
        path = os.path.abspath(path)
        if not os.path.splitext(path)[1]:
            path += ".json"
        previous, doc.path = doc.path, path
        if not self.save(doc):
            doc.path = previous
            return False
        return True

    def close(self, doc: Document, force: bool = False) -> bool:
        """Retorna False (sem fechar) se houver alterações não salvas e force=False."""
        if doc.dirty and not force:
            return False
        index = self.documents.index(doc)
        self.documents.remove(doc)
        if self.active is doc:
            self.active = self.documents[min(index, len(self.documents) - 1)] if self.documents else None
        self._fire("closed", doc)
        return True

    # ---------------------------------------------------------------- RF03
    def duplicate(self, doc: Document) -> Document:
        self._counter += 1
        copy = Document(duplicate(doc.diagram), self.notifier, untitled=f"Copy of {doc.title}",
                        unsaved_content=True)
        return self._add(copy)

    def activate(self, doc: Document) -> None:
        if doc is not self.active:
            self.active = doc
            self._fire("activated", doc)
