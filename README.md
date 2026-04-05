# prompt-forge-claude-code

Automatic prompt enhancement for Claude Code. Enhances your prompts via Claude Haiku and presents both versions for you to choose from — full visibility, full control. Also includes a manual `/forge` skill for on-demand enhancement.

---

## How It Works

prompt-forge operates in two modes:

### Auto Mode (Default)

A `UserPromptSubmit` hook intercepts your prompt, enhances it via Claude Haiku (~2s), and presents both versions for you to choose from. You stay in control.

```
You type: "fix the auth bug"
        |
        v
Hook fires → Haiku enhances (~2s)
        |
        v
Claude shows you:
  ┌─────────────────────────────────────────────────┐
  │  Prompt Forge enhanced your request:             │
  │                                                  │
  │  Original: "fix the auth bug"                    │
  │                                                  │
  │  Enhanced: "Fix the auth bug in the login        │
  │  handler — check for null session, incorrect     │
  │  password comparison, or missing error handling.  │
  │  Ensure existing tests pass."                    │
  │                                                  │
  │  1. Use enhanced                                 │
  │  2. Use original                                 │
  │  3. Edit                                         │
  └─────────────────────────────────────────────────┘
        |
        v
You choose → Claude proceeds with your choice
```

Your prompt is never silently modified. You always see the enhancement and decide what happens next.

### Manual Mode (/forge)

Type `/forge <your prompt>` in Claude Code for an on-demand enhancement:

```
/forge fix the auth bug
```

Claude will show you a before/after comparison and ask if you want to use the enhanced version.

---

## Installation

Inside a Claude Code session:

```
/plugin marketplace add Yamparala-Venkata-Gopi/prompt-forge-claude-code
```

```
/plugin install prompt-forge-claude-code@prompt-forge-claude-code
```

### Prerequisites

- **Claude Code** installed and authenticated
- **Python 3.8+** available as `python3`
- **Anthropic API key** set via one of:
  - `ANTHROPIC_API_KEY` environment variable (recommended)
  - `~/.claude/.credentials.json` file (Linux/Windows, auto-detected)
  - macOS keychain (auto-detected)

---

## Uninstall

```
/plugin uninstall prompt-forge-claude-code@prompt-forge-claude-code
```

---

## Configuration

### Environment Variables

| Variable | Values | Default | Description |
|---|---|---|---|
| `PROMPT_FORGE_DISABLED` | `1`, `true`, `yes` | unset | Disable all prompt enhancement |
| `PROMPT_FORGE_MODE` | `auto`, `off` | `auto` | `auto` = silent hook enhancement; `off` = disable hook |
| `ANTHROPIC_API_KEY` | API key string | unset | Anthropic API key for Haiku calls |

### When Prompts Are Skipped

The hook silently skips enhancement for:
- Empty prompts or whitespace only
- Short prompts under 4 words
- Simple confirmations: `yes`, `no`, `ok`, `done`, `continue`, `y`, `n`, etc.
- Slash commands starting with `/`
- Already-detailed prompts over 600 characters
- When `PROMPT_FORGE_DISABLED=1`
- When `PROMPT_FORGE_MODE=off`

### Cost

Uses Claude Haiku -- the fastest and cheapest Claude model. Typical cost per enhancement: less than $0.001.

---

## Cross-Platform Support

prompt-forge works on macOS, Linux, and Windows (via WSL or Python).

- **API key resolution** checks env var, credentials file, and macOS keychain in order
- **No platform-specific tools** required (no `gum`, no `/dev/tty`)
- **Python stdlib only** -- zero external dependencies

---

## Plugin Structure

```
prompt-forge-claude-code/
  .claude-plugin/
    plugin.json              Plugin manifest
    marketplace.json         Marketplace metadata
  agents/
    prompt-forge.md          Agent definition (uses Haiku)
  skills/
    prompt-enhance/
      SKILL.md               /forge skill definition
  hooks/
    hooks.json               UserPromptSubmit hook config
    enhance_prompt.py        Core hook script (Python)
  tests/
    test_enhance_prompt.py   Unit tests (60 tests)
  CHANGELOG.md               Version history and upgrade notes
  README.md
  package.json
```

---

## Upgrading from v1

v2 is a complete redesign. The hook no longer uses TTY-based interactive menus
(which were incompatible with the Claude Code hook system). Instead, Claude itself
presents the enhancement and lets you choose.

```bash
# 1. Update the plugin
/plugin update

# 2. Reload to pick up new hook + skill files
/reload-plugins
```

That's it. Your existing `PROMPT_FORGE_DISABLED` env var still works. See
[CHANGELOG.md](CHANGELOG.md) for full details.

---

## Development

### Run tests

```bash
python3 tests/test_enhance_prompt.py
```

All 60 tests use mocks — no API key or network access required.

### Test locally in Claude Code

```bash
claude --plugin-dir /path/to/prompt-forge-claude-code
```

Then type any prompt with 4+ words to see the enhancement flow.

### Validate plugin before publishing

```bash
claude plugin validate /path/to/prompt-forge-claude-code
```

---

## License

MIT
