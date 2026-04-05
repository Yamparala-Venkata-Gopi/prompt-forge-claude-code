#!/usr/bin/env python3
"""
Unit tests for enhance_prompt.py

Tests all business logic without requiring API keys or network access.
"""

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add hooks directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hooks'))
import enhance_prompt as ep


# =============================================================================
# Skip Logic Tests
# =============================================================================

class TestShouldSkip(unittest.TestCase):
    """Tests for the should_skip() function."""

    def test_skips_empty_string(self):
        self.assertTrue(ep.should_skip(""))

    def test_skips_whitespace_only(self):
        self.assertTrue(ep.should_skip("   "))

    def test_skips_none_like_empty(self):
        # Passing empty after strip
        self.assertTrue(ep.should_skip("  \t\n  "))

    def test_skips_confirmation_yes(self):
        self.assertTrue(ep.should_skip("yes"))

    def test_skips_confirmation_no(self):
        self.assertTrue(ep.should_skip("no"))

    def test_skips_confirmation_ok(self):
        self.assertTrue(ep.should_skip("ok"))

    def test_skips_confirmation_done(self):
        self.assertTrue(ep.should_skip("done"))

    def test_skips_confirmation_continue(self):
        self.assertTrue(ep.should_skip("continue"))

    def test_skips_confirmation_y(self):
        self.assertTrue(ep.should_skip("y"))

    def test_skips_confirmation_n(self):
        self.assertTrue(ep.should_skip("n"))

    def test_skips_confirmation_sure(self):
        self.assertTrue(ep.should_skip("sure"))

    def test_skips_confirmation_lgtm(self):
        self.assertTrue(ep.should_skip("lgtm"))

    def test_skips_confirmation_case_insensitive(self):
        self.assertTrue(ep.should_skip("YES"))
        self.assertTrue(ep.should_skip("No"))
        self.assertTrue(ep.should_skip("OK"))

    def test_skips_slash_commands(self):
        self.assertTrue(ep.should_skip("/help"))
        self.assertTrue(ep.should_skip("/forge something"))
        self.assertTrue(ep.should_skip("/commit -m 'test'"))

    def test_skips_short_prompt_under_4_words(self):
        self.assertTrue(ep.should_skip("fix bug"))

    def test_skips_exactly_3_words(self):
        self.assertTrue(ep.should_skip("fix the bug"))

    def test_does_not_skip_4_words(self):
        self.assertFalse(ep.should_skip("fix the login bug"))

    def test_skips_long_prompt_over_600_chars(self):
        long_prompt = "word " * 200  # 1000 chars
        self.assertTrue(ep.should_skip(long_prompt))

    def test_does_not_skip_normal_prompt(self):
        self.assertFalse(ep.should_skip("add logging to the proxy handler"))

    def test_does_not_skip_medium_length_prompt(self):
        prompt = "fix the authentication bug in the login handler when users have special characters"
        self.assertFalse(ep.should_skip(prompt))


# =============================================================================
# API Key Resolution Tests
# =============================================================================

class TestGetApiKey(unittest.TestCase):
    """Tests for the get_api_key() and related functions."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_env_var_takes_priority(self):
        key = ep.get_api_key()
        self.assertEqual(key, "sk-ant-test-key")

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""})
    @patch('enhance_prompt._read_credentials_file', return_value="sk-from-creds")
    @patch('enhance_prompt._read_macos_keychain', return_value="")
    def test_credentials_file_fallback(self, mock_kc, mock_creds):
        key = ep.get_api_key()
        self.assertEqual(key, "sk-from-creds")

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""})
    @patch('enhance_prompt._read_credentials_file', return_value="")
    @patch('enhance_prompt._read_macos_keychain', return_value="sk-from-keychain")
    def test_macos_keychain_fallback(self, mock_kc, mock_creds):
        key = ep.get_api_key()
        self.assertEqual(key, "sk-from-keychain")

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""})
    @patch('enhance_prompt._read_credentials_file', return_value="")
    @patch('enhance_prompt._read_macos_keychain', return_value="")
    def test_returns_empty_when_no_key_found(self, mock_kc, mock_creds):
        key = ep.get_api_key()
        self.assertEqual(key, "")

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "  sk-with-spaces  "})
    def test_env_var_is_stripped(self):
        key = ep.get_api_key()
        self.assertEqual(key, "sk-with-spaces")


class TestReadCredentialsFile(unittest.TestCase):
    """Tests for _read_credentials_file()."""

    @patch('enhance_prompt.Path.home')
    def test_reads_oauth_access_token(self, mock_home):
        """Most common case: Claude Code OAuth credentials."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home.return_value = Path(tmpdir)
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            creds = claude_dir / ".credentials.json"
            creds.write_text(json.dumps({
                "claudeAiOauth": {
                    "accessToken": "sk-ant-oat01-test-token",
                    "refreshToken": "sk-ant-ort01-refresh",
                    "expiresAt": 9999999999999,
                }
            }))
            result = ep._read_credentials_file()
            self.assertEqual(result, "sk-ant-oat01-test-token")

    @patch('enhance_prompt.Path.home')
    def test_reads_api_key_field(self, mock_home):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home.return_value = Path(tmpdir)
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            creds = claude_dir / ".credentials.json"
            creds.write_text(json.dumps({"apiKey": "sk-from-file"}))
            result = ep._read_credentials_file()
            self.assertEqual(result, "sk-from-file")

    @patch('enhance_prompt.Path.home')
    def test_reads_api_key_alternate_field(self, mock_home):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home.return_value = Path(tmpdir)
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            creds = claude_dir / ".credentials.json"
            creds.write_text(json.dumps({"api_key": "sk-alt-field"}))
            result = ep._read_credentials_file()
            self.assertEqual(result, "sk-alt-field")

    @patch('enhance_prompt.Path.home')
    def test_oauth_takes_priority_over_direct_key(self, mock_home):
        """OAuth token should be preferred when both exist."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home.return_value = Path(tmpdir)
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            creds = claude_dir / ".credentials.json"
            creds.write_text(json.dumps({
                "claudeAiOauth": {"accessToken": "sk-oauth-token"},
                "apiKey": "sk-direct-key"
            }))
            result = ep._read_credentials_file()
            self.assertEqual(result, "sk-oauth-token")

    @patch('enhance_prompt.Path.home')
    def test_returns_empty_when_no_file(self, mock_home):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home.return_value = Path(tmpdir)
            result = ep._read_credentials_file()
            self.assertEqual(result, "")

    @patch('enhance_prompt.Path.home')
    def test_returns_empty_on_invalid_json(self, mock_home):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home.return_value = Path(tmpdir)
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            creds = claude_dir / ".credentials.json"
            creds.write_text("not valid json {{{")
            result = ep._read_credentials_file()
            self.assertEqual(result, "")


class TestReadMacosKeychain(unittest.TestCase):
    """Tests for _read_macos_keychain()."""

    @patch('subprocess.run')
    def test_reads_from_keychain(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="sk-keychain-key\n"
        )
        result = ep._read_macos_keychain()
        self.assertEqual(result, "sk-keychain-key")

    @patch('subprocess.run')
    def test_returns_empty_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = ep._read_macos_keychain()
        self.assertEqual(result, "")

    @patch('subprocess.run', side_effect=FileNotFoundError)
    def test_returns_empty_when_security_not_found(self, mock_run):
        result = ep._read_macos_keychain()
        self.assertEqual(result, "")


# =============================================================================
# Haiku API Call Tests
# =============================================================================

class TestEnhanceWithClaude(unittest.TestCase):
    """Tests for enhance_with_claude()."""

    @patch('enhance_prompt.get_api_key', return_value='sk-ant-fake')
    @patch('urllib.request.urlopen')
    def test_returns_enhanced_text(self, mock_urlopen, mock_key):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "content": [{"text": "Enhanced: fix the null pointer in handle_request()"}]
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = ep.enhance_with_claude("fix the bug")
        self.assertEqual(result, "Enhanced: fix the null pointer in handle_request()")

    @patch('enhance_prompt.get_api_key', return_value='sk-ant-fake')
    @patch('urllib.request.urlopen')
    def test_strips_whitespace_from_response(self, mock_urlopen, mock_key):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "content": [{"text": "  enhanced with spaces  "}]
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = ep.enhance_with_claude("test prompt")
        self.assertEqual(result, "enhanced with spaces")

    @patch('enhance_prompt.get_api_key', return_value='')
    def test_raises_when_no_api_key(self, mock_key):
        with self.assertRaises(RuntimeError):
            ep.enhance_with_claude("fix the bug")

    @patch('enhance_prompt.get_api_key', return_value='sk-ant-fake')
    @patch('urllib.request.urlopen')
    def test_request_format(self, mock_urlopen, mock_key):
        """Verify the request sent to the API has correct format and headers."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "content": [{"text": "enhanced"}]
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        ep.enhance_with_claude("test prompt")

        # Verify urlopen was called with correct timeout
        call_args = mock_urlopen.call_args
        self.assertEqual(call_args[1].get('timeout', call_args[0][1] if len(call_args[0]) > 1 else None),
                         ep.API_TIMEOUT_SECONDS)

        # Verify the request object
        req = call_args[0][0]
        self.assertEqual(req.get_header("X-api-key"), "sk-ant-fake")
        self.assertEqual(req.get_header("Anthropic-version"), "2023-06-01")
        self.assertEqual(req.get_header("Content-type"), "application/json")

        # Verify payload
        payload = json.loads(req.data)
        self.assertEqual(payload["model"], ep.HAIKU_MODEL)
        self.assertEqual(payload["max_tokens"], 512)
        self.assertEqual(len(payload["messages"]), 1)
        self.assertEqual(payload["messages"][0]["content"], "test prompt")

    @patch('enhance_prompt.get_api_key', return_value='sk-ant-fake')
    @patch('urllib.request.urlopen')
    def test_timeout_is_set(self, mock_urlopen, mock_key):
        """Verify the API call uses the configured timeout."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "content": [{"text": "enhanced"}]
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        ep.enhance_with_claude("test")

        call_args = mock_urlopen.call_args
        # timeout should be passed as keyword or second positional arg
        if 'timeout' in call_args[1]:
            self.assertEqual(call_args[1]['timeout'], ep.API_TIMEOUT_SECONDS)
        else:
            self.assertEqual(call_args[0][1], ep.API_TIMEOUT_SECONDS)


# =============================================================================
# Main Flow Tests
# =============================================================================

class TestMainFlow(unittest.TestCase):
    """Tests for the main() function end-to-end."""

    def _run_main(self, stdin_data, env_overrides=None, mock_enhanced=None):
        """
        Helper to run main() with mocked stdin and capture stdout/exit code.
        Returns (stdout_text, exit_code).
        """
        if isinstance(stdin_data, dict):
            stdin_data = json.dumps(stdin_data)

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        env = dict(os.environ)
        # Clear any existing forge env vars
        env.pop("PROMPT_FORGE_DISABLED", None)
        env.pop("PROMPT_FORGE_MODE", None)
        if env_overrides:
            env.update(env_overrides)

        patches = [
            patch('sys.stdin', io.StringIO(stdin_data)),
            patch.dict('os.environ', env, clear=True),
        ]
        if mock_enhanced is not None:
            patches.append(
                patch('enhance_prompt.enhance_with_claude', return_value=mock_enhanced)
            )

        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            for p in patches:
                p.start()
            try:
                ep.main()
                exit_code = 0
            except SystemExit as e:
                exit_code = e.code if e.code is not None else 0
            finally:
                for p in patches:
                    p.stop()

        return stdout_capture.getvalue(), exit_code

    # -- Skip cases --

    def test_empty_prompt_exits_silently(self):
        out, code = self._run_main({"prompt": ""})
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_short_prompt_exits_silently(self):
        out, code = self._run_main({"prompt": "yes"})
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_slash_command_exits_silently(self):
        out, code = self._run_main({"prompt": "/help"})
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_long_prompt_exits_silently(self):
        out, code = self._run_main({"prompt": "x " * 400})
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    # -- Disabled / off mode --

    def test_disabled_flag_exits_silently(self):
        out, code = self._run_main(
            {"prompt": "fix the auth bug in login handler"},
            env_overrides={"PROMPT_FORGE_DISABLED": "1"}
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_disabled_flag_true(self):
        out, code = self._run_main(
            {"prompt": "fix the auth bug in login handler"},
            env_overrides={"PROMPT_FORGE_DISABLED": "true"}
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_disabled_flag_yes(self):
        out, code = self._run_main(
            {"prompt": "fix the auth bug in login handler"},
            env_overrides={"PROMPT_FORGE_DISABLED": "yes"}
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_mode_off_exits_silently(self):
        out, code = self._run_main(
            {"prompt": "fix the auth bug in login handler"},
            env_overrides={"PROMPT_FORGE_MODE": "off"}
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    # -- Successful enhancement --

    def test_outputs_correct_json_format(self):
        out, code = self._run_main(
            {"prompt": "add logging to the proxy handler"},
            mock_enhanced="Add structured logging to the proxy pipeline with INFO/DEBUG levels"
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("hookSpecificOutput", data)
        hook_output = data["hookSpecificOutput"]
        self.assertEqual(hook_output["hookEventName"], "UserPromptSubmit")
        self.assertIn("additionalContext", hook_output)

    def test_additional_context_format(self):
        out, code = self._run_main(
            {"prompt": "add logging to the proxy handler"},
            mock_enhanced="Add structured logging to the proxy pipeline"
        )
        data = json.loads(out)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        self.assertIn("[Prompt Forge]", ctx)
        self.assertIn("IMPORTANT: Before doing ANY work", ctx)
        # Must contain both original and enhanced prompts
        self.assertIn("add logging to the proxy handler", ctx)
        self.assertIn("Add structured logging to the proxy pipeline", ctx)
        # Must present user choices
        self.assertIn("Use enhanced", ctx)
        self.assertIn("Use original", ctx)
        self.assertIn("Edit", ctx)
        # Must instruct Claude to wait
        self.assertIn("Wait for the user's choice", ctx)

    # -- No change --

    def test_no_change_exits_silently(self):
        out, code = self._run_main(
            {"prompt": "add logging to the proxy handler"},
            mock_enhanced="add logging to the proxy handler",
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_empty_enhancement_exits_silently(self):
        out, code = self._run_main(
            {"prompt": "add logging to the proxy handler"},
            mock_enhanced="",
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    # -- Error handling --

    def test_api_error_exits_silently(self):
        """On API error, should exit 0 with no stdout output."""
        stdin_data = json.dumps({"prompt": "fix the auth bug in login handler"})
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        env = dict(os.environ)
        env.pop("PROMPT_FORGE_DISABLED", None)
        env.pop("PROMPT_FORGE_MODE", None)

        with patch('sys.stdin', io.StringIO(stdin_data)), \
             patch.dict('os.environ', env, clear=True), \
             patch('enhance_prompt.enhance_with_claude',
                   side_effect=Exception("API error")), \
             redirect_stdout(stdout_capture), \
             redirect_stderr(stderr_capture):
            try:
                ep.main()
                exit_code = 0
            except SystemExit as e:
                exit_code = e.code if e.code is not None else 0

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_capture.getvalue(), "")

    def test_invalid_json_input_exits_silently(self):
        out, code = self._run_main("not valid json {{{")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_missing_prompt_field_exits_silently(self):
        out, code = self._run_main({"session_id": "abc", "cwd": "/tmp"})
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    # -- Full hook input format --

    def test_handles_full_hook_input_schema(self):
        """Test with the complete hook input schema as documented."""
        hook_input = {
            "session_id": "abc-123",
            "transcript_path": "/tmp/transcript.json",
            "cwd": "/home/user/project",
            "permission_mode": "default",
            "hook_event_name": "UserPromptSubmit",
            "prompt": "add error handling to the API routes"
        }
        out, code = self._run_main(
            hook_input,
            mock_enhanced="Add comprehensive error handling to all API routes"
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("hookSpecificOutput", data)


# =============================================================================
# Cross-platform Path Handling Tests
# =============================================================================

class TestCrossPlatform(unittest.TestCase):
    """Tests for cross-platform compatibility."""

    @patch('enhance_prompt.Path.home')
    def test_credentials_path_uses_pathlib(self, mock_home):
        """Verify credentials file lookup uses pathlib for cross-platform paths."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home.return_value = Path(tmpdir)
            # No credentials file exists, should return empty
            result = ep._read_credentials_file()
            self.assertEqual(result, "")

    def test_no_tty_access_in_hook(self):
        """Verify the hook code doesn't reference /dev/tty."""
        import inspect
        source = inspect.getsource(ep)
        self.assertNotIn("/dev/tty", source)

    def test_no_gum_dependency(self):
        """Verify the hook code doesn't reference gum."""
        import inspect
        source = inspect.getsource(ep)
        self.assertNotIn("gum", source)


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance(unittest.TestCase):
    """Tests related to performance characteristics."""

    def test_api_timeout_is_reasonable(self):
        """Timeout should be <= 8 seconds for fast response."""
        self.assertLessEqual(ep.API_TIMEOUT_SECONDS, 8)

    def test_max_tokens_is_bounded(self):
        """Max tokens should be small to keep responses fast."""
        # Verify the constant is used in enhance_with_claude
        # by checking the payload construction
        with patch('enhance_prompt.get_api_key', return_value='sk-fake'), \
             patch('urllib.request.urlopen') as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "content": [{"text": "enhanced"}]
            }).encode()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            ep.enhance_with_claude("test prompt for performance")

            req = mock_urlopen.call_args[0][0]
            payload = json.loads(req.data)
            self.assertLessEqual(payload["max_tokens"], 1024)


if __name__ == '__main__':
    unittest.main(verbosity=2)
