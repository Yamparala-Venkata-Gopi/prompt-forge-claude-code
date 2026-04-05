#!/usr/bin/env bash
set -euo pipefail

# ── prompt-forge-claude-code installer ───────────────────────────────────────

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
HOOKS_INSTALL_DIR="${CLAUDE_DIR}/hooks/prompt-forge"
SETTINGS_FILE="${CLAUDE_DIR}/settings.json"

GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
BOLD="\033[1m"
RESET="\033[0m"

print_header() {
  echo -e "\n${BOLD}${CYAN}⚒  prompt-forge-claude-code${RESET}"
  echo -e "${CYAN}   Prompt enhancement for Claude Code${RESET}\n"
}

check_prerequisites() {
  if ! command -v python3 &>/dev/null; then
    echo -e "${YELLOW}⚠  python3 is required but not found. Please install Python 3.8+.${RESET}"
    exit 1
  fi

  if ! command -v jq &>/dev/null; then
    echo -e "${YELLOW}⚠  jq is required for settings.json merging. Install with: brew install jq${RESET}"
    exit 1
  fi

  echo -e "${GREEN}✓ Prerequisites OK${RESET}"
}

install_hook_script() {
  mkdir -p "${HOOKS_INSTALL_DIR}"
  cp "${REPO_DIR}/hooks/enhance_prompt.py" "${HOOKS_INSTALL_DIR}/enhance_prompt.py"
  chmod +x "${HOOKS_INSTALL_DIR}/enhance_prompt.py"
  echo -e "${GREEN}✓ Hook script installed to ${HOOKS_INSTALL_DIR}${RESET}"
}

merge_settings() {
  # Create settings.json if it doesn't exist
  if [ ! -f "${SETTINGS_FILE}" ]; then
    echo '{}' > "${SETTINGS_FILE}"
  fi

  # Build the hook entry
  HOOK_ENTRY=$(cat <<'EOF'
{
  "matcher": "",
  "hooks": [
    {
      "type": "command",
      "command": "python3 ~/.claude/hooks/prompt-forge/enhance_prompt.py",
      "timeout": 20000
    }
  ]
}
EOF
)

  # Check if hook already registered
  if jq -e '.hooks.UserPromptSubmit' "${SETTINGS_FILE}" &>/dev/null; then
    # Check if our hook is already there
    EXISTING=$(jq -r '.hooks.UserPromptSubmit[].hooks[].command' "${SETTINGS_FILE}" 2>/dev/null || echo "")
    if echo "${EXISTING}" | grep -q "prompt-forge"; then
      echo -e "${YELLOW}⚠  Hook already registered in ${SETTINGS_FILE} — skipping${RESET}"
      return
    fi
    # Append to existing array
    UPDATED=$(jq --argjson entry "${HOOK_ENTRY}" \
      '.hooks.UserPromptSubmit += [$entry]' "${SETTINGS_FILE}")
  else
    # Create the hook key
    UPDATED=$(jq --argjson entry "${HOOK_ENTRY}" \
      '.hooks.UserPromptSubmit = [$entry]' "${SETTINGS_FILE}")
  fi

  echo "${UPDATED}" > "${SETTINGS_FILE}"
  echo -e "${GREEN}✓ Registered UserPromptSubmit hook in ${SETTINGS_FILE}${RESET}"
}

check_api_key() {
  if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo -e "\n${YELLOW}⚠  ANTHROPIC_API_KEY is not set.${RESET}"
    echo    "   prompt-forge uses Claude Haiku to enhance prompts."
    echo    "   Add to your shell profile:"
    echo -e "   ${CYAN}export ANTHROPIC_API_KEY=sk-ant-...${RESET}\n"
  else
    echo -e "${GREEN}✓ ANTHROPIC_API_KEY found${RESET}"
  fi
}

check_optional_gum() {
  if command -v gum &>/dev/null; then
    echo -e "${GREEN}✓ gum detected — enhanced TUI enabled${RESET}"
  else
    echo -e "${YELLOW}ℹ  gum not found — using basic terminal UI${RESET}"
    echo    "   For a nicer experience: brew install charmbracelet/tap/gum"
  fi
}

print_done() {
  echo -e "\n${BOLD}${GREEN}✓ prompt-forge-claude-code installed!${RESET}\n"
  echo    "  Every prompt you submit in Claude Code will now be"
  echo    "  automatically enhanced before Claude sees it."
  echo -e "\n  ${BOLD}Controls:${RESET}"
  echo    "   • Accept  — use the enhanced prompt"
  echo    "   • Edit    — tweak it before submitting"
  echo    "   • Reject  — use your original prompt"
  echo -e "\n  ${BOLD}Disable temporarily:${RESET}"
  echo -e "   ${CYAN}export PROMPT_FORGE_DISABLED=1${RESET}"
  echo -e "\n  ${BOLD}Uninstall:${RESET}"
  echo -e "   ${CYAN}./uninstall.sh${RESET}\n"
}

# ── Run ───────────────────────────────────────────────────────────────────────
print_header
check_prerequisites
install_hook_script
merge_settings
check_api_key
check_optional_gum
print_done
