import unittest

from jetuml_py.app.properties import PropertiesModel, fields_for, insert_stereotype
from jetuml_py.model.diagram import DiagramType as DT
from jetuml_py.model.nodes import create_node
from tests.helpers import errors, make_editor, tool


def names(element):
    return [f.name for f in fields_for(element)]


class NodeFields(unittest.TestCase):
    def test_fields_match_annex_for_every_node_type(self):
        expected = {
            "Class": ["name", "attributes", "methods"], "Interface": ["name", "methods"],
            "Package": ["name"], "PackageDescription": ["name", "contents"], "Object": ["name"],
            "Field": ["name", "value"], "Actor": ["name"], "UseCase": ["name"], "State": ["name"],
            "InitialState": [], "FinalState": [], "ImplicitParameter": ["name"],
            "Call": ["open_bottom"], "Note": ["text"],
        }
        for type_name, fields in expected.items():
            self.assertEqual(names(create_node(type_name)), fields, type_name)

    def test_kinds_and_labels(self):
        by = {f.name: f for f in fields_for(create_node("Class"))}
        self.assertEqual((by["name"].kind, by["attributes"].kind, by["methods"].kind), ("line", "text", "text"))
        call = fields_for(create_node("Call"))[0]
        self.assertEqual((call.kind, call.label), ("bool", "Open Bottom"))
        self.assertEqual(fields_for(create_node("Note"))[0].kind, "text")


class EdgeFields(unittest.TestCase):
    def setUp(self):
        self.ed = make_editor(DT.CLASS)
        self.a, self.b = self.ed.add_node("Class", 0, 0), self.ed.add_node("Class", 300, 0)

    def test_class_diagram_edges(self):
        assoc = self.ed.connect(tool(self.ed, "Association"), self.a, self.b)
        self.assertEqual(names(assoc), ["start_label", "middle_label", "end_label", "directionality"])
        self.assertEqual(fields_for(assoc)[3].choices, ("Unspecified", "Unidirectional", "Bidirectional"))
        c = self.ed.add_node("Class", 600, 0)
        comp = self.ed.connect(tool(self.ed, "Composition"), c, self.a)   # (Associação + Agregação entre o mesmo par é proibido)
        self.assertEqual(names(comp)[-2:], ["directionality", "aggregation_type"])
        self.assertEqual(fields_for(comp)[-1].choices, ("Aggregation", "Composition"))
        real = self.ed.connect(tool(self.ed, "Realization"), self.a, self.b)
        self.assertEqual(names(real), ["generalization_type", "directionality"])
        self.assertEqual(fields_for(real)[1].choices, ("Unidirectional", "Bidirectional"))

    def test_other_diagram_edges(self):
        def edge(dtype, nodes, tool_name):
            ed = make_editor(dtype)
            made = [ed.add_node(t, i * 250, 0) for i, t in enumerate(nodes)]
            return ed.connect(tool(ed, tool_name), made[0], made[1])
        self.assertEqual(names(edge(DT.STATE, ["State", "State"], "Transition")), ["middle_label"])
        self.assertEqual(names(edge(DT.OBJECT, ["Object", "Object"], "Collaboration")), ["middle_label"])
        self.assertEqual(names(edge(DT.USE_CASE, ["UseCase", "UseCase"], "Include")), ["dependency_type"])
        self.assertEqual(fields_for(edge(DT.USE_CASE, ["UseCase", "UseCase"], "Include"))[0].choices,
                         ("None", "Include", "Extend"))
        self.assertEqual(names(edge(DT.USE_CASE, ["Actor", "UseCase"], "Association")), [])
        ed = make_editor(DT.SEQUENCE)
        l1, l2 = ed.add_node("ImplicitParameter", 0, 0), ed.add_node("ImplicitParameter", 200, 0)
        call = ed.add_call(l1, l2)
        self.assertEqual(names(call), ["middle_label"])
        ret = ed.connect(tool(ed, "Return"), call.end, call.start)
        self.assertEqual(names(ret), ["middle_label"])


class Commit(unittest.TestCase):
    def test_commit_applies_only_changes_in_one_undo_step(self):
        ed = make_editor(DT.CLASS)
        c = ed.add_node("Class", 0, 0)
        model = PropertiesModel(ed, c)
        self.assertFalse(model.commit(model.values()))                       # nada mudou
        self.assertTrue(model.commit({**model.values(), "name": "A", "methods": "run()"}))
        self.assertEqual((c.props["name"], c.props["methods"]), ("A", "run()"))
        self.assertTrue(ed.undo())
        self.assertEqual((c.props["name"], c.props["methods"]), ("", ""))   # um passo só

    def test_swap_composition_for_aggregation_without_recreating(self):
        ed = make_editor(DT.CLASS)
        a, b = ed.add_node("Class", 0, 0), ed.add_node("Class", 300, 0)
        e = ed.connect(tool(ed, "Composition"), a, b)
        ident = e.id
        PropertiesModel(ed, e).commit({"aggregation_type": "Aggregation", "end_label": "*"})
        self.assertEqual((e.id, e.props["aggregation_type"], e.props["end_label"]), (ident, "Aggregation", "*"))
        self.assertEqual(len(ed.diagram.edges), 1)

    def test_invalid_value_rejected_and_reported(self):
        ed = make_editor(DT.CLASS)
        a, b = ed.add_node("Class", 0, 0), ed.add_node("Class", 300, 0)
        e = ed.connect(tool(ed, "Association"), a, b)
        before = errors(ed)
        self.assertFalse(PropertiesModel(ed, e).commit({"directionality": "Sideways"}))
        self.assertEqual(e.props["directionality"], "Unspecified")
        self.assertEqual(errors(ed), before + 1)

    def test_open_bottom_is_boolean(self):
        ed = make_editor(DT.SEQUENCE)
        l1, l2 = ed.add_node("ImplicitParameter", 0, 0), ed.add_node("ImplicitParameter", 200, 0)
        box = ed.add_call(l1, l2).end
        self.assertTrue(PropertiesModel(ed, box).commit({"open_bottom": True}))
        self.assertIs(box.props["open_bottom"], True)
        self.assertFalse(PropertiesModel(ed, box).commit({"open_bottom": "yes"}))


class Stereotype(unittest.TestCase):
    def test_insert_places_cursor_between_delimiters(self):
        self.assertEqual(insert_stereotype("", 0), ("«»", 1))
        text, cur = insert_stereotype("Foo", 3)
        self.assertEqual((text, cur), ("Foo«»", 4))
        self.assertEqual(insert_stereotype("ab", 1), ("a«»b", 2))


if __name__ == "__main__":
    unittest.main()
