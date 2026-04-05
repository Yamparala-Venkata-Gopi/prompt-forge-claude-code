# ⚒ prompt-forge-claude-code

> Automatic prompt enhancement for Claude Code — intercepts your prompts, refines them with AI, shows you the diff, and lets you accept, edit, or reject before Claude ever sees it.

---

## What It Does

You type a prompt. Before Claude Code processes it, **prompt-forge** steps in:

1. Sends your prompt to Claude Haiku for refinement
2. Shows a colored diff of what changed
3. Asks you to **Accept**, **Edit**, or **Reject**
4. Submits your chosen version to Claude

```
You typed:
  "fix the bug"

prompt-forge suggests:
  "Fix the null pointer dereference in `handle_request()` in src/proxy.rs —
   it panics when the request body is empty. Add a nil guard at the top of
   the function and add a regression test."

╔══ Prompt Forge ══════════════════════════════════════╗
- fix the bug
+ Fix the null pointer dereference in `handle_request()` in src/proxy.rs —
+ it panics when the request body is empty. Add a nil guard at the top of
+ the function and add a regression test.
╚══════════════════════════════════════════════════════╝

What would you like to do?
  [a] Accept enhanced prompt
  [e] Edit enhanced prompt
  [r] Reject — use original
```

---

## Installation

### Prerequisites

- Python 3.8+
- `jq` (`brew install jq`)
- `ANTHROPIC_API_KEY` set in your environment
- Optional: `gum` for a nicer TUI (`brew install charmbracelet/tap/gum`)

### Install

```bash
git clone https://github.com/Yamparala-Venkata-Gopi/prompt-forge-claude-code.git
cd prompt-forge-claude-code
chmod +x install.sh
./install.sh
```

The installer:
- Copies the hook script to `~/.claude/hooks/prompt-forge/`
- Registers the `UserPromptSubmit` hook in `~/.claude/settings.json`

### Uninstall

```bash
./uninstall.sh
```

---

## Configuration

### Disable Temporarily

```bash
export PROMPT_FORGE_DISABLED=1
```

### When Prompts Are Skipped (No Enhancement)

prompt-forge skips enhancement for:
- Very short prompts (< 4 words)
- Simple confirmations: `yes`, `no`, `ok`, `done`, `continue`
- Long prompts (> 600 chars) — already detailed enough
- If `ANTHROPIC_API_KEY` is not set

### Cost

Uses **Claude Haiku** — the fastest and cheapest Claude model.
Typical cost per enhancement: **< $0.001** (less than a tenth of a cent).

---

## How It Works

prompt-forge uses Claude Code's `UserPromptSubmit` hook, which fires on every prompt before Claude processes it.

```
User submits prompt
        │
        ▼
UserPromptSubmit hook fires
        │
        ▼
enhance_prompt.py runs
  → calls Claude Haiku API
  → shows colored diff on terminal
  → reads user choice via /dev/tty
        │
        ▼
Returns {"prompt": "<chosen version>"}
        │
        ▼
Claude Code processes the final prompt
```

---

## Manual Usage (Without Auto-Hook)

You can also invoke the agent manually for a specific prompt:

In Claude Code, type:
```
/forge
```
or
```
enhance this prompt: fix the authentication bug
```

---

## Plugin Structure

```
prompt-forge-claude-code/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── agents/
│   └── prompt-forge.md      # Manual-invoke agent
├── skills/
│   └── prompt-enhance/
│       └── SKILL.md         # Skill definition
├── hooks/
│   ├── hooks.json           # UserPromptSubmit hook config
│   └── enhance_prompt.py    # Core hook script
├── install.sh               # Installer
├── uninstall.sh             # Uninstaller
└── README.md
```

---

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

Ideas for contributions:
- Windows (`install.ps1`) support
- Linux support
- Project-aware enhancement (reads `CLAUDE.md` for context)
- Enhancement history log
- Per-project enable/disable via `.claude/settings.json`

---

## License

MIT
