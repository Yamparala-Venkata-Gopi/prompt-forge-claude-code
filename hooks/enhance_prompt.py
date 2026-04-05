#!/usr/bin/env python3
"""
prompt-forge-claude-code — UserPromptSubmit hook
Intercepts Claude Code prompts, enhances them via Claude Haiku,
shows a colored diff, and lets the user accept / edit / reject.
"""

import json
import os
import subprocess
import sys
import tempfile
import difflib
import urllib.request
import urllib.error

# ── Constants ────────────────────────────────────────────────────────────────

ENHANCEMENT_SYSTEM_PROMPT = """You are a prompt enhancement engine for Claude Code sessions.

Your job: take the user's raw prompt and return a clearer, more specific, more actionable version.

Rules:
- PRESERVE the original intent exactly — never change what is being asked
- Add missing file paths, function names, or context when the request is vague
- Surface implied constraints ("don't break existing tests", "keep the public API stable")
- Replace vague verbs ("fix", "improve", "add") with specific descriptions of the desired outcome
- If the prompt is already clear and specific, return it UNCHANGED
- Output ONLY the enhanced prompt — no explanation, no preamble, no markdown

Examples:
  Input:  "fix the bug"
  Output: "Fix the null pointer dereference in `handle_request()` — it panics when the request body is empty. Add a guard clause at the top of the function."

  Input:  "add tests"
  Output: "Add unit tests for `ForwardProxyHandler::process_request()`. Cover the Allow, Block, and AllowWithInspection decision paths. Follow the existing wiremock patterns in `tests/`."

  Input:  "yes"
  Output: "yes"
"""

SKIP_PATTERNS = {"yes", "no", "ok", "done", "continue", "stop", "quit", "exit", "y", "n"}
MIN_WORDS = 4
MAX_CHARS_TO_ENHANCE = 600  # prompts longer than this are probably already detailed

# ANSI colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


# ── Helpers ───────────────────────────────────────────────────────────────────

def tty_print(msg: str) -> None:
    """Write to the terminal even when stdout is captured by Claude Code."""
    try:
        with open("/dev/tty", "w") as tty:
            tty.write(msg + "\n")
    except OSError:
        print(msg, file=sys.stderr)


def tty_input(prompt: str) -> str:
    """Read a line from the terminal even when stdin is consumed."""
    try:
        with open("/dev/tty", "r") as tty:
            sys.stderr.write(prompt)
            sys.stderr.flush()
            return tty.readline().strip()
    except OSError:
        return ""


def has_command(cmd: str) -> bool:
    try:
        subprocess.run([cmd, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def should_skip(prompt: str) -> bool:
    """Return True for prompts that don't benefit from enhancement."""
    stripped = prompt.strip()
    if not stripped:
        return True
    if stripped.lower() in SKIP_PATTERNS:
        return True
    if len(stripped.split()) < MIN_WORDS:
        return True
    if len(stripped) > MAX_CHARS_TO_ENHANCE:
        return True
    return False


# ── LLM Enhancement ──────────────────────────────────────────────────────────

def call_haiku(prompt: str, api_key: str) -> str:
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 512,
        "system": ENHANCEMENT_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        return result["content"][0]["text"].strip()


# ── Diff Display ─────────────────────────────────────────────────────────────

def show_diff(original: str, enhanced: str) -> None:
    orig_lines = original.splitlines(keepends=True)
    enh_lines = enhanced.splitlines(keepends=True)

    diff = list(
        difflib.unified_diff(orig_lines, enh_lines, fromfile="original", tofile="enhanced", lineterm="")
    )

    tty_print(f"\n{BOLD}╔══ Prompt Forge ══════════════════════════════════════╗{RESET}")

    if not diff:
        tty_print(f"{YELLOW}  No changes — prompt is already well-formed.{RESET}")
        tty_print(f"{BOLD}╚══════════════════════════════════════════════════════╝{RESET}")
        return

    tty_print("")
    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            tty_print(f"{DIM}{line}{RESET}")
        elif line.startswith("@@"):
            tty_print(f"{CYAN}{line}{RESET}")
        elif line.startswith("+"):
            tty_print(f"{GREEN}{line}{RESET}")
        elif line.startswith("-"):
            tty_print(f"{RED}{line}{RESET}")
        else:
            tty_print(line.rstrip())

    tty_print(f"\n{BOLD}╚══════════════════════════════════════════════════════╝{RESET}")


# ── Interactive Choice ────────────────────────────────────────────────────────

def open_editor(text: str) -> str:
    """Open $EDITOR with the text and return the edited result."""
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(text)
        tmp = f.name
    subprocess.run([editor, tmp])
    with open(tmp) as f:
        edited = f.read().strip()
    os.unlink(tmp)
    return edited if edited else text


def get_user_choice(original: str, enhanced: str) -> str:
    """Show menu and return the final prompt to use."""
    tty_print(f"\n{BOLD}What would you like to do?{RESET}")
    tty_print(f"  {GREEN}[a]{RESET} Accept enhanced prompt")
    tty_print(f"  {YELLOW}[e]{RESET} Edit enhanced prompt")
    tty_print(f"  {RED}[r]{RESET} Reject — use original\n")

    # Use gum if available for nicer UX
    if has_command("gum"):
        result = subprocess.run(
            ["gum", "choose", "--cursor-prefix", "→ ", "Accept", "Edit", "Reject"],
            capture_output=True,
            text=True,
        )
        choice = result.stdout.strip().lower()
    else:
        choice = tty_input("Choice (a/e/r) [a]: ").lower() or "a"

    if choice in ("a", "accept"):
        tty_print(f"{GREEN}✓ Using enhanced prompt{RESET}\n")
        return enhanced
    elif choice in ("e", "edit"):
        tty_print(f"{YELLOW}Opening editor...{RESET}\n")
        if has_command("gum"):
            result = subprocess.run(
                ["gum", "write", "--placeholder", "Edit your prompt...", "--value", enhanced],
                capture_output=True,
                text=True,
            )
            edited = result.stdout.strip() if result.stdout.strip() else enhanced
        else:
            edited = open_editor(enhanced)
        tty_print(f"{GREEN}✓ Using edited prompt{RESET}\n")
        return edited
    else:
        tty_print(f"{YELLOW}✓ Using original prompt{RESET}\n")
        return original


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # Read hook input from stdin
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
        prompt = data.get("prompt", "")
    except json.JSONDecodeError:
        prompt = raw.strip()

    if not prompt or should_skip(prompt):
        sys.exit(0)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        tty_print(f"{YELLOW}⚒  prompt-forge: ANTHROPIC_API_KEY not set — skipping enhancement.{RESET}")
        tty_print(f"{YELLOW}   Add to ~/.zshrc: export ANTHROPIC_API_KEY=sk-ant-...{RESET}")
        sys.exit(0)

    # Check if user has disabled prompt forge
    if os.environ.get("PROMPT_FORGE_DISABLED", "").lower() in ("1", "true", "yes"):
        sys.exit(0)

    try:
        enhanced = call_haiku(prompt, api_key)
    except Exception as e:
        tty_print(f"{YELLOW}prompt-forge: enhancement failed ({e}), using original{RESET}")
        sys.exit(0)

    # No meaningful change — pass through silently
    if enhanced.strip() == prompt.strip() or not enhanced.strip():
        sys.exit(0)

    show_diff(prompt, enhanced)
    final = get_user_choice(prompt, enhanced)

    # Only output if user chose something different from the original.
    # No output = Claude Code uses the original prompt unchanged.
    if final.strip() != prompt.strip():
        print(json.dumps({"prompt": final}))


if __name__ == "__main__":
    main()
