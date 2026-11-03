import re
import unittest
from pathlib import Path

from tools.traceability import MATRIX, verify


class Traceability(unittest.TestCase):
    def test_every_cited_test_exists(self):
        self.assertEqual(verify(), [])

    def test_every_requirement_in_the_doc_is_covered(self):
        doc = (Path(__file__).resolve().parent.parent / "docs" / "REQUISITOS.md").read_text(encoding="utf-8")
        ids = set(re.findall(r"^\| ((?:RF|RNF)\d+) \|", doc, re.M))
        self.assertEqual(len(ids), 45)
        self.assertEqual(ids - set(MATRIX), set())
        self.assertEqual(set(MATRIX) - ids, set())


if __name__ == "__main__":
    unittest.main()
