import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env


SKILL = REPO_ROOT / "ai/common/shared_skills/pr-verify"


class PrVerifyContractTest(unittest.TestCase):
    def test_platform_links_and_metadata(self):
        for platform in ("claude", "codex"):
            link = REPO_ROOT / f"ai/{platform}/skills/pr-verify"
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), "../../common/shared_skills/pr-verify")
            self.assertEqual(link.resolve(), SKILL.resolve())
        self.assertIn("$pr-verify", (SKILL / "agents/openai.yaml").read_text())

    def test_workflow_preserves_approval_and_safety_boundaries(self):
        content = (SKILL / "SKILL.md").read_text()
        for requirement in (
            "Wait for explicit approval before creating the worktree",
            "Changed scope, safety boundaries or test",
            "git worktree add -b <verification-branch> <verification-path> <pinned-head-sha>",
            "Do not inherit live service credentials",
            "Do not send real\nnotifications",
            "disable user, group and\nbroadcast mentions",
            "`テスト通知`",
            "Neutralize mention markup",
            "Stop execution, report the reproduction",
            "obtain approval before fixing",
            "Never push to the original\nor PR branch",
            "Commit only on the verification branch",
            "delete the verification branch or its remote ref",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, content)

    def test_all_existing_branches_are_protected(self):
        content = " ".join((SKILL / "SKILL.md").read_text().split())
        for requirement in (
            "every existing local branch and every branch on that remote with its name and SHA",
            "never update or delete them",
            "Only the verification branch created by this run may be changed",
            "Fetch may update remote-tracking refs, but never fetch into a local branch",
            "Check both local branches and the publication remote for each candidate",
            "Before its first push, require the remote branch to be absent",
            "empty expected-value lease",
            "last independently verified SHA; stop if it changed",
            "compare all recorded local and publication-remote branch names and SHAs",
            "without restoring branches or overwriting concurrent work",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, content)

    def test_completion_always_offers_pr_body_recording(self):
        content = " ".join((SKILL / "SKILL.md").read_text().split())
        report = content.split("## Report and preserve", 1)[1].split(
            "## Prepare the PR verification section", 1
        )[0]
        for requirement in (
            "Always offer recording the results in the original PR body before any preservation-only exit",
            "successful verification, failed cases, ending without fixing a defect, and interrupted execution or unverified cases after execution started",
            "`PR本文への記載を準備する（検証ブランチにローカルコミット）`",
            "`PR本文には記載せず、worktreeごと保持する`",
            "For the second, report its path, branch and uncommitted status and stop",
            "If preparation cannot proceed safely, report the reason and the unfinished stage",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, report)
        self.assertLess(report.index("Always offer"), report.index("Ask exactly:"))

    def test_completion_offer_excludes_pre_execution_and_early_push(self):
        content = " ".join((SKILL / "SKILL.md").read_text().split())
        self.assertIn("This completion offer does not apply to cancellation before execution or an early push needed to execute verification", content)
        early = content.split("## Publish early when execution requires it", 1)[1].split(
            "## Execute safely", 1
        )[0]
        self.assertIn("do not present the completion offer at this stage", early)

    def test_publication_requires_approval_and_verified_push(self):
        content = (SKILL / "SKILL.md").read_text()
        for requirement in (
            "Local commit approval does not\n  authorize pushing or updating the PR body",
            "Wait for explicit publication approval",
            "GitHub Actions run, Jenkins build/job and Slack notification links",
            "Do not trigger jobs or send Slack messages",
            "remaining concerns",
            "containing the saved verification commit SHA",
            "destination is the PR's base repository",
            "inspect push hooks and workflows",
            "Push that branch with `-u`",
            "remote ref matches the saved commit",
            "upstream matches the pushed branch",
            "Do not update the PR body unless push is verified",
            "gh pr edit <PR-number> --repo <base-owner/repo> --body-file <approved-body-file>",
            "Independently re-fetch the body",
            "stop without automatically retrying or reposting",
            "Never automatically delete published evidence on failure",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, content)

    def test_overview_and_review_selection_precede_final_plan_and_execution(self):
        content = " ".join((SKILL / "SKILL.md").read_text().split())
        stages = (
            "Present a short overview",
            "`この概要で進める`",
            "After agreement, ask exactly:",
            "`両方のレビューを実施する`",
            "`レビューなしで進める`",
            "Prepare a verification design containing:",
            "## Independently review the design",
            "Give both reviewers the same complete, versioned design",
            "both completed reviews of the same final version",
            "## Present and approve the final design",
            "present the final `<proposed_plan>`",
            "`承認して進める`",
            "## Isolate the approved snapshot",
            "git worktree add -b",
        )
        positions = [content.index(stage) for stage in stages]
        self.assertEqual(positions, sorted(positions))
        for requirement in (
            "present the overview again and repeat the confirmation",
            "overview does not authorize verification execution",
            "AI usage cost, and temporary input/output directory in this same confirmation",
            "not verification or worktree creation",
            "Do not ask for launch permission again",
            "do not launch either reviewer; mark the choice and `未レビュー`",
            "Resolve known safety concerns before proceeding even without review",
            "If findings change the agreed overview, present it again and obtain agreement",
            "Do not create a worktree or execute PR code until plan mode has ended",
            "no changes outside the approved temporary area",
            "no effects on live services",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, content)

    def test_reviewer_models_context_and_read_only_scope(self):
        content = " ".join((SKILL / "SKILL.md").read_text().split())
        for requirement in (
            "From Codex: a fresh-context `gpt-6.1-sol` / `high` subagent and external Claude `opus` / `high`",
            "From Claude: a fresh-context `opus` / `high` subagent and external Codex `gpt-6.1-sol` / `high`",
            "Explicitly set model and reasoning effort",
            "including the Claude subagent",
            'use `fork_turns="none"`',
            "same complete, versioned design, pinned PR base/head SHA, related code and configuration at those revisions, and unverified points",
            "Exclude the parent's safety judgments, conversation history and the other reviewer's results",
            "Use `second-opinion` for the external CLI launch",
            "read-only inspection of setup, dependency installation and lifecycle scripts",
            "Git hooks and checkout filters, test child processes",
            "inherited environment and credentials, shared data, notifications and external writes",
            "isolation measures reach the actual implementation and its subprocesses",
            "Do not execute PR code or verification commands during review",
            "evidence, remaining concerns and unverified points",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, content)

    def test_review_blockers_stop_verification_without_fallback(self):
        content = " ".join((SKILL / "SKILL.md").read_text().split())
        for requirement in (
            "Stop before verification on unresolved side-effect concerns",
            "missing information needed for judgment",
            "unavailable CLIs, launch failure or incomplete responses",
            "required model or effort cannot be set, stop",
            "non-zero exit, empty answer or missing final `__END_OF_ANSWER__` line means failure",
            "Do not automatically substitute models or skip a review",
            "Report the blocker and resolve it before proceeding",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, content)

    def test_changed_design_requires_both_reviews_and_saved_evidence(self):
        content = " ".join((SKILL / "SKILL.md").read_text().split())
        for requirement in (
            "Check findings against their evidence",
            "same revised version to both fresh, independent reviewers again",
            "both completed reviews of the same final version with no unresolved side-effect concerns or missing information",
            "One reviewer's approval or a majority vote cannot satisfy this gate",
            "design or execution conditions change after final review, repeat both independent reviews",
            "if already approved, obtain design approval again",
            "later fix designs and changes during verification",
            "`.pr-verify/<run-id>/`",
            "design versions and the review choice",
            "models and reasoning efforts, both review results and responses to findings",
            "the skipped path, record `未レビュー`",
            "temporary area, transfer them only after design approval",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, content)

    def test_body_replacement_preserves_user_content_and_detects_conflicts(self):
        content = (SKILL / "SKILL.md").read_text()
        for requirement in (
            "<!-- pr-verify:start -->",
            "<!-- pr-verify:end -->",
            "With no markers, append the section",
            "with exactly one ordered pair",
            "Preserve all content outside the managed section",
            "Stop on incomplete, reversed or duplicate markers",
            "Re-read the PR body and head immediately before updating",
            "If either changed",
            "obtain approval again",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, content)


class PrVerifyGitIsolationTest(unittest.TestCase):
    def test_branch_collisions_publication_and_concurrent_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote.git"
            repo = root / "repo"
            repo.mkdir()
            env = sanitized_env({
                "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
            })

            def git(*args, cwd=repo, check=True):
                return subprocess.run(
                    ["git", *args], cwd=cwd, env=env, check=check,
                    capture_output=True, text=True,
                )

            git("init", "--bare", str(remote))
            git("init", "-b", "main")
            git("commit", "--allow-empty", "-m", "initial")
            initial = git("rev-parse", "HEAD").stdout.strip()
            git("remote", "add", "origin", str(remote))
            git("branch", "verify/pr-123-test")
            git("push", "origin", "main", "main:refs/heads/verify/pr-123-test-1")
            local_before = git("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads").stdout
            remote_before = git("ls-remote", "--heads", "origin").stdout
            occupied = {line.split()[1].removeprefix("refs/heads/") for line in remote_before.splitlines()}
            occupied.update(line.split()[0].removeprefix("refs/heads/") for line in local_before.splitlines())
            base = "verify/pr-123-test"
            suffix = 0
            candidate = base
            while candidate in occupied:
                suffix += 1
                candidate = f"{base}-{suffix}"
            self.assertEqual(candidate, f"{base}-2")
            worktree = root / "verification"
            git("worktree", "add", "-b", candidate, str(worktree), initial)
            git("commit", "--allow-empty", "-m", "evidence", cwd=worktree)
            saved = git("rev-parse", "HEAD", cwd=worktree).stdout.strip()
            ref = f"refs/heads/{candidate}"
            git("push", "-u", f"--force-with-lease={ref}:", "origin", f"HEAD:{ref}", cwd=worktree)
            git("worktree", "remove", str(worktree))
            self.assertEqual(git("rev-parse", candidate).stdout.strip(), saved)
            self.assertEqual(git("rev-parse", "main").stdout.strip(), initial)
            self.assertEqual(git("rev-parse", base).stdout.strip(), initial)
            self.assertEqual(git("ls-remote", "--heads", "origin", "main", f"{base}-1").stdout, remote_before)

            # A concurrent creator must not be overwritten by the initial push.
            race_ref = "refs/heads/verify/pr-123-race"
            git("push", "origin", f"main:{race_ref}")
            rejected = git("push", f"--force-with-lease={race_ref}:", "origin", f"{candidate}:{race_ref}", check=False)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(git("ls-remote", "origin", race_ref).stdout.split()[0], initial)
            # Report concurrent changes instead of restoring the recorded SHA.
            git("commit", "--allow-empty", "-m", "concurrent change")
            concurrent = git("rev-parse", "main").stdout.strip()
            self.assertNotEqual(concurrent, initial)
            self.assertEqual(git("rev-parse", "main").stdout.strip(), concurrent)

    def test_dirty_origin_snapshot_collision_and_saved_branch(self):
        # Exercise cleanup only in a disposable repository, never this checkout.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            origin = root / "origin"
            origin.mkdir()
            env = sanitized_env({
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_AUTHOR_NAME": "test",
                "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_NAME": "test",
                "GIT_COMMITTER_EMAIL": "test@example.invalid",
            })

            def git(*args, cwd=origin, check=True):
                return subprocess.run(
                    ["git", *args], cwd=cwd, env=env, check=check,
                    capture_output=True, text=True,
                )

            git("init", "-b", "main")
            git("config", "core.hooksPath", str(root / "no-hooks"))
            (origin / "feature.txt").write_text("PR snapshot\n")
            git("add", "feature.txt")
            git("commit", "-m", "initial")
            pinned = git("rev-parse", "HEAD").stdout.strip()
            (origin / "feature.txt").write_text("uncommitted user work\n")
            before = git("status", "--porcelain").stdout
            worktree = root / "verification"
            branch = "verify/pr-123-test"
            git("worktree", "add", "-b", branch, str(worktree), pinned)
            self.assertEqual((worktree / "feature.txt").read_text(), "PR snapshot\n")
            collision = git("worktree", "add", "-b", branch, str(root / "collision"), pinned, check=False)
            self.assertNotEqual(collision.returncode, 0)

            # A later PR commit must not silently replace the pinned snapshot.
            git("commit", "--allow-empty", "-m", "updated PR")
            updated = git("rev-parse", "HEAD").stdout.strip()
            self.assertNotEqual(updated, pinned)
            self.assertEqual(git("rev-parse", "HEAD", cwd=worktree).stdout.strip(), pinned)
            (worktree / "verification.txt").write_text("synthetic verification evidence\n")
            refused = git("worktree", "remove", str(worktree), check=False)
            self.assertNotEqual(refused.returncode, 0)
            self.assertTrue(worktree.exists())
            git("add", "verification.txt", cwd=worktree)
            git("commit", "-m", "save verification", cwd=worktree)
            saved = git("rev-parse", "HEAD", cwd=worktree).stdout.strip()
            git("worktree", "remove", str(worktree))
            self.assertFalse(worktree.exists())
            self.assertEqual(git("rev-parse", branch).stdout.strip(), saved)
            self.assertEqual(git("show", f"{branch}:verification.txt").stdout, "synthetic verification evidence\n")
            self.assertEqual(git("rev-parse", "HEAD").stdout.strip(), updated)
            self.assertEqual(git("branch", "--show-current").stdout.strip(), "main")
            self.assertEqual(git("status", "--porcelain").stdout, before)
            self.assertEqual((origin / "feature.txt").read_text(), "uncommitted user work\n")
