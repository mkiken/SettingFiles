import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env

SCRIPT = REPO_ROOT / "shell/common/ai_session_search.py"
PROJECT = "/work/proj"
GEMINI_SID = "11111111-2222-3333-4444-555555555555"


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


class AiSessionSearchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.make_claude()
        self.make_codex()
        self.make_gemini()

    def make_claude(self):
        write_jsonl(
            self.home / ".claude/projects/-work-proj/aaaa-claude.jsonl",
            [
                {"type": "user", "cwd": PROJECT, "message": {"content": "<command-name>/x</command-name>"}},
                {"type": "user", "cwd": PROJECT, "message": {"content": [{"type": "text", "text": "ClaudeUserPrompt こんにちは"}]}},
                {"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": "TOOLONLYSECRET"}},
                    {"type": "text", "text": "ClaudeAnswer"},
                ]}},
                {"type": "user", "message": {"content": [{"type": "tool_result", "content": "TOOLRESULTSECRET"}]}},
                {"type": "assistant", "isSidechain": True, "message": {"content": [{"type": "text", "text": "SIDECHAINSECRET"}]}},
            ],
        )
        (self.home / ".claude/projects/-work-proj/empty.jsonl").write_text("")
        (self.home / ".claude/projects/-work-proj/broken.jsonl").write_text("{not json\n")

    def make_codex(self):
        def message(role, kind, text):
            return {"type": "response_item", "payload": {"type": "message", "role": role, "content": [{"type": kind, "text": text}]}}

        write_jsonl(
            self.home / ".codex/sessions/2026/10/25/rollout-2026-10-25T00-00-00-cccc.jsonl",
            [
                {"type": "session_meta", "payload": {"id": "cccc-codex", "cwd": PROJECT}},
                message("developer", "input_text", "DEVELOPERSECRET"),
                message("user", "input_text", "# AGENTS.md instructions for /x"),
                message("user", "input_text", "<environment_context>ENVSECRET</environment_context>"),
                message("user", "input_text", "CodexUserPrompt"),
                message("assistant", "output_text", "CodexAnswer"),
            ],
        )

    def make_gemini(self):
        project_hash = hashlib.sha256(PROJECT.encode()).hexdigest()
        (self.home / ".gemini").mkdir(parents=True, exist_ok=True)
        (self.home / ".gemini/projects.json").write_text(json.dumps({"projects": {PROJECT: "proj"}}))
        chats = self.home / ".gemini/tmp/proj/chats"
        write_jsonl(
            chats / "session-2026-10-25T00-00-gjsonl.jsonl",
            [
                {"sessionId": GEMINI_SID, "projectHash": project_hash, "kind": "main"},
                {"$set": {"messages": [{"id": "m1", "type": "user", "content": [{"text": "GeminiJsonlPrompt"}]}]}},
                {"id": "m2", "type": "gemini", "content": "GeminiJsonlAnswer"},
                {"$set": {"messages": [
                    {"id": "m1", "type": "user", "content": [{"text": "GeminiJsonlPrompt"}]},
                    {"id": "m2", "type": "gemini", "content": "GeminiJsonlAnswer"},
                ]}},
                {"id": "m3", "type": "info", "content": "INFOSECRET"},
            ],
        )
        (chats / "session-2026-01-01T00-00-gjson.json").write_text(
            json.dumps({
                "sessionId": "legacy-json", "projectHash": "f" * 64,
                "messages": [
                    {"type": "user", "content": "LegacyPrompt"},
                    {"type": "gemini", "content": "LegacyAnswer"},
                ],
            })
        )
        write_jsonl(
            chats / "session-2026-10-25T00-00-a2a-serv.jsonl",
            [
                {"sessionId": "a2a-server", "projectHash": project_hash, "kind": "main"},
                {"$set": {"messages": [{"id": "x", "type": "user", "content": [{"text": "A2ASECRET"}]}]}},
            ],
        )

    def run_cli(self, *args):
        env = sanitized_env(HOME=str(self.home))
        for key in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "GEMINI_CLI_HOME"):
            env.pop(key, None)
        result = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), *args], env=env, capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def rows(self, *args):
        return [line.split("\t") for line in self.run_cli(*args).splitlines()]

    def test_list_extracts_id_cwd_and_first_user_prompt_per_agent(self):
        by_agent = {row[0]: row for row in self.rows("list") if row[1] != "legacy-json"}
        self.assertEqual(by_agent["claude"][1:3], ["aaaa-claude", PROJECT])
        self.assertIn("ClaudeUserPrompt", by_agent["claude"][4])
        self.assertEqual(by_agent["codex"][1:3], ["cccc-codex", PROJECT])
        self.assertIn("CodexUserPrompt", by_agent["codex"][4])
        self.assertEqual(by_agent["gemini"][1:3], [GEMINI_SID, PROJECT])
        self.assertIn("GeminiJsonlPrompt", by_agent["gemini"][4])

    def test_list_skips_empty_broken_and_a2a_files(self):
        ids = {row[1] for row in self.rows("list")}
        self.assertEqual(ids, {"aaaa-claude", "cccc-codex", GEMINI_SID, "legacy-json"})

    def test_list_is_sorted_newest_first(self):
        oldest = self.home / ".claude/projects/-work-proj/aaaa-claude.jsonl"
        os.utime(oldest, (1_000_000_000, 1_000_000_000))
        self.assertEqual(self.rows("list")[-1][1], "aaaa-claude")

    def test_gemini_legacy_json_has_empty_cwd_when_project_hash_is_unknown(self):
        legacy = next(row for row in self.rows("list") if row[1] == "legacy-json")
        self.assertEqual(legacy[2], "")

    def test_search_matches_body_text_case_insensitively(self):
        self.assertEqual([r[1] for r in self.rows("search", "claudeanswer")], ["aaaa-claude"])
        self.assertEqual([r[1] for r in self.rows("search", "LegacyAnswer")], ["legacy-json"])
        self.assertEqual([r[1] for r in self.rows("search", "GeminiJsonlAnswer")], [GEMINI_SID])

    def test_search_matches_japanese(self):
        self.assertEqual([r[1] for r in self.rows("search", "こんにちは")], ["aaaa-claude"])

    def test_search_requires_every_term(self):
        self.assertEqual([r[1] for r in self.rows("search", "ClaudeUserPrompt ClaudeAnswer")], ["aaaa-claude"])
        self.assertEqual(self.rows("search", "ClaudeUserPrompt CodexAnswer"), [])

    def test_search_ignores_tool_calls_injected_messages_and_non_conversation_entries(self):
        for secret in (
            "TOOLONLYSECRET", "TOOLRESULTSECRET", "SIDECHAINSECRET", "DEVELOPERSECRET",
            "ENVSECRET", "INFOSECRET", "A2ASECRET",
        ):
            with self.subTest(secret=secret):
                self.assertEqual(self.rows("search", secret), [])

    def test_search_with_empty_query_lists_everything(self):
        self.assertEqual(self.run_cli("search", ""), self.run_cli("list"))

    def test_search_row_has_snippet_after_title(self):
        row = self.rows("search", "ClaudeAnswer")[0]
        self.assertIn("ClaudeAnswer", row[4].split("|", 1)[1])

    def test_preview_with_query_shows_only_matching_messages_with_highlight(self):
        path = str(self.home / ".claude/projects/-work-proj/aaaa-claude.jsonl")
        out = self.run_cli("preview", "claude", path, "ClaudeAnswer")
        self.assertIn("── Assistant ──", out)
        self.assertIn("\x1b[1;33mClaudeAnswer\x1b[0m", out)
        self.assertNotIn("ClaudeUserPrompt", out)

    def test_preview_without_query_shows_conversation_in_order(self):
        path = str(self.home / ".codex/sessions/2026/10/25/rollout-2026-10-25T00-00-00-cccc.jsonl")
        out = self.run_cli("preview", "codex", path)
        self.assertLess(out.index("── User ──"), out.index("── Assistant ──"))
        self.assertIn("CodexUserPrompt", out)
        self.assertNotIn("ENVSECRET", out)

    def test_gemini_jsonl_messages_are_deduplicated_by_id(self):
        path = str(self.home / ".gemini/tmp/proj/chats/session-2026-10-25T00-00-gjsonl.jsonl")
        out = self.run_cli("preview", "gemini", path)
        self.assertEqual(out.count("GeminiJsonlPrompt"), 1)
        self.assertEqual(out.count("GeminiJsonlAnswer"), 1)

    def test_unknown_command_exits_with_usage(self):
        result = subprocess.run([sys.executable, "-I", str(SCRIPT), "bogus"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
