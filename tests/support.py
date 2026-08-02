"""Shared test utilities independent of a test module's directory depth."""

from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
