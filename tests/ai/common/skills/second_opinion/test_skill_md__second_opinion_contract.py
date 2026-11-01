import re
import unittest

from support import REPO_ROOT


SKILL_DIR = REPO_ROOT / "ai/common/skills/second-opinion"
WRITE_FLAGS = ("--write", "workspace-write", "auto_edit", "acceptEdits")


def split_skill(text):
    _, frontmatter, body = text.split("---", 2)
    return frontmatter, body


class SecondOpinionSkillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        cls.frontmatter, cls.body = split_skill(cls.text)

    def test_frontmatter_has_only_name_and_one_line_description(self):
        keys = re.findall(r"^([A-Za-z_-]+):", self.frontmatter, re.MULTILINE)
        self.assertEqual(keys, ["name", "description"])
        self.assertIn("name: second-opinion", self.frontmatter)

    def test_model_and_effort_are_always_explicit(self):
        for required in (
            "always pass both explicitly",
            "never rely on a CLI default",
            "-m <model>",
            "--model <model>",
            "--effort <level>",
            'model_reasoning_effort="<e>"',
            "Gemini has no effort setting",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.body)

    def test_consultation_never_edits(self):
        # Asking for an opinion must not be able to change the working tree, so no
        # write-capable flag may appear in the skill or its references.
        texts = {
            path.name: path.read_text(encoding="utf-8")
            for path in (SKILL_DIR / "SKILL.md", *(SKILL_DIR / "references").glob("*.md"))
        }
        for name, text in texts.items():
            for flag in WRITE_FLAGS:
                with self.subTest(file=name, flag=flag):
                    self.assertNotIn(flag, text)
        self.assertIn("This skill never edits files", self.body)

    def test_every_target_runs_read_only(self):
        rows = {
            line.split("|")[1].strip(): line
            for line in self.body.splitlines()
            if re.match(r"\| (codex|gemini|claude) \|", line)
        }
        self.assertEqual(set(rows), {"codex", "gemini", "claude"})
        self.assertIn("-s read-only", rows["codex"])
        self.assertIn("--approval-mode plan", rows["gemini"])
        self.assertIn("--permission-mode plan", rows["claude"])
        self.assertIn("sandbox_mode=\"read-only\"", self.body)

    def test_autonomous_launch_requires_confirmation_before_any_cli_runs(self):
        for required in (
            "you may only propose it",
            "run no CLI until the answer arrives",
            "Ask at most once per topic",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.body)

    def test_failure_is_distinguished_from_answer_content(self):
        for required in (
            "non-zero exit",
            "an empty answer",
            "no `__END_OF_ANSWER__` line",
            "incomplete, not an answer",
            "do not answer in its place",
            "do not add flags such as `--skip-trust`",
            "separate files",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.body)

    def test_sessions_are_kept_so_conversations_can_resume(self):
        for required in ("--session-id", "--resume", "codex exec resume", "thread_id"):
            with self.subTest(required=required):
                self.assertIn(required, self.body)
        # These flags drop the session and break resume; they may only appear in the prohibition.
        for flag in ("--ephemeral", "--no-session-persistence"):
            with self.subTest(flag=flag):
                for line in self.body.splitlines():
                    if flag in line:
                        self.assertIn("Never add", line)

    def test_one_context_request_per_target(self):
        for required in ("Context request", "once per target", "Ask for more only once per target"):
            with self.subTest(required=required):
                self.assertIn(required, self.body)

    def test_report_keeps_evidence_and_verifies_findings(self):
        for required in (
            "session ID",
            "the resume command",
            "open the cited `file:line` yourself",
            "regenerates each attached output",
            "Make no code changes and apply no suggested fix until the user chooses",
            "Never call the CLI you are running in",
            "`trash`",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.body)

    def test_references_are_routed_by_path(self):
        for reference in ("references/brief.md", "references/models.md"):
            with self.subTest(reference=reference):
                self.assertIn(reference, self.body)
                self.assertTrue((SKILL_DIR / reference).is_file())

    def test_positional_parameters_survive_skill_argument_substitution(self):
        # Claude Code rewrites bare $N in a skill body when the skill is invoked with args.
        self.assertNotRegex(self.text, r"\$[0-9]")


if __name__ == "__main__":
    unittest.main()
