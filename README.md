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

```bash
/plugin install Yamparala-Venkata-Gopi/prompt-forge-claude-code
```

That's it. Claude Code's plugin system handles everything — no shell scripts, no manual config.

### Prerequisites

- Optional: `gum` for a nicer TUI (`brew install charmbracelet/tap/gum`)

> **No API key setup needed.** Claude Code already has your Anthropic API key — prompt-forge uses it automatically.

---

## Uninstall

```bash
/plugin uninstall Yamparala-Venkata-Gopi/prompt-forge-claude-code
```

---

## Configuration

### Disable Temporarily

```bash
export PROMPT_FORGE_DISABLED=1
```

### When Prompts Are Skipped (No Enhancement)

prompt-forge silently skips enhancement for:
- Short prompts under 4 words
- Simple confirmations: `yes`, `no`, `ok`, `done`, `continue`
- Already-detailed prompts over 600 characters
- When `PROMPT_FORGE_DISABLED=1`

### Cost

Uses **Claude Haiku** — the fastest and cheapest Claude model.
Typical cost per enhancement: **< $0.001**.

---

## How It Works

prompt-forge uses Claude Code's native `UserPromptSubmit` hook via the plugin system.

```
User submits prompt
        │
        ▼
UserPromptSubmit hook fires
        │
        ▼
enhance_prompt.py runs (${CLAUDE_PLUGIN_ROOT}/hooks/enhance_prompt.py)
  → calls Claude Haiku API
  → shows colored diff in terminal
  → reads user choice via /dev/tty
        │
        ▼
Returns {"prompt": "<chosen version>"} to Claude Code
```

---

## Manual Usage (Without Auto-Hook)

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
│   ├── hooks.json           # UserPromptSubmit hook (auto-discovered)
│   └── enhance_prompt.py    # Core hook script
└── README.md
```

---

## Contributing

PRs welcome.

Ideas:
- Windows support
- Project-aware enhancement (reads `CLAUDE.md` for context)
- Enhancement history log
- Per-project enable/disable

---

## License

MIT
