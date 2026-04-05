# Changelog

All notable changes to prompt-forge-claude-code are documented here.

## [2.0.0] - 2026-04-04

### Breaking Changes

- **Complete architecture redesign.** The hook no longer attempts to modify prompts
  or show an interactive accept/edit/reject menu. Those features were incompatible
  with the Claude Code hook system (hooks are non-interactive and cannot modify
  prompt text).
- **Removed dependencies**: `gum` CLI, `/dev/tty` access, and the `$EDITOR`-based
  edit flow are gone. The plugin now uses pure Python stdlib with zero external
  dependencies.
- **New user experience**: The hook now enhances your prompt via Haiku and presents
  both versions through Claude itself. You choose "Use enhanced", "Use original",
  or "Edit" before Claude proceeds. Full visibility, full control.

### Added

- **OAuth credential support**: Reads `claudeAiOauth.accessToken` from
  `~/.claude/.credentials.json`. This is how most Claude Code users authenticate.
  Previously only `ANTHROPIC_API_KEY` env var and macOS keychain were supported.
- **Slash command skip**: Prompts starting with `/` are now skipped automatically.
- **More confirmation words skipped**: Added `sure`, `thanks`, `lgtm`, `yep`,
  `nope`, `go ahead`, `proceed`, etc.
- **`PROMPT_FORGE_MODE` env var**: Set to `off` to disable the auto-hook while
  keeping the `/forge` skill available.
- **Proper `hookSpecificOutput` format**: Uses the documented Claude Code hook
  output schema (`hookSpecificOutput.additionalContext`).
- **60 unit tests** covering skip logic, API key resolution (env var, credentials
  file, OAuth, macOS keychain), API calls, main flow, error handling, disabled mode,
  cross-platform checks, and performance.

### Fixed

- **Hook output format**: v1 returned `{"prompt": "..."}` which Claude Code silently
  ignored. v2 uses the correct `hookSpecificOutput.additionalContext` format.
- **marketplace.json validation**: Removed invalid root-level keys (`$schema`,
  `description`, `version`). Now passes `claude plugin validate` cleanly.
- **Cross-platform API key resolution**: Works on macOS, Linux, and Windows.
- **Removed debug logging**: No longer writes to `/tmp/prompt-forge-debug.log`.
- **Fail-open on all errors**: Any failure exits silently (code 0), never blocking
  the user's prompt.

### Removed

- Interactive TTY-based accept/edit/reject menu (incompatible with hook system)
- `gum` CLI integration
- `/dev/tty` direct access
- `$EDITOR` integration for prompt editing
- Debug file logging

### Upgrading from v1

1. Run `/plugin update` in Claude Code to pull the latest version
2. Run `/reload-plugins` to load the new hook and skill
3. The `PROMPT_FORGE_DISABLED` env var still works as before
4. The new `PROMPT_FORGE_MODE=off` env var is available for finer control
5. No configuration migration needed -- all v1 env vars are still supported

## [1.0.1] - 2025-12-01

- Initial public release
- Interactive prompt enhancement via TTY-based accept/edit/reject menu
- macOS keychain and env var API key support
