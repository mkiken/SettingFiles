import unittest

from support import REPO_ROOT


class ClaudeMdSkillToneTest(unittest.TestCase):
    def test_skill_edits_keep_normal_prose_without_genshijin_confirmation(self):
        content = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")

        for required in (
            "Keep skill prose non-genshijin",
            "skill sources and generated skill outputs",
            "follow their existing normal prose style",
            "Do not ask whether to use genshijin when editing a skill",
            "even though `SKILL.md` is a text file",
        ):
            with self.subTest(required=required):
                self.assertIn(required, content)


if __name__ == "__main__":
    unittest.main()
