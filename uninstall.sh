#!/usr/bin/env bash
set -euo pipefail

CLAUDE_DIR="${HOME}/.claude"
HOOKS_INSTALL_DIR="${CLAUDE_DIR}/hooks/prompt-forge"
SETTINGS_FILE="${CLAUDE_DIR}/settings.json"

GREEN="\033[32m"
YELLOW="\033[33m"
BOLD="\033[1m"
RESET="\033[0m"

echo -e "\n${BOLD}Uninstalling prompt-forge-claude-code...${RESET}\n"

# Remove hook scripts
if [ -d "${HOOKS_INSTALL_DIR}" ]; then
  rm -rf "${HOOKS_INSTALL_DIR}"
  echo -e "${GREEN}✓ Removed hook scripts${RESET}"
else
  echo -e "${YELLOW}ℹ  Hook directory not found — skipping${RESET}"
fi

# Remove hook entry from settings.json
if [ -f "${SETTINGS_FILE}" ] && command -v jq &>/dev/null; then
  UPDATED=$(jq 'del(.hooks.UserPromptSubmit[] | select(.hooks[].command | contains("prompt-forge")))' \
    "${SETTINGS_FILE}" 2>/dev/null || cat "${SETTINGS_FILE}")
  echo "${UPDATED}" > "${SETTINGS_FILE}"
  echo -e "${GREEN}✓ Removed hook from ${SETTINGS_FILE}${RESET}"
fi

echo -e "\n${BOLD}${GREEN}✓ Uninstalled.${RESET}\n"
