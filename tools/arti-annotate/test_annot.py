import json
import os
import unittest

import annot

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "fixtures.json"), encoding="utf-8") as f:
    FIXTURES = json.load(f)


class FixtureTests(unittest.TestCase):
    def test_fixtures(self):
        for fx in FIXTURES:
            with self.subTest(fx["name"]):
                got = annot.parse(fx["input"])
                self.assertEqual(len(got), len(fx["parse"]))
                for g, want in zip(got, fx["parse"]):
                    for k, v in want.items():
                        self.assertEqual(g[k], v, k)
                self.assertEqual(annot.strip(fx["input"]), fx["strip"])
                for ann_id, want in fx["accept"].items():
                    self.assertEqual(annot.accept(fx["input"], ann_id), want)
                for ann_id, want in fx["revert"].items():
                    self.assertEqual(annot.revert(fx["input"], ann_id), want)


class MutationTests(unittest.TestCase):
    def test_add_comment_then_revise_then_revert(self):
        t = "Make this concise. Keep that."
        t = annot.add_comment(t, 0, 18, "shorter")
        self.assertEqual(t, "{==Make this concise.==}{>>#a1 open | shorter<<} Keep that.")
        t = annot.revise(t, "a1", "Be concise.")
        a = annot.parse(t)[0]
        self.assertEqual((a["status"], a["text"], a["was"], a["note"]), ("revised", "Be concise.", "Make this concise.", "shorter"))
        self.assertEqual(annot.revert(t, "a1"), "Make this concise. Keep that.")
        self.assertEqual(annot.accept(t, "a1"), "Be concise. Keep that.")

    def test_revise_twice_keeps_first_original(self):
        t = annot.add_comment("one two", 0, 3, "")
        t = annot.revise(annot.revise(t, "a1", "uno"), "a1", "eins")
        self.assertEqual(annot.revert(t, "a1"), "one two")

    def test_next_id_and_overlap(self):
        t = annot.add_comment("alpha beta gamma", 0, 5, "x")
        t = annot.add_comment(t, t.index("gamma"), len(t), "y")
        self.assertEqual([a["id"] for a in annot.parse(t)], ["a1", "a2"])
        with self.assertRaises(ValueError):
            annot.add_comment(t, 0, 3, "overlap")

    def test_delimiter_in_note_and_was_is_escaped(self):
        t = annot.add_comment("x y", 0, 1, "bad <<} note")
        self.assertEqual(annot.parse(t)[0]["note"], "bad < <} note")
        t = annot.revise(annot.add_comment("q <<} r", 0, 7, ""), "a1", "z")
        self.assertEqual(annot.parse(t)[0]["was"], "q <<} r")

    def test_suggestion_roundtrip(self):
        t = annot.add_suggestion("We utilize it.", 3, 10, "use", "plain")
        self.assertEqual(annot.accept(t, "a1"), "We use it.")
        self.assertEqual(annot.revert(t, "a1"), "We utilize it.")

    def test_crlf_preserved(self):
        t = "a\r\n{==b==}{>>#a1 open<<}\r\nc"
        self.assertEqual(annot.strip(t), "a\r\nb\r\nc")


if __name__ == "__main__":
    unittest.main()
