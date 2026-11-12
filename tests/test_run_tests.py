import io
import os
import signal
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_tests
from support import sanitized_env


class RunTestsTest(unittest.TestCase):
    def test_changed_paths_include_git_changes_and_preserve_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            def git(*args):
                return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, env=sanitized_env())
            git("init", "-q")
            git("config", "user.email", "test@example.invalid")
            git("config", "user.name", "Test")
            (root / "old").write_text("old")
            git("add", "old")
            git("commit", "-qm", "base")
            base = git("rev-parse", "HEAD").stdout.decode().strip()
            (root / "old").write_text("staged")
            git("add", "old")
            (root / "old").write_text("unstaged")
            (root / "space and\nnewline").write_text("new")
            self.assertEqual(run_tests.changed_paths(root=root), (["old", "space and\nnewline"], False))
            git("commit", "-qm", "change")
            self.assertEqual(run_tests.changed_paths(base, root=root), (["old", "space and\nnewline"], False))
            with self.assertRaises(ValueError):
                run_tests.changed_paths("invalid-commit", root=root)

    def test_changed_paths_detects_deletes_and_renames(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            def git(*args):
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, env=sanitized_env())
            git("init", "-q")
            git("config", "user.email", "test@example.invalid")
            git("config", "user.name", "Test")
            (root / "old").write_text("old")
            git("add", "old")
            git("commit", "-qm", "base")
            (root / "old").rename(root / "new")
            self.assertEqual(run_tests.changed_paths(root=root), (["new", "old"], True))

    def test_argument_conflicts_are_rejected(self):
        for args in (["--base", "HEAD"], ["--changed", "--paths", "x"]):
            with self.subTest(args=args), mock.patch("sys.stderr", io.StringIO()):
                with self.assertRaises(SystemExit):
                    run_tests.parse_args(args)

    def test_discovery_rejects_missing_packages_empty_and_import_errors(self):
        cases = {"missing": ("nested/test_missing.py", "import unittest\n"),
                 "empty": ("test_empty.py", "value = 1\n"),
                 "broken": ("test_broken.py", "raise ImportError('broken')\n")}
        for name, (file, contents) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                target = root / file
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents)
                with self.assertRaises(ValueError):
                    run_tests.discover_test_ids(root)

    def test_dependency_map_validates_exclusions_and_targets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            map_path = root / "dependencies.toml"
            for content in ('[untested]\n"a" = ""', '[untested]\n"a" = 1',
                            '[untested]\n"a" = "one"\n"a" = "two"',
                            '[untested]\n"a" = "reason"\n[extra_tests]\n"a" = ["tests/missing.py"]'):
                map_path.write_text(content)
                with self.subTest(content=content), self.assertRaises(ValueError):
                    run_tests.load_dependency_map(map_path, root=root, test_ids=[])
            target = root / "tests/test_example.py"
            target.parent.mkdir()
            target.write_text("import unittest\n")
            map_path.write_text('[extra_tests]\n"a" = ["tests/test_example.py"]')
            with self.assertRaisesRegex(ValueError, "uncollected"):
                run_tests.load_dependency_map(map_path, root=root, test_ids=[])

    def test_full_suite_triggers_include_shared_files_and_deletion(self):
        self.assertTrue(run_tests.requires_full_suite(["tests/support.py"]))
        self.assertTrue(run_tests.requires_full_suite(["tests/pkg/__init__.py"]))
        self.assertTrue(run_tests.requires_full_suite(["any"], deleted=True))
        self.assertFalse(run_tests.requires_full_suite(["shell/example.sh"]))

    def test_config_audit_dispatch_reads_shared_core_and_adapters(self):
        expected = run_tests.TEST_DIR / "ai/codex/skills/config_audit/test_skill_head_md__dispatch_contract.py"
        for source in ("ai/common/config_audit_subagents/orchestrator_core.md",
                       "ai/claude/skills/config-audit/SKILL.md",
                       "ai/gemini/commands/config-audit.toml"):
            with self.subTest(source=source):
                selected, unmatched = run_tests.selected_test_paths([source])
                self.assertIn(expected, selected)
                self.assertFalse(unmatched)

    def test_herdr_status_selects_shared_modules(self):
        expected = run_tests.TEST_DIR / "shell/herdr/test_herdr_status_icon_sh.py"
        for source in ("shell/tmux/tmux_emoji.conf", "shell/tmux/tmux_window_name.py"):
            with self.subTest(source=source):
                selected, unmatched = run_tests.selected_test_paths([source])
                self.assertIn(expected, selected)
                self.assertFalse(unmatched)

    def test_shell_source_dependencies_select_the_reader(self):
        cases = (
            ("shell/zsh/auto_multiplexer.zsh", "tests/mac/scripts/test_herdr_sh__herdr_setup.py"),
            ("shell/zsh/filter/base.zsh", "tests/mac/scripts/test_herdr_sh__herdr_setup.py"),
            ("shell/zsh/plugin.zsh", "tests/mac/scripts/test_herdr_sh__herdr_setup.py"),
            ("shell/tmux/tmux_notification_title.sh", "tests/shell/tmux/test_ai_notification_summary_sh.py"),
            ("shell/tmux/tmux_notification_title.sh", "tests/shell/tmux/test_claude_transcript_analyze.py"),
            ("shell/tmux/tmux_notification_title.sh", "tests/shell/tmux/test_gemini_transcript_summary_jq.py"),
            ("shell/tmux/ai_notification_summary.sh", "tests/shell/tmux/test_claude_transcript_analyze.py"),
            ("shell/tmux/ai_notification_summary.sh", "tests/shell/tmux/test_gemini_transcript_summary_jq.py"),
            ("shell/tmux/tmux_window_name.sh", "tests/shell/zsh/alias/test_notification_zsh__notification_silent_mode.py"),
        )
        for source, test in cases:
            with self.subTest(source=source, test=test):
                selected, unmatched = run_tests.selected_test_paths([source])
                self.assertIn(run_tests.REPO_ROOT / test, selected)
                self.assertFalse(unmatched)

    def test_direct_read_dependencies_select_the_reader(self):
        cases = (
            ('ai/common/skills/plan-review/references/claude.md', 'tests/ai/claude/test_claude_md__plan_review_body_output.py'),
            ('.gitignore', 'tests/ai/claude/test_settings_json__slash_anywhere_mod.py'),
            ('ai/codex/config.toml', 'tests/ai/codex/skills/plan_model_handoff/test_skill_md__plan_model_handoff_contract.py'),
            ('ai/codex/config.toml', 'tests/shell/zsh/alias/test_notification_zsh__notification_suppression.py'),
            ('ai/codex/config.toml', 'tests/terminal/herdr/plugins/notify_rich/test_codex_monthly_credit.py'),
            ('ai/codex/_AGENTS.md', 'tests/ai/codex/test_codex_base_md__plan_review_criteria.py'),
            ('ai/common/skills/plan-review/references/codex.md', 'tests/ai/codex/test_codex_base_md__plan_review_criteria.py'),
            ('ai/codex/skills/config-audit/SKILL.md', 'tests/ai/common/config_audit_subagents/test_orchestrator_core_md__audit_report_contract.py'),
            ('shell/common/pr/generate_audit_report.py', 'tests/ai/common/config_audit_subagents/test_orchestrator_core_md__audit_report_contract.py'),
            ('shell/common/pr/serve_review_report.py', 'tests/ai/common/config_audit_subagents/test_orchestrator_core_md__audit_report_contract.py'),
            ('shell/common/pr/serve_review_report.py', 'tests/ai/common/test_audit_fix_core_md__audit_fix_contract.py'),
            ('ai/common/pr_review_subagents/verifier_core.md', 'tests/ai/common/pr_review_subagents/test_orchestrator_core_md__adversarial_verification.py'),
            ('ai/common/pr_review_verify.md', 'tests/ai/common/pr_review_subagents/test_orchestrator_core_md__adversarial_verification.py'),
            ('ai/codex/codex_base.md', 'tests/ai/common/shared_skills/herdr_tab_label/test_skill_md__herdr_tab_label_skill.py'),
            ('ai/codex/codex_base.md', 'tests/mac/scripts/test_common_sh__codex_agents_sync.py'),
            ('ai/common/shared_skills/worktree-task/SKILL.md', 'tests/ai/common/shared_skills/herdr_tab_label/test_skill_md__herdr_tab_label_skill.py'),
            ('ai/common/prompt_base.md', 'tests/ai/common/skills/plan_review/test_skill_md__progressive_disclosure.py'),
            ('ai/common/prompt_base.md', 'tests/mac/scripts/test_common_sh__codex_agents_sync.py'),
            ('ai/claude/agents/audit-fix-considerer.md', 'tests/ai/common/test_audit_fix_core_md__audit_fix_contract.py'),
            ('ai/claude/skills/audit-fix/SKILL.md', 'tests/ai/common/test_audit_fix_core_md__audit_fix_contract.py'),
            ('ai/codex/skills/audit-fix/SKILL.md', 'tests/ai/common/test_audit_fix_core_md__audit_fix_contract.py'),
            ('ai/codex/skills/audit-fix/skill_head.md', 'tests/ai/common/test_audit_fix_core_md__audit_fix_contract.py'),
            ('ai/common/audit_fix_subagents/considerer_core.md', 'tests/ai/common/test_audit_fix_core_md__audit_fix_contract.py'),
            ('ai/common/audit_fix_subagents/designer_core.md', 'tests/ai/common/test_audit_fix_core_md__audit_fix_contract.py'),
            ('ai/common/audit_fix_subagents/implementer_core.md', 'tests/ai/common/test_audit_fix_core_md__audit_fix_contract.py'),
            ('ai/gemini/commands/audit-fix.toml', 'tests/ai/common/test_audit_fix_core_md__audit_fix_contract.py'),
            ('ai/codex/skills/pr-body/SKILL.md', 'tests/ai/common/test_pr_body_core_md__change_summary.py'),
            ('ai/codex/skills/pr-comment-post/SKILL.md', 'tests/ai/common/test_pr_post_mechanics_core_md__out_of_range_always_individual.py'),
            ('ai/codex/skills/review-post/SKILL.md', 'tests/ai/common/test_pr_post_mechanics_core_md__out_of_range_always_individual.py'),
            ('ai/codex/skills/review-post/SKILL.md', 'tests/ai/common/test_review_post_core_md__carryover_line.py'),
            ('ai/codex/skills/review-post/SKILL.md', 'tests/ai/common/test_review_post_core_md__inline_body_contract.py'),
            ('ai/common/review_post_core.md', 'tests/ai/common/test_pr_post_mechanics_core_md__out_of_range_always_individual.py'),
            ('ai/common/pr_review_subagents/orchestrator_core.md', 'tests/ai/common/test_pr_review_core_md__perspectives.py'),
            ('ai/common/pr_body_format.md', 'tests/ai/common/test_pr_review_scope_md__review_guide_and_incremental.py'),
            ('ai/claude/skills/pr-review-subagents/SKILL.md', 'tests/ai/common/test_pr_review_verify_md__adapters.py'),
            ('ai/claude/skills/pr-review-subagents/SKILL.md', 'tests/ai/common/test_prompt_base_md__ai_pr_effort_policy.py'),
            ('ai/claude/skills/pr-review/SKILL.md', 'tests/ai/common/test_pr_review_verify_md__adapters.py'),
            ('ai/gemini/commands/pr-review-subagents.toml', 'tests/ai/common/test_pr_review_verify_md__adapters.py'),
            ('ai/gemini/commands/pr-review.toml', 'tests/ai/common/test_pr_review_verify_md__adapters.py'),
            ('shell/zsh/alias/ai/claude.zsh', 'tests/ai/common/test_prompt_base_md__ai_pr_effort_policy.py'),
            ('ai/common/skills/prompt-self-improvement/SKILL.md', 'tests/ai/common/test_prompt_base_md__always_on_skill_pointers.py'),
            ('ai/claude/skills/review-merge/SKILL.md', 'tests/ai/common/test_review_merge_core_md__carryover_values.py'),
            ('ai/codex/skills/review-merge/SKILL.md', 'tests/ai/common/test_review_merge_core_md__carryover_values.py'),
            ('shell/common/pr/generate_review_report.py', 'tests/ai/common/test_review_merge_core_md__carryover_values.py'),
            ('shell/common/pr/generate_review_report.py', 'tests/ai/common/test_review_post_core_md__carryover_line.py'),
            ('ai/claude/skills/review-post/SKILL.md', 'tests/ai/common/test_review_post_core_md__carryover_line.py'),
            ('ai/claude/skills/review-post/SKILL.md', 'tests/ai/common/test_review_post_core_md__inline_body_contract.py'),
            ('ai/common/pr_post_mechanics_core.md', 'tests/ai/common/test_review_post_core_md__carryover_line.py'),
            ('ai/common/pr_post_mechanics_core.md', 'tests/ai/common/test_review_post_core_md__inline_body_contract.py'),
            ('ai/common/review_merge_core.md', 'tests/ai/common/test_review_post_core_md__carryover_line.py'),
            ('shell/zsh/managed.zsh', 'tests/mac/initialization/test_git_setup_sh__worktrunk_setup.py'),
            ('shell/zsh/managed.zsh', 'tests/mac/scripts/test_dev_tools_sh__mdv_install.py'),
            ('ai/claude/settings.json', 'tests/mac/scripts/test_dev_tools_sh__mdv_install.py'),
            ('ai/claude/settings.json', 'tests/mac/scripts/test_herdr_sh__herdr_integrations.py'),
            ('ai/claude/settings.json', 'tests/shell/zsh/alias/test_notification_zsh__notification_suppression.py'),
            ('mac/initialization/dev_tools.sh', 'tests/mac/scripts/test_dev_tools_sh__mdv_install.py'),
            ('mac/update', 'tests/mac/scripts/test_dev_tools_sh__mdv_install.py'),
            ('ai/codex/hooks.json', 'tests/mac/scripts/test_herdr_sh__herdr_integrations.py'),
            ('terminal/herdr/config.toml', 'tests/mac/scripts/test_herdr_sh__herdr_setup.py'),
            ('terminal/herdr/config.toml', 'tests/shell/herdr/test_herdr_open_zoxide_picker_sh.py'),
            ('terminal/herdr/config.toml', 'tests/terminal/herdr/plugins/notify_rich/test_codex_monthly_credit.py'),
            ('ai/gemini/settings.json', 'tests/shell/zsh/alias/ai/test_gemini_zsh__cli_version_pin.py'),
            ('ai/gemini/settings.json', 'tests/shell/zsh/alias/test_notification_zsh__notification_suppression.py'),
        )
        for source, test in cases:
            with self.subTest(source=source, test=test):
                selected, unmatched = run_tests.selected_test_paths([source])
                self.assertIn(run_tests.REPO_ROOT / test, selected)
                self.assertFalse(unmatched)

    def test_repository_references_select_the_reader(self):
        cases = (
            ('ai/claude/agents_src/rules_common.md', 'tests/ai/codex/agents_src/test_rules_common_md__confidence.py'),
            ('ai/gemini/agents_src/rules_common.md', 'tests/ai/codex/agents_src/test_rules_common_md__confidence.py'),
            ('ai/codex/skills/pr-body/SKILL.md', 'tests/ai/codex/skills/pr_body/test_skill_head_md__description_scope.py'),
            ('ai/codex/skills/pr-body/SKILL.md', 'tests/ai/common/test_pr_body_format_md__readability_rules.py'),
            ('ai/codex/skills/pr-comment-review/SKILL.md', 'tests/ai/codex/skills/pr_comment_review/test_skill_head_md__description_scope.py'),
            ('mac/scripts/common.sh', 'tests/ai/common/audit_fix_subagents/test_designer_core_md__audit_fix_agent_generation.py'),
            ('mac/scripts/common.sh', 'tests/ai/common/pr_review_subagents/test_orchestrator_core_md__adversarial_verification.py'),
            ('mac/scripts/common.sh', 'tests/ai/common/review_fix_subagents/test_designer_core_md__review_fix_agent_generation.py'),
            ('mac/scripts/common.sh', 'tests/ai/common/shared_skills/worktree_task/test_skill_md__worktree_task_skill.py'),
            ('CLAUDE.md', 'tests/ai/common/shared_skills/worktree_task/test_skill_md__worktree_task_skill.py'),
            ('ai/common/skills/prompt-self-improvement/SKILL.md', 'tests/ai/common/shared_skills/worktree_task/test_skill_md__worktree_task_skill.py'),
            ('ai/claude/skills/grilling/SKILL.md', 'tests/ai/common/skills/test_skill_description_scope.py'),
            ('ai/codex/skills/dig/SKILL.md', 'tests/ai/common/skills/test_skill_description_scope.py'),
            ('ai/codex/skills/grilling/SKILL.md', 'tests/ai/common/skills/test_skill_description_scope.py'),
            ('ai/codex/skills/pr-body/skill_head.md', 'tests/ai/common/skills/test_skill_description_scope.py'),
            ('ai/codex/skills/pr-comment-review/skill_head.md', 'tests/ai/common/skills/test_skill_description_scope.py'),
            ('ai/common/shared_skills/branch-pr-task/SKILL.md', 'tests/ai/common/skills/test_skill_description_scope.py'),
            ('ai/common/shared_skills/worktree-task/SKILL.md', 'tests/ai/common/skills/test_skill_description_scope.py'),
            ('ai/common/skills/fact-based/SKILL.md', 'tests/ai/common/skills/test_skill_description_scope.py'),
            ('ai/common/skills/second-opinion/SKILL.md', 'tests/ai/common/skills/test_skill_description_scope.py'),
            ('ai/gemini/skills/fact-based/skill_head.md', 'tests/ai/common/skills/test_skill_description_scope.py'),
            ('ai/codex/skills/pr-create-by-branch/SKILL.md', 'tests/ai/common/test_pr_body_format_md__readability_rules.py'),
            ('ai/codex/skills/pr-create-by-branch/SKILL.md', 'tests/ai/common/test_pr_create_by_branch_core_md__reviewer_reminder.py'),
            ('ai/common/pr_comment_implement/analysis-design.md', 'tests/ai/common/test_pr_comment_implement_core_md__comment_disposition.py'),
            ('ai/common/pr_comment_implement/analysis-design.md', 'tests/ai/common/test_pr_comment_implement_core_md__final_action_selection.py'),
            ('ai/common/pr_comment_implement/analysis-design.md', 'tests/ai/common/test_pr_comment_implement_core_md__project_workflow_isolation.py'),
            ('ai/common/pr_comment_implement/analysis-design.md', 'tests/ai/common/test_pr_comment_implement_core_md__reaction_state_verification.py'),
            ('ai/common/pr_comment_implement/analysis-design.md', 'tests/ai/common/test_pr_comment_implement_core_md__standalone_reply_header.py'),
            ('ai/common/pr_comment_implement/finalization.md', 'tests/ai/common/test_pr_comment_implement_core_md__comment_disposition.py'),
            ('ai/common/pr_comment_implement/finalization.md', 'tests/ai/common/test_pr_comment_implement_core_md__final_action_selection.py'),
            ('ai/common/pr_comment_implement/finalization.md', 'tests/ai/common/test_pr_comment_implement_core_md__project_workflow_isolation.py'),
            ('ai/common/pr_comment_implement/finalization.md', 'tests/ai/common/test_pr_comment_implement_core_md__reaction_state_verification.py'),
            ('ai/common/pr_comment_implement/finalization.md', 'tests/ai/common/test_pr_comment_implement_core_md__standalone_reply_header.py'),
            ('ai/common/pr_comment_implement/implementation.md', 'tests/ai/common/test_pr_comment_implement_core_md__comment_disposition.py'),
            ('ai/common/pr_comment_implement/implementation.md', 'tests/ai/common/test_pr_comment_implement_core_md__final_action_selection.py'),
            ('ai/common/pr_comment_implement/implementation.md', 'tests/ai/common/test_pr_comment_implement_core_md__project_workflow_isolation.py'),
            ('ai/common/pr_comment_implement/implementation.md', 'tests/ai/common/test_pr_comment_implement_core_md__reaction_state_verification.py'),
            ('ai/common/pr_comment_implement/implementation.md', 'tests/ai/common/test_pr_comment_implement_core_md__standalone_reply_header.py'),
            ('ai/claude/skills/pr-comment-implement/SKILL.md', 'tests/ai/common/test_pr_comment_implement_core_md__final_action_selection.py'),
            ('ai/claude/skills/pr-comment-implement/SKILL.md', 'tests/ai/common/test_pr_comment_implement_core_md__progressive_disclosure.py'),
            ('ai/claude/skills/pr-comment-implement/SKILL.md', 'tests/ai/common/test_pr_comment_implement_core_md__standalone_reply_header.py'),
            ('ai/codex/skills/pr-comment-implement/SKILL.md', 'tests/ai/common/test_pr_comment_implement_core_md__final_action_selection.py'),
            ('ai/gemini/commands/pr-comment-implement.toml', 'tests/ai/common/test_pr_comment_implement_core_md__final_action_selection.py'),
            ('ai/gemini/commands/pr-comment-implement.toml', 'tests/ai/common/test_pr_comment_implement_core_md__progressive_disclosure.py'),
            ('ai/gemini/commands/pr-comment-implement.toml', 'tests/ai/common/test_pr_comment_implement_core_md__standalone_reply_header.py'),
            ('ai/codex/skills/pr-comment-implement/skill_head.md', 'tests/ai/common/test_pr_comment_implement_core_md__progressive_disclosure.py'),
            ('ai/claude/skills/pr-create-by-branch/SKILL.md', 'tests/ai/common/test_pr_create_by_branch_core_md__reviewer_reminder.py'),
            ('ai/claude/agents/pr-review-verifier.md', 'tests/ai/common/test_pr_review_verify_md__adapters.py'),
            ('ai/claude/agents/pr-review-verifier.md', 'tests/ai/common/test_prompt_base_md__ai_pr_effort_policy.py'),
            ('ai/codex/agents/pr_review_verifier.toml', 'tests/ai/common/test_pr_review_verify_md__adapters.py'),
            ('ai/codex/agents/pr_review_verifier.toml', 'tests/ai/common/test_prompt_base_md__ai_pr_effort_policy.py'),
            ('ai/codex/skills/pr-review-subagents/SKILL.md', 'tests/ai/common/test_pr_review_verify_md__adapters.py'),
            ('ai/codex/skills/pr-review/SKILL.md', 'tests/ai/common/test_pr_review_verify_md__adapters.py'),
            ('ai/gemini/agents/pr-review-verifier.md', 'tests/ai/common/test_pr_review_verify_md__adapters.py'),
            ('ai/claude/agents_src/pr_review_verify/head_verifier.md', 'tests/ai/common/test_prompt_base_md__ai_pr_effort_policy.py'),
            ('ai/codex/agents_src/pr_review_verify/head_verifier.toml', 'tests/ai/common/test_prompt_base_md__ai_pr_effort_policy.py'),
            ('shell/common/alias/claude.sh', 'tests/ai/common/test_prompt_base_md__ai_pr_effort_policy.py'),
            ('shell/common/alias/claude.sh', 'tests/shell/zsh/filter/test_github_zsh__pr_reviewer_reminder.py'),
            ('shell/zsh/alias/ai/ai.zsh', 'tests/ai/common/test_prompt_base_md__ai_pr_effort_policy.py'),
            ('shell/zsh/alias/ai/ai.zsh', 'tests/shell/zsh/alias/ai/test_gemini_zsh__pr_review_natural_language.py'),
            ('shell/zsh/alias/ai/ai.zsh', 'tests/shell/zsh/alias/test_git_zsh__repository_worktree_navigation.py'),
            ('shell/zsh/alias/ai/ai.zsh', 'tests/shell/zsh/filter/test_ai_zsh__freview_worktree.py'),
            ('shell/zsh/alias/ai/ai.zsh', 'tests/shell/zsh/filter/test_git_zsh__fgwt_worktree_navigation.py'),
            ('shell/zsh/alias/ai/gemini.zsh', 'tests/ai/common/test_prompt_base_md__ai_pr_effort_policy.py'),
            ('ai/claude/_CLAUDE.md', 'tests/ai/common/test_prompt_base_md__always_on_skill_pointers.py'),
            ('ai/codex/codex_base.md', 'tests/ai/common/test_prompt_base_md__always_on_skill_pointers.py'),
            ('ai/codex/codex_base.md', 'tests/mac/scripts/ai/test_rtk_sh__rtk_setup.py'),
            ('ai/common/skills/task-completion/SKILL.md', 'tests/ai/common/test_prompt_base_md__always_on_skill_pointers.py'),
            ('ai/common/skills/task-completion/SKILL.md', 'tests/ai/common/test_prompt_base_md__commit_confirmation.py'),
            ('ai/gemini/_GEMINI.md', 'tests/ai/common/test_prompt_base_md__always_on_skill_pointers.py'),
            ('ai/gemini/skills/fact-based/SKILL.md', 'tests/ai/gemini/skills/fact_based/test_skill_head_md__description_scope.py'),
            ('mac/Brewfile', 'tests/mac/initialization/test_git_setup_sh__worktrunk_setup.py'),
            ('mac/Brewfile', 'tests/mac/scripts/ai/test_rtk_sh__rtk_setup.py'),
            ('shell/zsh/alias/git.zsh', 'tests/mac/initialization/test_git_setup_sh__worktrunk_setup.py'),
            ('shell/zsh/alias/utils.zsh', 'tests/mac/scripts/ai/test_codex_sh__hooks_json_setup.py'),
            ('shell/zsh/alias/utils.zsh', 'tests/mac/test_update__context_mode_setup.py'),
            ('ai/codex/_AGENTS.md', 'tests/mac/scripts/ai/test_rtk_sh__rtk_setup.py'),
            ('ai/codex/_AGENTS.md', 'tests/mac/scripts/test_common_sh__codex_agents_sync.py'),
            ('terminal/mdv/mdv-plans.css', 'tests/mac/scripts/test_dev_tools_sh__mdv_install.py'),
            ('shell/herdr/herdr_worktree_context.sh', 'tests/shell/herdr/test_herdr_open_lazygit_sh.py'),
            ('shell/herdr/herdr-popup-run.sh', 'tests/shell/herdr/test_herdr_open_zoxide_picker_sh.py'),
            ('shell/zsh/filter/ai.zsh', 'tests/shell/tmux/test_rename_window_git_sh__review_window_git_name.py'),
            ('shell/zsh/filter/ai.zsh', 'tests/shell/zsh/alias/test_git_zsh__repository_worktree_navigation.py'),
            ('mac/initialization/ai/gemini.sh', 'tests/shell/zsh/alias/ai/test_gemini_zsh__cli_version_pin.py'),
            ('mac/updates/gemini.sh', 'tests/shell/zsh/alias/ai/test_gemini_zsh__cli_version_pin.py'),
            ('shell/zsh/alias/tmux.zsh', 'tests/shell/zsh/alias/test_git_zsh__repository_worktree_navigation.py'),
            ('shell/zsh/filter/git.zsh', 'tests/shell/zsh/alias/test_git_zsh__repository_worktree_navigation.py'),
            ('shell/zsh/filter/git.zsh', 'tests/shell/zsh/filter/test_ai_zsh__freview_worktree.py'),
            ('shell/zsh/filter/git.zsh', 'tests/shell/zsh/filter/test_github_zsh__compare_url_picker.py'),
            ('ai/gemini/.env', 'tests/shell/zsh/alias/test_notification_zsh__notification_suppression.py'),
            ('shell/tmux/ai_notification_hook_common.sh', 'tests/shell/zsh/alias/test_notification_zsh__notification_suppression.py'),
            ('shell/bash/managed.bash', 'tests/shell/zsh/alias/test_utils_zsh__shell_loader_setup.py'),
            ('shell/zsh/managed.zsh', 'tests/shell/zsh/alias/test_utils_zsh__shell_loader_setup.py'),
            ('shell/zsh/alias/gh.zsh', 'tests/shell/zsh/filter/test_ai_zsh__freview_worktree.py'),
            ('shell/zsh/alias/gh.zsh', 'tests/shell/zsh/filter/test_github_zsh__pr_picker_label.py'),
            ('shell/zsh/alias/gh.zsh', 'tests/shell/zsh/filter/test_github_zsh__pr_reviewer_reminder.py'),
            ('shell/zsh/alias/other.zsh', 'tests/shell/zsh/filter/test_ai_zsh__freview_worktree.py'),
            ('shell/zsh/filter/github.zsh', 'tests/shell/zsh/filter/test_ai_zsh__freview_worktree.py'),
            ('shell/herdr/herdr_status_icon.sh', 'tests/terminal/herdr/plugins/notify_rich/test_herdr_plugin_toml__herdr_plugin_notify.py'),
            ('terminal/herdr/plugins/notify-rich/notify-on-agent-status.sh', 'tests/terminal/herdr/plugins/notify_rich/test_herdr_plugin_toml__herdr_plugin_notify.py'),
            ('ai/claude/hooks/claude-hook.py', 'tests/terminal/herdr/test_config_toml__herdr_notifications.py'),
            ('ai/claude/hooks/stop-send-notification.sh', 'tests/terminal/herdr/test_config_toml__herdr_notifications.py'),
            ('ai/codex/hooks/codex-hook.py', 'tests/terminal/herdr/test_config_toml__herdr_notifications.py'),
            ('ai/codex/hooks/codex-stop-notification.sh', 'tests/terminal/herdr/test_config_toml__herdr_notifications.py'),
            ('ai/gemini/hooks/gemini-hook.py', 'tests/terminal/herdr/test_config_toml__herdr_notifications.py'),
            ('ai/gemini/hooks/notification.sh', 'tests/terminal/herdr/test_config_toml__herdr_notifications.py'),
            ('shell/tmux/herdr_review_sessions.py', 'tests/terminal/herdr/test_config_toml__herdr_notifications.py'),
        )
        for source, test in cases:
            with self.subTest(source=source, test=test):
                selected, unmatched = run_tests.selected_test_paths([source])
                self.assertIn(run_tests.REPO_ROOT / test, selected)
                self.assertFalse(unmatched)

    def test_joined_paths_select_the_reader(self):
        cases = (
            ('ai/codex/skills/pr-comment-implement/references/analysis-design.md', 'tests/ai/common/test_pr_comment_implement_core_md__comment_disposition.py'),
            ('ai/codex/skills/pr-comment-implement/references/analysis-design.md', 'tests/ai/common/test_pr_comment_implement_core_md__project_workflow_isolation.py'),
            ('ai/codex/skills/pr-comment-implement/references/finalization.md', 'tests/ai/common/test_pr_comment_implement_core_md__final_action_selection.py'),
            ('ai/codex/skills/pr-comment-implement/references/finalization.md', 'tests/ai/common/test_pr_comment_implement_core_md__reaction_state_verification.py'),
            ('ai/codex/skills/pr-comment-implement/references/finalization.md', 'tests/ai/common/test_pr_comment_implement_core_md__standalone_reply_header.py'),
            ('shell/tmux/tmux_window_name.sh', 'tests/shell/tmux/test_tmux_window_name.py'),
        )
        for source, test in cases:
            with self.subTest(source=source, test=test):
                selected, unmatched = run_tests.selected_test_paths([source])
                self.assertIn(run_tests.REPO_ROOT / test, selected)
                self.assertFalse(unmatched)

    def test_variable_paths_select_the_reader(self):
        cases = (
            ('ai/codex/skills/audit-fix/skill_head.md', 'tests/ai/codex/test_codex_base_md__user_confirmation.py'),
            ('ai/codex/skills/config-audit/skill_head.md', 'tests/ai/codex/test_codex_base_md__user_confirmation.py'),
            ('ai/codex/skills/dig/SKILL.md', 'tests/ai/codex/test_codex_base_md__user_confirmation.py'),
            ('ai/codex/skills/grilling/SKILL.md', 'tests/ai/codex/test_codex_base_md__user_confirmation.py'),
            ('ai/codex/skills/plan-model-handoff/SKILL.md', 'tests/ai/codex/test_codex_base_md__user_confirmation.py'),
            ('ai/codex/skills/pr-create-by-branch/skill_head.md', 'tests/ai/codex/test_codex_base_md__user_confirmation.py'),
            ('ai/codex/skills/review-fix/skill_head.md', 'tests/ai/codex/test_codex_base_md__user_confirmation.py'),
            ('ai/common/skills/plan-review/references/codex.md', 'tests/ai/codex/test_codex_base_md__user_confirmation.py'),
            ('ai/claude/skills/pr-comment-implement/SKILL.md', 'tests/ai/common/pr_comment_implement/test_finalization_md__workflow_contract.py'),
            ('ai/codex/skills/pr-comment-implement/skill_head.md', 'tests/ai/common/pr_comment_implement/test_finalization_md__workflow_contract.py'),
            ('ai/gemini/commands/pr-comment-implement.toml', 'tests/ai/common/pr_comment_implement/test_finalization_md__workflow_contract.py'),
            ('ai/claude/_CLAUDE.md', 'tests/ai/common/test_genshijin_activate_md__genshijin_prompt_integration.py'),
            ('ai/common/genshijin-file-policy.md', 'tests/ai/common/test_genshijin_activate_md__genshijin_prompt_integration.py'),
            ('ai/gemini/_GEMINI.md', 'tests/ai/common/test_genshijin_activate_md__genshijin_prompt_integration.py'),
            ('mac/scripts/common.sh', 'tests/ai/common/test_genshijin_activate_md__genshijin_prompt_integration.py'),
            ('mac/updates/codex.sh', 'tests/ai/common/test_genshijin_activate_md__genshijin_prompt_integration.py'),
            ('mac/updates/gemini.sh', 'tests/ai/common/test_genshijin_activate_md__genshijin_prompt_integration.py'),
            ('ai/claude/skills/pr-review-subagents/SKILL.md', 'tests/ai/common/test_pr_review_scope_md__review_guide_and_incremental.py'),
            ('ai/claude/skills/pr-review/SKILL.md', 'tests/ai/common/test_pr_review_scope_md__review_guide_and_incremental.py'),
            ('ai/codex/skills/pr-review-subagents/SKILL.md', 'tests/ai/common/test_pr_review_scope_md__review_guide_and_incremental.py'),
            ('ai/codex/skills/pr-review/SKILL.md', 'tests/ai/common/test_pr_review_scope_md__review_guide_and_incremental.py'),
            ('ai/gemini/commands/pr-review-subagents.toml', 'tests/ai/common/test_pr_review_scope_md__review_guide_and_incremental.py'),
            ('ai/gemini/commands/pr-review.toml', 'tests/ai/common/test_pr_review_scope_md__review_guide_and_incremental.py'),
            ('ai/claude/skills/review-fix/SKILL.md', 'tests/ai/common/test_review_fix_core_md__pr_body_update.py'),
            ('ai/codex/skills/review-fix/skill_head.md', 'tests/ai/common/test_review_fix_core_md__pr_body_update.py'),
            ('shell/tmux/ai_notification_hook_common.sh', 'tests/ai/gemini/hooks/test_notification_sh__gemini_herdr_notification.py'),
            ('shell/tmux/ai_notification_sound.sh', 'tests/ai/gemini/hooks/test_notification_sh__gemini_herdr_notification.py'),
            ('shell/tmux/ai_notification_summary.sh', 'tests/ai/gemini/hooks/test_notification_sh__gemini_herdr_notification.py'),
            ('shell/tmux/gemini_context_usage.py', 'tests/ai/gemini/hooks/test_notification_sh__gemini_herdr_notification.py'),
            ('shell/tmux/gemini_transcript_summary.jq', 'tests/ai/gemini/hooks/test_notification_sh__gemini_herdr_notification.py'),
            ('mac/initialization/ai/codex.sh', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('mac/updates/codex.sh', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('mac/initialization/ai/codex.sh', 'tests/mac/scripts/ai/test_codex_sh__hooks_json_setup.py'),
            ('mac/updates/codex.sh', 'tests/mac/scripts/ai/test_codex_sh__hooks_json_setup.py'),
            ('mac/updates/claude.sh', 'tests/mac/scripts/test_common_sh__herdr_skill_sync.py'),
            ('ai/claude/_CLAUDE.md', 'tests/mac/scripts/test_dev_tools_sh__mdv_install.py'),
            ('ai/codex/_AGENTS.md', 'tests/mac/scripts/test_dev_tools_sh__mdv_install.py'),
            ('ai/codex/codex_base.md', 'tests/mac/scripts/test_dev_tools_sh__mdv_install.py'),
            ('ai/common/prompt_base.md', 'tests/mac/scripts/test_dev_tools_sh__mdv_install.py'),
            ('mac/initialization/NOTES.md', 'tests/mac/scripts/test_dev_tools_sh__mdv_install.py'),
            ('mac/Brewfile', 'tests/mac/scripts/test_herdr_sh__herdr_setup.py'),
            ('mac/initialization/herdr.sh', 'tests/mac/scripts/test_herdr_sh__herdr_setup.py'),
            ('mac/initialization/initialize', 'tests/mac/scripts/test_herdr_sh__herdr_setup.py'),
            ('mac/initialization/tmux.sh', 'tests/mac/scripts/test_herdr_sh__herdr_setup.py'),
            ('mac/update', 'tests/mac/scripts/test_herdr_sh__herdr_setup.py'),
            ('mac/updates/herdr.sh', 'tests/mac/scripts/test_herdr_sh__herdr_setup.py'),
            ('shell/zsh/managed.zsh', 'tests/mac/scripts/test_herdr_sh__herdr_setup.py'),
            ('ai/claude/settings.json', 'tests/mac/test_update__context_mode_setup.py'),
            ('ai/codex/config.toml', 'tests/mac/test_update__context_mode_setup.py'),
            ('mac/scripts/ai/claude.sh', 'tests/mac/test_update__context_mode_setup.py'),
            ('mac/scripts/ai/codex.sh', 'tests/mac/test_update__context_mode_setup.py'),
            ('mac/scripts/ai/gemini.sh', 'tests/mac/test_update__context_mode_setup.py'),
            ('mac/scripts/common.sh', 'tests/mac/test_update__context_mode_setup.py'),
            ('mac/updates/codex.sh', 'tests/mac/test_update__context_mode_setup.py'),
            ('mac/updates/gemini.sh', 'tests/mac/test_update__context_mode_setup.py'),
            ('ai/claude/hooks/stop-send-notification.sh', 'tests/shell/zsh/alias/test_notification_zsh__notification_suppression.py'),
            ('ai/codex/hooks/codex-stop-notification.sh', 'tests/shell/zsh/alias/test_notification_zsh__notification_suppression.py'),
            ('ai/gemini/hooks/notification.sh', 'tests/shell/zsh/alias/test_notification_zsh__notification_suppression.py'),
            ('mac/initialization/ai/gemini.sh', 'tests/shell/zsh/alias/test_notification_zsh__notification_suppression.py'),
            ('mac/updates/gemini.sh', 'tests/shell/zsh/alias/test_notification_zsh__notification_suppression.py'),
            ('ai/codex/hooks/codex_hook_common.py', 'tests/terminal/herdr/plugins/notify_rich/test_herdr_plugin_toml__herdr_plugin_notify.py'),
            ('shell/tmux/ai_notification_summary.sh', 'tests/terminal/herdr/plugins/notify_rich/test_herdr_plugin_toml__herdr_plugin_notify.py'),
            ('shell/tmux/claude_transcript_analyze.py', 'tests/terminal/herdr/plugins/notify_rich/test_herdr_plugin_toml__herdr_plugin_notify.py'),
            ('shell/tmux/herdr_review_sessions.py', 'tests/terminal/herdr/plugins/notify_rich/test_herdr_plugin_toml__herdr_plugin_notify.py'),
            ('shell/tmux/ai_notification_hook_common.sh', 'tests/terminal/herdr/test_config_toml__herdr_notifications.py'),
            ('shell/tmux/ai_notification_sound.sh', 'tests/terminal/herdr/test_config_toml__herdr_notifications.py'),
            ('shell/tmux/ai_notification_summary.sh', 'tests/terminal/herdr/test_config_toml__herdr_notifications.py'),
            ('shell/tmux/gemini_context_usage.py', 'tests/terminal/herdr/test_config_toml__herdr_notifications.py'),
            ('shell/tmux/gemini_transcript_summary.jq', 'tests/terminal/herdr/test_config_toml__herdr_notifications.py'),
        )
        for source, test in cases:
            with self.subTest(source=source, test=test):
                selected, unmatched = run_tests.selected_test_paths([source])
                self.assertIn(run_tests.REPO_ROOT / test, selected)
                self.assertFalse(unmatched)

    def test_constant_directories_select_the_reader(self):
        cases = (
            ('ai/claude/mods/rich-output/.claude-plugin/plugin.json', 'tests/ai/claude/test_settings_json__rich_output_mod.py'),
            ('ai/claude/mods/rich-output/hooks/hooks.json', 'tests/ai/claude/test_settings_json__rich_output_mod.py'),
            ('ai/claude/mods/rich-output/hooks/register.tsx', 'tests/ai/claude/test_settings_json__rich_output_mod.py'),
            ('ai/claude/mods/slash-anywhere/hooks/register.ts', 'tests/ai/claude/test_settings_json__slash_anywhere_mod.py'),
            ('ai/common/pr_comment_implement/analysis-design.md', 'tests/ai/common/test_pr_comment_implement_core_md__progressive_disclosure.py'),
            ('ai/common/pr_comment_implement/finalization.md', 'tests/ai/common/test_pr_comment_implement_core_md__progressive_disclosure.py'),
            ('ai/common/pr_comment_implement/implementation.md', 'tests/ai/common/test_pr_comment_implement_core_md__progressive_disclosure.py'),
            ('ai/common/shared_skills/branch-pr-task/agents/openai.yaml', 'tests/ai/common/shared_skills/branch_pr_task/test_skill_md__branch_pr_task_skill.py'),
            ('ai/common/shared_skills/herdr-tab-label/agents/openai.yaml', 'tests/ai/common/shared_skills/herdr_tab_label/test_skill_md__herdr_tab_label_skill.py'),
            ('ai/common/shared_skills/pr-verify/agents/openai.yaml', 'tests/ai/common/shared_skills/pr_verify/test_skill_md__pr_verify_skill.py'),
            ('ai/common/shared_skills/worktree-task/agents/openai.yaml', 'tests/ai/common/shared_skills/worktree_task/test_skill_md__worktree_task_skill.py'),
            ('ai/common/skills/plan-review/references/browser.md', 'tests/ai/common/skills/plan_review/test_skill_md__progressive_disclosure.py'),
        )
        for source, test in cases:
            with self.subTest(source=source, test=test):
                selected, unmatched = run_tests.selected_test_paths([source])
                self.assertIn(run_tests.REPO_ROOT / test, selected)
                self.assertFalse(unmatched)

    def test_dynamic_source_dependencies_select_the_reader(self):
        cases = (
            ('ai/codex/agents/config_auditor_default.toml', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('ai/codex/agents/config_auditor_conflict.toml', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('ai/codex/agents/config_auditor_overlap.toml', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('ai/codex/agents/config_auditor_patch.toml', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('ai/codex/agents/config_auditor_ambiguity.toml', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('ai/codex/agents/config_auditor_concise.toml', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('ai/codex/agents/audit_fix_designer.toml', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('ai/codex/agents/audit_fix_implementer.toml', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('ai/codex/agents/audit_fix_considerer.toml', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('ai/codex/agents/review_fix_designer.toml', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('ai/codex/agents/review_fix_implementer.toml', 'tests/mac/scripts/ai/test_codex_sh__config_auditor_agents.py'),
            ('mac/scripts/common.sh', 'tests/mac/updates/test_codex_sh__sourced_failure_does_not_kill_parent.py'),
            ('mac/scripts/common.sh', 'tests/mac/updates/test_herdr_sh__sourced_failure_does_not_kill_parent.py'),
            ('mac/scripts/ai/codex.sh', 'tests/mac/updates/test_codex_sh__sourced_failure_does_not_kill_parent.py'),
            ('mac/scripts/herdr.sh', 'tests/mac/updates/test_herdr_sh__sourced_failure_does_not_kill_parent.py'),
        )
        for source, test in cases:
            with self.subTest(source=source, test=test):
                selected, unmatched = run_tests.selected_test_paths([source])
                self.assertIn(run_tests.REPO_ROOT / test, selected)
                self.assertFalse(unmatched)

    def test_selection_rejects_unmapped_even_when_other_path_matches(self):
        with mock.patch.object(run_tests, "discover_test_ids", return_value=["test_run_tests.RunTestsTest.test_example"]), \
             mock.patch.object(run_tests, "load_dependency_map", return_value=({}, {})), \
             mock.patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(run_tests.main(["--paths", "tests/test_run_tests.py", "unmapped"]), 2)

    def test_exclusion_reason_and_empty_change(self):
        with mock.patch.object(run_tests, "discover_test_ids", return_value=["fake.Test.test_example"]), \
             mock.patch.object(run_tests, "load_dependency_map", return_value=({}, {"unmapped": "documentation only"})), \
             mock.patch.object(run_tests, "requires_full_suite", return_value=False), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(run_tests.main(["--paths", "unmapped"]), 0)
            self.assertIn("documentation only", output.getvalue())
            with mock.patch.object(run_tests, "changed_paths", return_value=([], False)):
                self.assertEqual(run_tests.main(["--changed"]), 0)
            self.assertIn("no tests run", output.getvalue())

    def test_git_failure_exits_with_selection_error(self):
        with mock.patch.object(run_tests, "discover_test_ids", return_value=["fake.Test.test_example"]), \
             mock.patch.object(run_tests, "load_dependency_map", return_value=({}, {})), \
             mock.patch.object(run_tests, "changed_paths", side_effect=ValueError("Git failed")), \
             mock.patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(run_tests.main(["--changed"]), 2)

    def test_selection_reports_both_convention_and_extra_dependency(self):
        source = "ai/common/config_audit_subagents/orchestrator_core.md"
        extra = "tests/ai/codex/skills/config_audit/test_skill_head_md__dispatch_contract.py"
        with mock.patch.object(run_tests, "discover_test_ids", return_value=["fake.Test.test_example"]), \
             mock.patch.object(run_tests, "load_dependency_map", return_value=({source: [extra]}, {})), \
             mock.patch.object(run_tests, "run_shards", return_value=[]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            run_tests.main(["--paths", source])
            self.assertIn("naming convention and extra dependency", output.getvalue())

    def create_test_file(self, test_dir, relative_path, class_name="ExampleTest"):
        path = test_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "import unittest\n"
            f"class {class_name}(unittest.TestCase):\n"
            "    def test_example(self): pass\n"
        )
        return path

    def test_discovers_each_test_once_in_stable_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            (test_dir / "test_zeta.py").write_text(
                "import unittest\n"
                "class ZetaTest(unittest.TestCase):\n"
                "    def test_second(self): pass\n"
            )
            (test_dir / "test_alpha.py").write_text(
                "import unittest\n"
                "class AlphaTest(unittest.TestCase):\n"
                "    def test_first(self): pass\n"
            )

            test_ids = run_tests.discover_test_ids(test_dir)

        self.assertEqual(
            test_ids,
            [
                "test_alpha.AlphaTest.test_first",
                "test_zeta.ZetaTest.test_second",
            ],
        )

    def test_partitions_all_ids_once_with_balanced_deterministic_shards(self):
        test_ids = [f"test_module.ExampleTest.test_{index:02d}" for index in range(19)]

        first = run_tests.partition_test_ids(reversed(test_ids), jobs=8)
        second = run_tests.partition_test_ids(test_ids, jobs=8)

        self.assertEqual(first, second)
        self.assertEqual(sorted(test_id for shard in first for test_id in shard), test_ids)
        self.assertEqual(len(set(test_id for shard in first for test_id in shard)), 19)
        self.assertLessEqual(max(map(len, first)) - min(map(len, first)), 1)

    def test_default_job_count_is_capped_and_handles_unknown_cpu_count(self):
        cases = ((16, 8), (4, 4), (None, 1))
        for cpu_count, expected in cases:
            with self.subTest(cpu_count=cpu_count):
                self.assertEqual(run_tests.default_job_count(cpu_count), expected)

    def test_explicit_job_count_overrides_default(self):
        self.assertEqual(run_tests.parse_args(["--jobs", "12"]).jobs, 12)

    def test_non_positive_job_count_is_rejected(self):
        for value in ("0", "-1"):
            with self.subTest(value=value):
                with self.assertRaises(SystemExit):
                    with mock.patch("sys.stderr", io.StringIO()):
                        run_tests.parse_args(["--jobs", value])

    def test_paths_argument_accepts_multiple_repo_relative_paths(self):
        args = run_tests.parse_args(
            ["--paths", "shell/tmux/example.sh", "mac/scripts/example.sh"]
        )

        self.assertEqual(args.paths, ["shell/tmux/example.sh", "mac/scripts/example.sh"])

    def test_source_path_convention_preserves_extension_and_scenarios(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            direct = self.create_test_file(test_dir, "shell/tmux/test_example_sh.py", "DirectTest")
            scenario = self.create_test_file(
                test_dir,
                "shell/tmux/test_example_sh__edge_case.py",
                "ScenarioTest",
            )

            selected, unmatched = run_tests.selected_test_paths(
                ["shell/tmux/example.sh"],
                test_dir=test_dir,
                dependency_map={},
            )

        self.assertEqual(selected, [direct, scenario])
        self.assertEqual(unmatched, [])

    def test_python_and_dot_directories_have_deterministic_test_paths(self):
        self.assertEqual(
            run_tests.test_path_prefix_for_source("shell/tmux/example.py"),
            run_tests.TEST_DIR / "shell" / "tmux" / "test_example",
        )
        self.assertEqual(
            run_tests.test_path_prefix_for_source(".claude/skills/worktree-task/SKILL.md"),
            run_tests.TEST_DIR
            / "dot_claude"
            / "skills"
            / "worktree_task"
            / "test_skill_md",
        )

    def test_select_test_ids_deduplicates_direct_and_dependency_tests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            test_dir = repo_root / "tests"
            test_file = self.create_test_file(test_dir, "shell/test_example_sh.py")
            test_ids = ["shell.test_example_sh.ExampleTest.test_example"]
            with mock.patch.object(run_tests, "REPO_ROOT", repo_root):
                selected, paths, unmatched = run_tests.select_test_ids(
                    ["shell/example.sh"],
                    test_ids,
                    test_dir=test_dir,
                    dependency_map={"shell/example.sh": ["tests/shell/test_example_sh.py"]},
                )

        self.assertEqual(selected, test_ids)
        self.assertEqual(paths, [test_file])
        self.assertEqual(unmatched, [])

    def test_unmapped_paths_and_invalid_dependency_targets_are_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            test_dir = repo_root / "tests"
            with mock.patch.object(run_tests, "REPO_ROOT", repo_root):
                selected, paths, unmatched = run_tests.select_test_ids(
                    ["shell/no_test.sh"], [], test_dir=test_dir, dependency_map={}
                )
                self.assertEqual((selected, paths, unmatched), ([], [], ["shell/no_test.sh"]))
                with self.assertRaisesRegex(ValueError, "missing tests"):
                    run_tests.selected_test_paths(
                        ["shell/example.sh"],
                        test_dir=test_dir,
                        dependency_map={"shell/example.sh": ["tests/missing.py"]},
                    )

        with self.assertRaises(ValueError):
            run_tests.normalize_repo_path("../outside.sh")

    def test_result_status_preserves_single_and_multiple_failures(self):
        success = run_tests.ShardResult(1, 2, 0, 0.1, "ok")
        failure_one = run_tests.ShardResult(2, 2, 1, 0.1, "first failure")
        failure_two = run_tests.ShardResult(3, 2, 2, 0.1, "second failure")
        cases = (
            ([success], 0, ""),
            ([success, failure_one], 1, "first failure"),
            ([failure_one, failure_two], 1, "second failure"),
        )
        for results, expected_status, expected_diagnostic in cases:
            with self.subTest(result_count=len(results), status=expected_status):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
                    status = run_tests.print_results(results, total_duration=0.2)
                self.assertEqual(status, expected_status)
                self.assertIn(expected_diagnostic, stderr.getvalue())

    def test_launch_failure_stops_started_shards(self):
        started_process = mock.Mock()
        started_process.pid = 123
        output = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
        calls = 0

        def popen_factory(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                kwargs["stdout"].close()
                return started_process
            raise OSError("launch failed")

        stopped = []
        with mock.patch.object(tempfile, "TemporaryFile", return_value=output):
            with self.assertRaisesRegex(run_tests.ShardLaunchError, "shard 2"):
                run_tests.run_shards(
                    [["test_one"], ["test_two"]],
                    popen_factory=popen_factory,
                    stop_processes=lambda runs: stopped.extend(runs),
                )

        self.assertEqual([run.process for run in stopped], [started_process])

    def test_keyboard_interrupt_stops_all_started_shards(self):
        processes = []

        def popen_factory(*args, **kwargs):
            process = mock.Mock()
            process.pid = len(processes) + 100
            process.poll.side_effect = KeyboardInterrupt
            processes.append(process)
            return process

        stopped = []
        with self.assertRaises(KeyboardInterrupt):
            run_tests.run_shards(
                [["test_one"], ["test_two"]],
                popen_factory=popen_factory,
                stop_processes=lambda runs: stopped.extend(runs),
            )

        self.assertEqual([run.process for run in stopped], processes)

    def test_terminate_processes_signals_each_process_group(self):
        process = mock.Mock()
        process.pid = 456
        process.poll.side_effect = (None, 0)
        run = mock.Mock(process=process)

        with mock.patch.object(os, "killpg") as killpg:
            run_tests.terminate_processes([run], grace_seconds=1)

        killpg.assert_called_once_with(456, signal.SIGTERM)

    def test_multiplexer_env_is_purged_before_any_shard_starts(self):
        # Herdr pane 内でスイートを起動すると HERDR_*/TMUX が全 shard に継承され、
        # テストの PATH スタブが HERDR_BIN_PATH 優先の実装に迂回されて実在の
        # multiplexer インスタンスを操作してしまう（実害として観測済み）。
        # main() が shard 起動前に一度だけ環境を落とすことを固定する。
        polluted = {
            "HERDR_BIN_PATH": "/opt/homebrew/opt/herdr/bin/herdr",
            "HERDR_SOCKET_PATH": "/tmp/herdr.sock",
            "HERDR_ENV": "1",
            "HERDR_WORKSPACE_ID": "wC7",
            "TMUX": "/tmp/tmux-501/default,1,0",
        }
        seen = {}

        def capture_discover(*args, **kwargs):
            seen["at_discover"] = dict(os.environ)
            return ["fake.Test.test_example"]

        def capture_run_shards(shards, **kwargs):
            seen["at_run_shards"] = dict(os.environ)
            return []

        with mock.patch.dict(os.environ, polluted, clear=False):
            with mock.patch.object(run_tests, "load_dependency_map", return_value=({}, {})), mock.patch.object(run_tests, "discover_test_ids", side_effect=capture_discover):
                with mock.patch.object(run_tests, "run_shards", side_effect=capture_run_shards):
                    run_tests.main([])

        for stage in ("at_discover", "at_run_shards"):
            with self.subTest(stage=stage):
                leaked = [
                    key
                    for key in seen[stage]
                    if key.startswith("HERDR_") or key == "TMUX"
                ]
                self.assertEqual(leaked, [], seen[stage])

    def test_main_return_code_unaffected_when_environment_is_clean(self):
        with mock.patch.object(run_tests, "load_dependency_map", return_value=({}, {})), mock.patch.object(run_tests, "discover_test_ids", return_value=[]):
            status = run_tests.main([])

        self.assertEqual(status, 1)


if __name__ == "__main__":
    unittest.main()
