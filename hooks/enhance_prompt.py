#!/usr/bin/env python3
"""
prompt-forge-claude-code -- UserPromptSubmit hook

Intercepts Claude Code prompts, enhances them via Claude Haiku,
and returns additional context to help Claude better understand the user's intent.

Non-interactive. Fails open (exit 0) on any error. No TTY access.
"""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

# -- Constants ----------------------------------------------------------------

ENHANCEMENT_SYSTEM_PROMPT = """\
You are a prompt enhancement engine for Claude Code sessions.

Your job: take the user's raw prompt and return a clearer, more specific, \
more actionable version.

CRITICAL RULES:
- Output ONLY the enhanced prompt. No questions, no explanations, no preamble.
- NEVER ask for more information. Make reasonable assumptions.
- PRESERVE the original intent exactly.
- If the prompt is already specific and clear, return it UNCHANGED.
- Keep the enhancement concise -- do not pad unnecessarily.

What to improve:
- Replace vague verbs ("fix", "add", "improve") with specific outcomes
- Add likely file paths or function names based on context clues
- Surface implied constraints ("don't break existing tests", "keep the API stable")

Examples:
  Input:  "fix the bug in the login handler"
  Output: "Fix the bug in the login handler -- identify the root cause \
(check for null session, incorrect password comparison, or missing error \
handling), add a fix, and ensure existing login tests still pass."

  Input:  "add tests"
  Output: "Add unit tests for the main business logic. Cover the happy path, \
edge cases, and error conditions. Follow the existing test patterns."

  Input:  "yes"
  Output: "yes"
"""

SKIP_PATTERNS = frozenset({
    "yes", "no", "ok", "done", "continue", "stop", "quit", "exit",
    "y", "n", "sure", "thanks", "thank you", "go ahead", "proceed",
    "lgtm", "correct", "right", "nope", "yep", "yup", "nah",
})

MIN_WORDS = 4
MAX_CHARS_TO_ENHANCE = 600
API_TIMEOUT_SECONDS = 8
HAIKU_MODEL = "claude-haiku-4-5-20251001"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


# -- Skip Logic ---------------------------------------------------------------

def should_skip(prompt):
    """Return True for prompts that don't benefit from enhancement."""
    stripped = prompt.strip()
    if not stripped:
        return True
    if stripped.lower() in SKIP_PATTERNS:
        return True
    if stripped.startswith("/"):
        return True
    if len(stripped.split()) < MIN_WORDS:
        return True
    if len(stripped) > MAX_CHARS_TO_ENHANCE:
        return True
    return False


# -- API Key Resolution -------------------------------------------------------

def _read_credentials_file():
    """Read API key from ~/.claude/.credentials.json (Linux/Windows/macOS).

    Claude Code stores credentials in several formats:
    - OAuth: {"claudeAiOauth": {"accessToken": "sk-ant-oat01-..."}}
    - Direct key: {"apiKey": "sk-ant-api03-..."} or similar
    """
    try:
        creds_path = Path.home() / ".claude" / ".credentials.json"
        if not creds_path.exists():
            return ""
        data = json.loads(creds_path.read_text(encoding="utf-8"))

        # OAuth tokens (most common for Claude Code users)
        oauth = data.get("claudeAiOauth")
        if isinstance(oauth, dict):
            token = oauth.get("accessToken", "")
            if token:
                return str(token)

        # Direct API key fields
        for key_name in ("apiKey", "api_key", "anthropic_api_key"):
            if key_name in data and data[key_name]:
                return str(data[key_name])
    except Exception:
        pass
    return ""


def _read_macos_keychain():
    """Read API key from macOS keychain where Claude Code stores it."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code", "-w"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def get_api_key():
    """
    Resolve API key in order:
    1. ANTHROPIC_API_KEY env var
    2. ~/.claude/.credentials.json (Linux/Windows)
    3. macOS keychain
    """
    # 1. Environment variable
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key

    # 2. Credentials file
    key = _read_credentials_file()
    if key:
        return key

    # 3. macOS keychain
    key = _read_macos_keychain()
    if key:
        return key

    return ""


# -- Haiku API Call ------------------------------------------------------------

def enhance_with_claude(prompt):
    """Call Claude Haiku API to enhance the prompt. Returns enhanced text."""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("No API key found")

    payload = {
        "model": HAIKU_MODEL,
        "max_tokens": 512,
        "system": ENHANCEMENT_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as resp:
        result = json.loads(resp.read())
        return result["content"][0]["text"].strip()


# -- Main ---------------------------------------------------------------------

def main():
    """
    Hook entry point. Reads JSON from stdin, optionally enhances the prompt,
    and writes additional context to stdout as JSON.

    Exit 0 = allow prompt (with or without additional context).
    On ANY error, exit 0 silently (fail open).
    """
    # Check disabled flag early
    if os.environ.get("PROMPT_FORGE_DISABLED", "").lower() in ("1", "true", "yes"):
        sys.exit(0)

    # Check mode
    mode = os.environ.get("PROMPT_FORGE_MODE", "auto").lower()
    if mode == "off":
        sys.exit(0)

    # Read hook input from stdin
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
        prompt = data.get("prompt", "")
    except (json.JSONDecodeError, ValueError):
        # Can't parse input, fail open
        sys.exit(0)

    if not prompt or should_skip(prompt):
        sys.exit(0)

    try:
        enhanced = enhance_with_claude(prompt)
    except Exception as exc:
        print("[Prompt Forge] Enhancement skipped: %s" % str(exc), file=sys.stderr)
        sys.exit(0)

    # No meaningful change -- pass through silently
    if not enhanced or enhanced.strip() == prompt.strip():
        sys.exit(0)

    # Build the additional context output.
    # Instruct Claude to present the enhancement to the user and ask
    # for confirmation before proceeding. Claude acts as the UI layer.
    context_text = (
        "[Prompt Forge] An enhanced version of the user's prompt is available.\n"
        "\n"
        "IMPORTANT: Before doing ANY work, you MUST present the following to "
        "the user and ask which version they want to use. Do NOT proceed until "
        "the user confirms.\n"
        "\n"
        "Show this to the user:\n"
        "\n"
        "---\n"
        "**Prompt Forge** enhanced your request:\n"
        "\n"
        "**Original:**\n"
        "> %s\n"
        "\n"
        "**Enhanced:**\n"
        "> %s\n"
        "\n"
        "How would you like to proceed?\n"
        "1. **Use enhanced** -- proceed with the enhanced prompt\n"
        "2. **Use original** -- proceed with your original prompt as-is\n"
        "3. **Edit** -- tell me what to change about the enhanced version\n"
        "---\n"
        "\n"
        "Wait for the user's choice before taking any action."
    ) % (prompt, enhanced)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context_text,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # Fail open on any uncaught exception
        sys.exit(0)
