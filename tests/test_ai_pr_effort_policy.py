import re
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_ALIASES = REPO_ROOT / "shell/zsh/alias/ai/claude.zsh"
CODEX_ALIASES = REPO_ROOT / "shell/zsh/alias/ai/codex.zsh"
CLAUDE_COMMON = REPO_ROOT / "shell/common/alias/claude.sh"


def run_zsh(script: str, command: str) -> list[str]:
    """Run an alias after sourcing it and return the stubbed CLI arguments."""
    result = subprocess.run(
        ["zsh", "-fc", script],
        cwd=REPO_ROOT,
        env={
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "TEST_COMMAND": command,
        },
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    return [match.group(1) for match in re.finditer(r"^<(.*)>$", result.stdout, re.MULTILINE)]


def run_claude_alias(command: str) -> list[str]:
    return run_zsh(
        f'''source "{CLAUDE_ALIASES}"
no_notify() {{ printf '<%s>\\n' "$@"; }}
eval "$TEST_COMMAND"''',
        command,
    )


def run_codex_alias(command: str) -> list[str]:
    return run_zsh(
        f'''source "{CODEX_ALIASES}"
cx() {{ printf '<%s>\\n' "$@"; }}
source "{REPO_ROOT / 'shell/zsh/alias/ai/ai.zsh'}"
eval "$TEST_COMMAND"''',
        command,
    )


def run_codex_command(command: str) -> list[str]:
    return run_zsh(
        f'''source "{CODEX_ALIASES}"
no_notify() {{ printf '<%s>\\n' "$@"; }}
remove_tmux_window_icon() {{ :; }}
eval "$TEST_COMMAND"''',
        command,
    )


def frontmatter_value(path: Path, field: str) -> str:
    match = re.search(rf"^{re.escape(field)}: ?(.+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
    if match is None:
        raise AssertionError(f"{field} is missing from {path}")
    return match.group(1).strip().strip('"')


def toml_header_value(path: Path, field: str) -> str:
    match = re.search(
        rf'^{re.escape(field)} = "([^"]+)"$', path.read_text(encoding="utf-8"), re.MULTILINE
    )
    if match is None:
        raise AssertionError(f"{field} is missing from {path}")
    return match.group(1)


def toml_header_has_field(path: Path, field: str) -> bool:
    return re.search(rf"^{re.escape(field)} = ", path.read_text(encoding="utf-8"), re.MULTILINE) is not None


class PrCommentImplementAliasTest(unittest.TestCase):
    URL = "https://github.com/acme/widget/pull/42#discussion_r123"
    EXTRA = "fix only the failing path"

    ALIASES = (
        ("cl-pr-comment-implement", "_cl-pr-comment-implement", "light"),
        ("cl-pci", "_cl-pr-comment-implement", "light"),
        ("clh-pr-comment-implement", "_clh-pr-comment-implement", "high"),
        ("clh-pci", "_clh-pr-comment-implement", "high"),
        ("cx-pr-comment-implement", "_cx-pr-comment-implement", "light"),
        ("cx-pci", "_cx-pr-comment-implement", "light"),
        ("cxh-pr-comment-implement", "_cxh-pr-comment-implement", "high"),
        ("cxh-pci", "_cxh-pr-comment-implement", "high"),
    )

    def test_all_public_aliases_retain_noglob_and_dispatch_policy(self):
        claude_aliases = CLAUDE_ALIASES.read_text(encoding="utf-8")
        codex_aliases = CODEX_ALIASES.read_text(encoding="utf-8")

        for alias, helper, tier in self.ALIASES:
            with self.subTest(alias=alias):
                aliases = claude_aliases if alias.startswith("cl") else codex_aliases
                self.assertIn(f"alias {alias}='noglob {helper}'", aliases)

                captured = (
                    run_claude_alias(f'{alias} "{self.URL}" "{self.EXTRA}"')
                    if alias.startswith("cl")
                    else run_codex_alias(f'{alias} "{self.URL}" "{self.EXTRA}"')
                )
                prompt_prefix = "/" if alias.startswith("cl") else "$"
                prompt = f"{prompt_prefix}pr-comment-implement {self.URL} {self.EXTRA}"

                self.assertEqual(captured[-1], prompt)
                self.assertEqual(captured.count(prompt), 1)
                if alias.startswith("cl"):
                    self.assertEqual(captured[:4], ["claude", "--allow-dangerously-skip-permissions", "--permission-mode", "plan"])
                    self.assertNotIn("--model", captured)
                    if tier == "light":
                        self.assertNotIn("--effort", captured)
                    else:
                        self.assertEqual(captured[4:6], ["--effort", "high"])
                else:
                    if tier == "light":
                        self.assertNotIn("--model", captured)
                        self.assertNotIn("-c", captured)
                    else:
                        self.assertEqual(captured[:2], ["--model", "gpt-5.6-sol"])
                        self.assertEqual(captured[2:4], ["-c", 'model_reasoning_effort="high"'])


class CodexModelSelectionTest(unittest.TestCase):
    def test_commands_select_the_expected_model(self):
        cases = (
            ("cx task", ["--model", "gpt-5.6-terra", "task"]),
            ("cx --model custom-model task", ["--model", "custom-model", "task"]),
            ("cx --model=custom-model task", ["--model=custom-model", "task"]),
            ("cx -m custom-model task", ["-m", "custom-model", "task"]),
            (
                "cxh task",
                ["--model", "gpt-5.6-sol", "-c", 'model_reasoning_effort="high"', "task"],
            ),
        )

        for command, expected in cases:
            with self.subTest(command=command):
                captured = run_codex_command(command)
                self.assertEqual(captured[:2], ["homebrew_run", "codex"])
                self.assertEqual(captured[2:], expected)


class ReviewEntrypointEffortPolicyTest(unittest.TestCase):
    def test_claude_review_roles_use_the_expected_effort(self):
        cases = (
            ("cl-pr-review 123 focus on errors", "high", "/pr-review 123 focus on errors ultrathink"),
            ("cl-pr-review-subagents 123 focus on errors", "high", "/pr-review-subagents 123 focus on errors ultrathink"),
            ("cl-pcr https://github.com/acme/widget/pull/42#discussion_r123 focus", "high", "/pr-comment-review https://github.com/acme/widget/pull/42#discussion_r123 focus ultrathink"),
        )

        for command, effort, prompt in cases:
            with self.subTest(command=command):
                captured = run_claude_alias(command)
                effort_index = captured.index("--effort")
                self.assertEqual(captured[effort_index + 1], effort)
                self.assertEqual(captured[-1], prompt)

    def test_codex_review_roles_use_the_expected_effort(self):
        cases = (
            ("cx-pr-review 123 focus on errors", "high", "$pr-review PR #123 をレビューして focus on errors"),
            ("cx-pr-review-subagent 123 focus on errors", "high", "$pr-review-subagents PR #123 をレビューして focus on errors"),
            ("cx-pcr https://github.com/acme/widget/pull/42#discussion_r123 focus", "high", "$pr-comment-review https://github.com/acme/widget/pull/42#discussion_r123 focus"),
        )

        for command, effort, prompt in cases:
            with self.subTest(command=command):
                captured = run_codex_alias(command)
                self.assertEqual(captured[:2], ["--model", "gpt-5.6-sol"])
                self.assertEqual(captured[2:4], ["-c", f'model_reasoning_effort="{effort}"'])
                self.assertIn("--dangerously-bypass-approvals-and-sandbox", captured)
                self.assertEqual(captured[-1], prompt)


class ReviewerAgentEffortPolicyTest(unittest.TestCase):
    DIMENSIONS = (
        "bugs",
        "security",
        "architecture",
        "errors",
        "history",
        "tests",
        "performance",
        "consistency",
        "simplification",
    )

    def test_claude_reviewer_sources_and_generated_agents_match(self):
        for dimension in self.DIMENSIONS:
            with self.subTest(dimension=dimension):
                source = REPO_ROOT / f"ai/claude/agents_src/head_{dimension}.md"
                generated = REPO_ROOT / f"ai/claude/agents/pr-reviewer-{dimension}.md"
                self.assertEqual(frontmatter_value(source, "effort"), "high")
                self.assertEqual(frontmatter_value(generated, "effort"), "high")
                self.assertEqual(frontmatter_value(generated, "model"), frontmatter_value(source, "model"))

    def test_codex_reviewer_sources_and_generated_agents_match(self):
        for dimension in self.DIMENSIONS:
            with self.subTest(dimension=dimension):
                source = REPO_ROOT / f"ai/codex/agents_src/head_{dimension}.toml"
                generated = REPO_ROOT / f"ai/codex/agents/pr_reviewer_{dimension}.toml"
                # Review agents inherit the caller's model and effort configuration.
                for field in ("model", "model_reasoning_effort"):
                    self.assertFalse(toml_header_has_field(source, field))
                    self.assertFalse(toml_header_has_field(generated, field))

    def test_codex_review_fix_agents_inherit_caller_model_and_effort(self):
        for role in ("designer", "implementer"):
            with self.subTest(role=role):
                source = REPO_ROOT / f"ai/codex/agents_src/review_fix/head_{role}.toml"
                generated = REPO_ROOT / f"ai/codex/agents/review_fix_{role}.toml"
                # Review-fix agents must not override the caller's execution settings.
                for field in ("model", "model_reasoning_effort"):
                    self.assertFalse(toml_header_has_field(source, field))
                    self.assertFalse(toml_header_has_field(generated, field))


if __name__ == "__main__":
    unittest.main()
