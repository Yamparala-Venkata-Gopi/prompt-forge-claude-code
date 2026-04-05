#!/usr/bin/env python3
"""
Unit tests for enhance_prompt.py
Tests all business logic without requiring API keys or a TTY.
"""

import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add hooks directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hooks'))
import enhance_prompt as ep


class TestShouldSkip(unittest.TestCase):

    def test_skips_empty(self):
        self.assertTrue(ep.should_skip(""))

    def test_skips_whitespace_only(self):
        self.assertTrue(ep.should_skip("   "))

    def test_skips_confirmation_yes(self):
        self.assertTrue(ep.should_skip("yes"))

    def test_skips_confirmation_no(self):
        self.assertTrue(ep.should_skip("no"))

    def test_skips_confirmation_ok(self):
        self.assertTrue(ep.should_skip("ok"))

    def test_skips_confirmation_done(self):
        self.assertTrue(ep.should_skip("done"))

    def test_skips_short_prompt_under_4_words(self):
        self.assertTrue(ep.should_skip("fix bug"))

    def test_skips_exactly_3_words(self):
        self.assertTrue(ep.should_skip("fix the bug"))

    def test_does_not_skip_4_words(self):
        self.assertFalse(ep.should_skip("fix the login bug"))

    def test_skips_long_prompt_over_600_chars(self):
        long = "word " * 200
        self.assertTrue(ep.should_skip(long))

    def test_does_not_skip_normal_prompt(self):
        self.assertFalse(ep.should_skip("add logging to the proxy handler"))

    def test_does_not_skip_medium_length_prompt(self):
        prompt = "fix the authentication bug in the login handler when users have special characters in password"
        self.assertFalse(ep.should_skip(prompt))


class TestGetUserChoice(unittest.TestCase):

    @patch('enhance_prompt.has_command', return_value=False)
    @patch('enhance_prompt.tty_input', return_value='a')
    @patch('enhance_prompt.tty_print')
    def test_accept_returns_enhanced(self, mock_print, mock_input, mock_cmd):
        result = ep.get_user_choice("original prompt", "enhanced prompt")
        self.assertEqual(result, "enhanced prompt")

    @patch('enhance_prompt.has_command', return_value=False)
    @patch('enhance_prompt.tty_input', return_value='r')
    @patch('enhance_prompt.tty_print')
    def test_reject_returns_original(self, mock_print, mock_input, mock_cmd):
        result = ep.get_user_choice("original prompt", "enhanced prompt")
        self.assertEqual(result, "original prompt")

    @patch('enhance_prompt.has_command', return_value=False)
    @patch('enhance_prompt.open_editor', return_value='my edited prompt')
    @patch('enhance_prompt.tty_input', return_value='e')
    @patch('enhance_prompt.tty_print')
    def test_edit_returns_edited(self, mock_print, mock_input, mock_editor, mock_cmd):
        result = ep.get_user_choice("original prompt", "enhanced prompt")
        self.assertEqual(result, "my edited prompt")

    @patch('enhance_prompt.has_command', return_value=False)
    @patch('enhance_prompt.tty_input', return_value='')
    @patch('enhance_prompt.tty_print')
    def test_empty_input_defaults_to_accept(self, mock_print, mock_input, mock_cmd):
        result = ep.get_user_choice("original prompt", "enhanced prompt")
        self.assertEqual(result, "enhanced prompt")

    @patch('enhance_prompt.has_command', return_value=False)
    @patch('enhance_prompt.tty_input', return_value='x')
    @patch('enhance_prompt.tty_print')
    def test_unknown_choice_returns_original(self, mock_print, mock_input, mock_cmd):
        result = ep.get_user_choice("original prompt", "enhanced prompt")
        self.assertEqual(result, "original prompt")


class TestEnhanceWithClaude(unittest.TestCase):

    @patch('subprocess.run')
    def test_returns_enhanced_text(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Enhanced: fix the null pointer in handle_request()",
            stderr=""
        )
        result = ep.enhance_with_claude("fix the bug")
        self.assertEqual(result, "Enhanced: fix the null pointer in handle_request()")

    @patch('subprocess.run')
    def test_strips_whitespace_from_response(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  enhanced prompt with spaces  ",
            stderr=""
        )
        result = ep.enhance_with_claude("fix the bug")
        self.assertEqual(result, "enhanced prompt with spaces")

    @patch('subprocess.run')
    def test_raises_on_non_zero_exit(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="claude CLI error"
        )
        with self.assertRaises(RuntimeError):
            ep.enhance_with_claude("fix the bug")


class TestMainFlow(unittest.TestCase):

    def _run_main(self, stdin_json: dict, env: dict = None, mock_enhanced: str = None,
                  user_choice: str = 'a') -> tuple:
        import io
        from contextlib import redirect_stdout

        stdin_data = json.dumps(stdin_json)
        stdout_capture = io.StringIO()
        env_patch = {**os.environ, **(env or {})}

        with patch('sys.stdin', io.StringIO(stdin_data)), \
             patch.dict('os.environ', env_patch, clear=True), \
             patch('enhance_prompt.tty_print'), \
             patch('enhance_prompt.tty_input', return_value=user_choice), \
             patch('enhance_prompt.has_command', return_value=False), \
             redirect_stdout(stdout_capture):

            with patch('enhance_prompt.enhance_with_claude', return_value=mock_enhanced or ""):
                try:
                    ep.main()
                    exit_code = 0
                except SystemExit as e:
                    exit_code = e.code or 0

        return stdout_capture.getvalue(), exit_code

    def test_short_prompt_exits_silently(self):
        out, code = self._run_main({"prompt": "yes"})
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_disabled_flag_exits_silently(self):
        out, code = self._run_main(
            {"prompt": "fix the auth bug in login handler"},
            env={"PROMPT_FORGE_DISABLED": "1"}
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_accept_outputs_enhanced_prompt(self):
        out, code = self._run_main(
            {"prompt": "add logging to proxy"},
            mock_enhanced="Add structured logging to the proxy pipeline with INFO/DEBUG levels",
            user_choice='a'
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["prompt"], "Add structured logging to the proxy pipeline with INFO/DEBUG levels")

    def test_reject_outputs_nothing(self):
        out, code = self._run_main(
            {"prompt": "add logging to proxy"},
            mock_enhanced="Add structured logging to the proxy pipeline with INFO/DEBUG levels",
            user_choice='r'
        )
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "")

    def test_no_change_exits_silently(self):
        out, code = self._run_main(
            {"prompt": "add logging to proxy"},
            mock_enhanced="add logging to proxy",
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_cli_error_exits_silently(self):
        import io
        from contextlib import redirect_stdout
        stdin_data = json.dumps({"prompt": "fix the auth bug in login handler"})
        stdout_capture = io.StringIO()

        with patch('sys.stdin', io.StringIO(stdin_data)), \
             patch('enhance_prompt.tty_print'), \
             patch('enhance_prompt.enhance_with_claude', side_effect=Exception("claude CLI error")), \
             redirect_stdout(stdout_capture):
            try:
                ep.main()
                exit_code = 0
            except SystemExit as e:
                exit_code = e.code or 0

        self.assertEqual(exit_code, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
