from jetuml_py.editor import DiagramEditor
from jetuml_py.model.diagram import Diagram, DiagramType
from jetuml_py.tools import tool_by_name


def make_editor(dtype: DiagramType) -> DiagramEditor:
    return DiagramEditor(Diagram(dtype))


def tool(ed: DiagramEditor, name: str):
    return tool_by_name(ed.diagram.type, name)


def errors(ed: DiagramEditor) -> int:
    return len(ed.notifier.active())


def make_controller(dtype):
    from jetuml_py.app.workspace import Document
    from jetuml_py.interaction import InteractionController
    from jetuml_py.model.diagram import Diagram
    from jetuml_py.notifications import NotificationService
    doc = Document(Diagram(dtype), NotificationService())
    return InteractionController(doc)


def use(c, name):
    c.set_tool(tool_by_name(c.diagram.type, name))


def click(c, x, y, **kw):
    c.press(x, y, **kw)
    c.release(x, y, **kw)


def drag(c, x1, y1, x2, y2, shift=False, ctrl=False):
    c.press(x1, y1, ctrl=ctrl)
    c.drag((x1 + x2) / 2, (y1 + y2) / 2)
    c.drag(x2, y2)
    c.release(x2, y2, shift=shift, ctrl=ctrl)
