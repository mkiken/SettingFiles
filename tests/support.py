"""Shared test utilities independent of a test module's directory depth."""

import os
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent

# Herdr / tmux が pane へ注入する変数。テストプロセスがこれを継承したまま
# fake 実行ファイルを PATH 先頭に置いても、実装側が `${HERDR_BIN_PATH:-herdr}`
# のように PATH 解決より環境変数を優先するため PATH スタブを迂回し、
# 実在の multiplexer インスタンスを操作してしまう。
MULTIPLEXER_ENV_PREFIXES = ("HERDR_",)
MULTIPLEXER_ENV_NAMES = ("TMUX", "TMUX_PANE")


def _is_multiplexer_env(key):
    return key.startswith(MULTIPLEXER_ENV_PREFIXES) or key in MULTIPLEXER_ENV_NAMES


def strip_multiplexer_env(env):
    """env から multiplexer 注入変数を除いた新しい dict を返す。"""
    return {key: value for key, value in env.items() if not _is_multiplexer_env(key)}


def sanitized_env(overrides=None, **kwargs):
    """os.environ から multiplexer 変数を除いた subprocess 用 env を作る。

    HERDR_* / TMUX を使うテストは overrides (dict) か keyword 引数で明示的に
    渡すこと。dict と keyword を両方渡した場合は keyword が優先される。
    """
    env = strip_multiplexer_env(os.environ)
    if overrides:
        env.update(overrides)
    env.update(kwargs)
    return env


def purge_multiplexer_env(environ=None):
    """プロセスの環境変数から multiplexer 注入変数を除去し、除去したキーを返す。"""
    environ = os.environ if environ is None else environ
    removed = [key for key in list(environ) if _is_multiplexer_env(key)]
    for key in removed:
        del environ[key]
    return removed
