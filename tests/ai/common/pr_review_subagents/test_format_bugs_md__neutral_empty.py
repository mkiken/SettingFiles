import unittest

from support import REPO_ROOT


FORMAT_DIR = REPO_ROOT / "ai/common/pr_review_subagents"
AREAS = {
    "bugs": "バグ検出",
    "claims": "主張検証",
    "design": "設計品質",
    "history": "Git履歴",
    "performance": "パフォーマンス",
    "security": "セキュリティ",
    "tests": "テスト品質",
}


class SpecialistEmptyResultContractTest(unittest.TestCase):
    def test_all_dimensions_use_threshold_neutral_empty_result(self):
        for dimension, area in AREAS.items():
            with self.subTest(dimension=dimension):
                content = (FORMAT_DIR / f"format_{dimension}.md").read_text(encoding="utf-8")
                self.assertIn(f"{area}: 該当する問題は見つかりませんでした。", content)
                self.assertNotIn("信頼度75以上の", content)


if __name__ == "__main__":
    unittest.main()
