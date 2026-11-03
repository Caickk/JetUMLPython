import unittest

from jetuml_py.model.diagram import DiagramType as DT
from tests.helpers import errors, make_editor, tool


class ClassDiagramRules(unittest.TestCase):
    def setUp(self):
        self.ed = make_editor(DT.CLASS)
        self.a = self.ed.add_node("Class", 0, 0)
        self.b = self.ed.add_node("Class", 300, 0)

    def test_duplicate_edge_rejected_with_notification(self):
        self.assertIsNotNone(self.ed.connect(tool(self.ed, "Association"), self.a, self.b))
        self.assertIsNone(self.ed.connect(tool(self.ed, "Association"), self.a, self.b))
        self.assertEqual(errors(self.ed), 1)

    def test_back_and_forth_rejected_for_inheritance_dependency_aggregation_association(self):
        for name in ("Inheritance", "Dependency", "Aggregation"):
            ed = make_editor(DT.CLASS)
            a, b = ed.add_node("Class", 0, 0), ed.add_node("Class", 300, 0)
            self.assertIsNotNone(ed.connect(tool(ed, name), a, b), name)
            self.assertIsNone(ed.connect(tool(ed, name), b, a), name)
            self.assertEqual(errors(ed), 1, name)

    def test_association_and_aggregation_cannot_be_combined(self):
        self.ed.connect(tool(self.ed, "Association"), self.a, self.b)
        self.assertIsNone(self.ed.connect(tool(self.ed, "Aggregation"), self.b, self.a))
        self.assertEqual(errors(self.ed), 1)

    def test_self_inheritance_and_self_dependency_blocked_but_self_association_allowed(self):
        self.assertIsNone(self.ed.connect(tool(self.ed, "Inheritance"), self.a, self.a))
        self.assertIsNone(self.ed.connect(tool(self.ed, "Dependency"), self.a, self.a))
        self.assertEqual(errors(self.ed), 2)
        self.assertIsNotNone(self.ed.connect(tool(self.ed, "Association"), self.a, self.a))

    def test_inheritance_and_realization_are_same_kind_with_type(self):
        e = self.ed.connect(tool(self.ed, "Realization"), self.a, self.b)
        self.assertEqual(e.props["generalization_type"], "Implementation")

    def test_invalid_endpoints(self):
        note = self.ed.add_node("Note", 0, 200)
        self.assertIsNone(self.ed.connect(tool(self.ed, "Association"), self.a, note))
        self.assertEqual(errors(self.ed), 1)

    def test_node_type_not_allowed_in_diagram(self):
        self.assertIsNone(self.ed.add_node("Actor", 0, 0))
        self.assertEqual(errors(self.ed), 1)


class NoteConnectorRules(unittest.TestCase):
    def test_connect_node_to_note_and_anchor_from_note(self):
        ed = make_editor(DT.STATE)
        s, n = ed.add_node("State", 0, 0), ed.add_node("Note", 200, 0)
        self.assertIsNotNone(ed.connect(tool(ed, "Note Connector"), s, n))
        anchor = ed.anchor_note(n, 400, 300)
        self.assertEqual(anchor.end.TYPE, "Point")
        self.assertIsNone(ed.connect(tool(ed, "Note Connector"), n, s))  # nota -> nó não é permitido


class ObjectDiagramRules(unittest.TestCase):
    def setUp(self):
        self.ed = make_editor(DT.OBJECT)
        self.o1 = self.ed.add_node("Object", 10, 10)
        self.o2 = self.ed.add_node("Object", 300, 10)

    def test_field_only_inside_object(self):
        self.assertIsNone(self.ed.add_node("Field", 700, 700))
        self.assertEqual(errors(self.ed), 1)
        f = self.ed.add_node("Field", 20, 20)
        self.assertIs(f.parent, self.o1)

    def test_collaboration_cycle_and_self_blocked(self):
        c = tool(self.ed, "Collaboration")
        self.assertIsNotNone(self.ed.connect(c, self.o1, self.o2))
        self.assertIsNone(self.ed.connect(c, self.o2, self.o1))
        self.assertIsNone(self.ed.connect(c, self.o1, self.o1))
        self.assertEqual(errors(self.ed), 2)

    def test_reference_goes_from_field_to_object(self):
        f = self.ed.add_node("Field", 20, 20)
        self.assertIsNotNone(self.ed.connect(tool(self.ed, "Reference"), f, self.o2))
        self.assertIsNone(self.ed.connect(tool(self.ed, "Reference"), self.o1, self.o2))


class UseCaseRules(unittest.TestCase):
    def test_rules(self):
        ed = make_editor(DT.USE_CASE)
        actor, uc1, uc2 = ed.add_node("Actor", 0, 0), ed.add_node("UseCase", 200, 0), ed.add_node("UseCase", 400, 0)
        for name in ("Association", "Include", "Extend", "Generalization"):
            self.assertIsNone(ed.connect(tool(ed, name), uc1, uc1), name)
        self.assertEqual(errors(ed), 4)
        inc = ed.connect(tool(ed, "Include"), uc1, uc2)
        self.assertEqual(inc.props["dependency_type"], "Include")
        ed.set_property(inc, "dependency_type", "Extend")
        self.assertEqual(inc.props["dependency_type"], "Extend")
        self.assertIsNone(ed.connect(tool(ed, "Include"), actor, uc1))


class StateRules(unittest.TestCase):
    def test_transition_limits(self):
        ed = make_editor(DT.STATE)
        s1, s2 = ed.add_node("State", 0, 0), ed.add_node("State", 300, 0)
        ini, fin = ed.add_node("InitialState", 0, 200), ed.add_node("FinalState", 300, 200)
        t = tool(ed, "Transition")
        self.assertIsNotNone(ed.connect(t, ini, s1))
        self.assertIsNotNone(ed.connect(t, s2, fin))
        self.assertIsNone(ed.connect(t, fin, s1))
        self.assertIsNone(ed.connect(t, s1, ini))
        self.assertEqual(errors(ed), 2)
        for _ in range(2):
            self.assertIsNotNone(ed.connect(t, s1, s1))
        self.assertIsNone(ed.connect(t, s1, s1))
        for _ in range(2):
            self.assertIsNotNone(ed.connect(t, s1, s2))
        self.assertIsNone(ed.connect(t, s1, s2))
        for _ in range(2):
            self.assertIsNotNone(ed.connect(t, s2, s1))
        self.assertIsNone(ed.connect(t, s2, s1))


class SequenceRules(unittest.TestCase):
    def setUp(self):
        self.ed = make_editor(DT.SEQUENCE)
        self.l1, self.l2, self.l3, self.l4 = (self.ed.add_node("ImplicitParameter", x, 0) for x in (0, 200, 400, 600))
        self.call, self.ret = tool(self.ed, "Call"), tool(self.ed, "Return")

    def test_first_call_creates_both_boxes_and_second_root_is_rejected(self):
        e1 = self.ed.connect(self.call, self.l1, self.l2)
        self.assertIs(e1.start.parent, self.l1)
        self.assertIs(e1.end.parent, self.l2)
        self.assertIsNone(self.ed.connect(self.call, self.l3, self.l4))
        self.assertEqual(errors(self.ed), 1)

    def test_control_flow_jump_fails_silently_and_valid_flow_works(self):
        e1 = self.ed.connect(self.call, self.l1, self.l2)
        b1, b2 = e1.start, e1.end
        before = errors(self.ed)
        self.assertIsNone(self.ed.connect(self.call, b1, self.l3))   # b1 aguarda retorno de b2: salto
        self.assertIsNone(self.ed.connect(self.ret, b1, b2))          # retorno no sentido errado
        self.assertEqual(errors(self.ed), before)                     # nenhuma notificação
        e2 = self.ed.connect(self.call, b2, self.l3)
        b3 = e2.end
        self.assertIsNotNone(self.ed.connect(self.ret, b3, b2))
        self.assertIsNone(self.ed.connect(self.ret, b3, b2))          # já retornou
        self.assertIsNotNone(self.ed.connect(self.ret, b2, b1))
        self.assertIsNotNone(self.ed.connect(self.call, b1, self.l4))  # b1 voltou a ser ativa
        self.assertEqual(errors(self.ed), before)

    def test_call_and_return_only_between_activation_boxes(self):
        self.ed.connect(self.call, self.l1, self.l2)
        self.assertIsNone(self.ed.connect(self.ret, self.l1, self.l2))
        self.assertEqual(errors(self.ed), 1)

    def test_box_cannot_receive_calls_from_several_callers(self):
        from jetuml_py.validation import validate_edge
        e1 = self.ed.connect(self.call, self.l1, self.l2)
        e2 = self.ed.connect(self.call, e1.end, self.l3)
        self.ed.connect(self.ret, e2.end, e1.end)
        res = validate_edge(self.ed.diagram, "Call", {}, e1.end, e2.end)
        self.assertFalse(res)
        self.assertFalse(res.silent)

    def test_self_call_and_constructor_call(self):
        e1 = self.ed.connect(self.call, self.l1, self.l2)
        b2 = e1.end
        selfcall = self.ed.add_call(b2, b2)
        self.assertIs(selfcall.end.parent, self.l2)
        self.assertIsNot(selfcall.end, b2)
        self.ed.connect(self.ret, selfcall.end, b2)
        ctor = self.ed.add_call(b2, self.l4, constructor=True)
        self.assertEqual(ctor.props["middle_label"], "«create»")
        self.assertIsNone(self.ed.add_call(b2, self.l4, constructor=True))  # já criada
        # a linha de vida criada pode originar chamadas sem violar a regra de raiz única
        self.assertIsNotNone(self.ed.add_call(self.l4, self.l3))

    def test_call_node_cannot_be_added_directly(self):
        self.assertIsNone(self.ed.add_node("Call", 0, 0, parent=self.l1))
        self.assertEqual(errors(self.ed), 1)


if __name__ == "__main__":
    unittest.main()
