import re
import unittest
from pathlib import Path


from support import REPO_ROOT
SKILL_DIR = REPO_ROOT / ".claude/skills/herdr-dev"
SKILL_MD = SKILL_DIR / "SKILL.md"
REFERENCES_DIR = SKILL_DIR / "references"

# The router's routing table cites files as `references/<name>.md`; any
# other repository-relative reference (`.claude/skills/...` etc.) is prose,
# not a routing pointer, so the pattern is deliberately narrow.
REFERENCE_POINTER_PATTERN = re.compile(r"`references/([a-z0-9_-]+\.md)`")

ALLOWED_FRONTMATTER_KEYS = {"name", "description"}


class HerdrDevReferencesTest(unittest.TestCase):
    """herdr-dev is a router SKILL.md plus references/*.md read-units (see
    CLAUDE.md's Symlink Strategy section). Nothing previously verified that
    a reference the router names still exists, or that every reference file
    is reachable from the router — a rename on either side breaks the split
    silently, since there is no runtime include mechanism to error out.
    Mirrors the dangling-pointer check in test_always_on_skill_pointers.py.
    """

    def setUp(self):
        self.router_text = SKILL_MD.read_text(encoding="utf-8")
        self.reference_files = {p.name for p in REFERENCES_DIR.glob("*.md")}

    def test_references_directory_exists(self):
        self.assertTrue(
            REFERENCES_DIR.is_dir(),
            f"{REFERENCES_DIR.relative_to(REPO_ROOT)} does not exist",
        )
        self.assertTrue(self.reference_files, "references/ contains no .md files")

    def test_router_pointers_resolve_to_real_files(self):
        # Dangling-pointer direction: every references/x.md the router
        # names in its routing table must exist on disk.
        cited = set(REFERENCE_POINTER_PATTERN.findall(self.router_text))
        self.assertTrue(cited, "router SKILL.md cites no references/*.md files")
        missing = cited - self.reference_files
        self.assertFalse(
            missing,
            f"router SKILL.md points at references/{missing}, which do not exist",
        )

    def test_every_reference_file_is_routed_to(self):
        # Orphan-file direction: every references/*.md file must be named
        # somewhere in the router's routing table, or it is dead weight
        # nobody's instructions ever tell an agent to read.
        cited = set(REFERENCE_POINTER_PATTERN.findall(self.router_text))
        orphans = self.reference_files - cited
        self.assertFalse(
            orphans,
            f"references/{orphans} exist but the router SKILL.md never routes to them",
        )

    def test_cross_reference_pointers_resolve(self):
        # Reference files point at each other (e.g. plugin-env.md <->
        # popups.md). Those pointers must also resolve, or a rename on one
        # side silently strands the other.
        for path in sorted(REFERENCES_DIR.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            cited = set(REFERENCE_POINTER_PATTERN.findall(text))
            missing = cited - self.reference_files
            self.assertFalse(
                missing,
                f"{path.relative_to(REPO_ROOT)} points at references/{missing}, which do not exist",
            )

    def test_router_frontmatter_stays_cross_platform(self):
        # Repository-local skill frontmatter must stay in the cross-platform
        # subset (name + description only) per CLAUDE.md's Symlink Strategy
        # section, since Codex injects SKILL.md raw with no runtime include.
        match = re.match(r"^---\n(.*?)\n---\n", self.router_text, re.DOTALL)
        self.assertIsNotNone(match, "router SKILL.md is missing a frontmatter block")
        keys = set(re.findall(r"^([a-zA-Z0-9_-]+):", match.group(1), re.MULTILINE))
        extra = keys - ALLOWED_FRONTMATTER_KEYS
        self.assertFalse(
            extra,
            f"router SKILL.md frontmatter has non-cross-platform keys: {extra}",
        )


if __name__ == "__main__":
    unittest.main()
