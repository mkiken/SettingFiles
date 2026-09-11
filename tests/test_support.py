import os
import unittest
from unittest import mock

from support import purge_multiplexer_env, sanitized_env, strip_multiplexer_env


class StripMultiplexerEnvTest(unittest.TestCase):
    def test_removes_known_multiplexer_variables(self):
        env = {
            "HERDR_BIN_PATH": "/opt/homebrew/opt/herdr/bin/herdr",
            "HERDR_ENV": "1",
            "HERDR_SOCKET_PATH": "/tmp/herdr.sock",
            "TMUX": "/tmp/tmux-501/default,1,0",
            "PATH": "/bin",
        }

        self.assertEqual(strip_multiplexer_env(env), {"PATH": "/bin"})

    def test_removes_unlisted_herdr_variable_by_prefix(self):
        # 列挙方式への退行防止: 個別変数名でなくプレフィックスで除去することを pin する。
        env = {"HERDR_FUTURE_THING": "1", "PATH": "/bin"}

        self.assertEqual(strip_multiplexer_env(env), {"PATH": "/bin"})

    def test_does_not_remove_variables_only_resembling_the_prefix(self):
        env = {"HERDRISH": "1", "NOT_HERDR_ENV": "1"}

        self.assertEqual(strip_multiplexer_env(env), env)

    def test_does_not_mutate_input(self):
        env = {"HERDR_ENV": "1", "PATH": "/bin"}
        original = dict(env)

        strip_multiplexer_env(env)

        self.assertEqual(env, original)


class SanitizedEnvTest(unittest.TestCase):
    def test_excludes_inherited_multiplexer_variable(self):
        with mock.patch.dict(os.environ, {"HERDR_ENV": "1"}):
            env = sanitized_env()

        self.assertNotIn("HERDR_ENV", env)

    def test_override_applies_after_strip(self):
        # strip の後に override を当てる順序の pin。逆順だと明示的に渡した
        # スタブ経路（HERDR_BIN_PATH）が消えて静かに壊れる。
        with mock.patch.dict(os.environ, {"HERDR_BIN_PATH": "/real/herdr"}):
            env = sanitized_env(HERDR_BIN_PATH="/fake/herdr")

        self.assertEqual(env["HERDR_BIN_PATH"], "/fake/herdr")

    def test_does_not_mutate_os_environ(self):
        with mock.patch.dict(os.environ, {"HERDR_ENV": "1"}):
            sanitized_env()
            self.assertEqual(os.environ["HERDR_ENV"], "1")

    def test_accepts_dict_overrides_without_keyword_collision(self):
        # 呼び出し側は extra_env (任意キーを含む dict) を **展開ではなく
        # 位置引数として渡す。extra_env に "overrides" 等の予約語衝突が
        # 起きないことを pin する。
        env = sanitized_env({"HERDR_ENV": "1", "PATH": "/bin"})

        self.assertEqual(env["HERDR_ENV"], "1")
        self.assertEqual(env["PATH"], "/bin")

    def test_keyword_overrides_take_precedence_over_dict(self):
        env = sanitized_env({"HERDR_ENV": "1"}, HERDR_ENV="2")

        self.assertEqual(env["HERDR_ENV"], "2")


class PurgeMultiplexerEnvTest(unittest.TestCase):
    def test_removes_keys_from_given_mapping_and_returns_removed(self):
        env = {"HERDR_ENV": "1", "TMUX": "t", "PATH": "/bin"}

        removed = purge_multiplexer_env(env)

        self.assertEqual(env, {"PATH": "/bin"})
        self.assertEqual(sorted(removed), ["HERDR_ENV", "TMUX"])


if __name__ == "__main__":
    unittest.main()
