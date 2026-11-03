"""Teste de estresse: milhares de gestos aleatórios (semente fixa) nos cinco tipos de diagrama.

Verifica, a cada passo, as invariantes do modelo e, ao final, que desfazer tudo volta ao estado inicial,
refazer tudo volta ao final, e que salvar/abrir em JSON preserva o diagrama.
"""
import json
import random
import tempfile
import unittest
from pathlib import Path

from jetuml_py.model.diagram import DiagramType as DT
from jetuml_py.persistence import diagram_to_dict, load, save
from jetuml_py.rendering.layout import apply_layout
from jetuml_py.tools import TOOLBARS
from tests.helpers import make_controller
from tests.invariants import check_consistency

STEPS = 350


def snap(d):
    return json.dumps(diagram_to_dict(d), sort_keys=True)


class Fuzzer:
    def __init__(self, dtype, seed):
        self.rnd = random.Random(seed)
        self.c = make_controller(dtype)
        self.tools = [t for t in TOOLBARS[dtype] if t.action != "clipboard"]
        self.clip = None

    def point(self):
        nodes = [n for n in self.c.diagram.all_nodes() if n.TYPE != "Point"]
        if nodes and self.rnd.random() < 0.65:
            n = self.rnd.choice(nodes)
            bottom = n.stem_end() if n.TYPE == "ImplicitParameter" else n.y + n.height
            return n.x + self.rnd.random() * max(n.width, 1), n.y + self.rnd.random() * max(bottom - n.y, 1)
        return self.rnd.random() * 900, self.rnd.random() * 650

    def sequence_gesture(self):
        """Dirigido: chamadas, construtores, autochamadas e retornos entre linhas de vida e caixas de ativação."""
        c, r = self.c, self.rnd
        d = c.diagram
        lifelines = [n for n in d.roots if n.TYPE == "ImplicitParameter"]
        boxes = [n for n in d.all_nodes() if n.TYPE == "Call"]
        if len(lifelines) < 2 or r.random() < 0.15:
            c.set_tool(next(t for t in self.tools if t.name == "Implicit Parameter"))
            c.press(r.randint(0, 800), r.randint(0, 60)); c.release(0, 0)
            return
        name = r.choice(["Call", "Call", "Call", "Return"])
        c.set_tool(next(t for t in self.tools if t.name == name))
        starts = boxes + lifelines if name == "Call" else (boxes or lifelines)
        ends = boxes + lifelines
        a, b = r.choice(starts), r.choice(ends)
        header = r.random() < 0.4
        ax, ay = a.x + a.width / 2, a.y + a.height / 2
        bx = b.x + b.width / 2
        by = b.y + (b.height / 2 if (header or b.TYPE == "Call") else b.height + 10)
        c.press(ax, ay)
        c.drag((ax + bx) / 2, (ay + by) / 2)
        c.drag(bx, by)
        c.release(bx, by)

    def gesture(self):
        c, r = self.c, self.rnd
        if c.diagram.type.value == "SequenceDiagram" and r.random() < 0.6:
            return self.sequence_gesture()
        c.set_tool(r.choice(self.tools))
        x1, y1 = self.point()
        x2, y2 = self.point()
        shift, ctrl = r.random() < 0.3, r.random() < 0.2
        c.press(x1, y1, ctrl=ctrl, shift=shift)
        for _ in range(r.randint(0, 2)):
            c.drag(*self.point())
        c.drag(x2, y2)
        if r.random() < 0.1:
            c.cancel()
        else:
            c.release(x2, y2, ctrl=ctrl, shift=shift)

    def edit(self):
        c, r, ed = self.c, self.rnd, self.c.editor
        action = r.choice(["delete", "all", "copy", "cut", "paste", "undo", "redo", "prop", "attach"])
        sel = c.selection
        sel.prune(c.diagram)
        if action == "delete":
            c.delete_selection()
        elif action == "all":
            c.select_all()
        elif action == "copy":
            self.clip = ed.copy_elements(sel.nodes, sel.edges) or self.clip
        elif action == "cut":
            self.clip = ed.cut_elements(sel.nodes, sel.edges) or self.clip
            sel.clear()
        elif action == "paste" and self.clip:
            res = ed.paste(self.clip, 20, 20)
            if res:
                sel.set(*res)
        elif action == "undo":
            ed.undo()
        elif action == "redo":
            ed.redo()
        elif action == "prop":
            nodes = [n for n in c.diagram.all_nodes() if "name" in n.props]
            if nodes:
                ed.set_property(r.choice(nodes), "name", r.choice(["A", "/B/", "_c_", "«x»", ""]))
        elif action == "attach":
            pkgs = [n for n in c.diagram.all_nodes() if n.TYPE == "Package"]
            others = [n for n in c.diagram.all_nodes() if n.TYPE in ("Class", "Interface", "Note", "Package")]
            if pkgs and others:
                ed.attach(r.choice(others), r.choice(pkgs)) if r.random() < 0.6 else ed.detach(r.choice(others))

    def run(self, steps):
        for i in range(steps):
            self.gesture() if self.rnd.random() < 0.75 else self.edit()
            problems = check_consistency(self.c.diagram)
            assert not problems, f"step {i}: {problems}"
            if i % 40 == 0:
                apply_layout(self.c.diagram)
                before = snap(self.c.diagram)
                apply_layout(self.c.diagram)
                assert snap(self.c.diagram) == before, "layout is not idempotent"


class StressTests(unittest.TestCase):
    def check_type(self, dtype, seeds=(1, 2, 3, 4, 5)):
        for seed in seeds:
            with self.subTest(dtype=dtype.name, seed=seed):
                f = Fuzzer(dtype, seed)
                initial = snap(f.c.diagram)
                f.run(STEPS)
                while f.c.editor.redo():       # comandos desfeitos durante a execução aleatória ainda estão na pilha
                    pass
                final = snap(f.c.diagram)
                # salvar/abrir preserva
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "d.json"
                    save(f.c.diagram, path)
                    self.assertEqual(snap(load(path)), final)
                # desfazer tudo volta ao início; refazer tudo volta ao fim
                while f.c.editor.undo():
                    pass
                self.assertEqual(snap(f.c.diagram), initial)
                self.assertEqual(check_consistency(f.c.diagram), [])
                while f.c.editor.redo():
                    pass
                self.assertEqual(snap(f.c.diagram), final)

    def test_class(self):
        self.check_type(DT.CLASS)

    def test_sequence(self):
        self.check_type(DT.SEQUENCE, seeds=range(1, 13))   # o mais delicado: mais sementes

    def test_state(self):
        self.check_type(DT.STATE)

    def test_object(self):
        self.check_type(DT.OBJECT)

    def test_use_case(self):
        self.check_type(DT.USE_CASE)


if __name__ == "__main__":
    unittest.main()
