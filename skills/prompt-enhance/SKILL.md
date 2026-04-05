# Prompt Enhance

## When to Activate

Activate this skill when the user says:
- "enhance this prompt"
- "improve my prompt"
- "forge this prompt"
- "refine my prompt"
- "make this prompt better"
- "how should I phrase this"
- "/forge"

Do NOT activate for:
- General coding questions
- File editing requests
- Build or test commands

## What This Skill Does

Analyzes the user's prompt and rewrites it to be more effective for Claude Code sessions.

## Core Enhancement Principles

### 1. Specificity Over Vagueness
- **Before**: "fix the bug"
- **After**: "Fix the off-by-one error in `process_items()` in `src/processor.rs` — the loop iterates one item too many when the input list is empty"

### 2. Add Implied Constraints
- **Before**: "refactor the auth module"
- **After**: "Refactor the auth module in `src/auth/mod.rs` to use the `tower::Service` trait. Preserve the existing public API — no breaking changes to function signatures. Keep all existing tests passing."

### 3. Scope Definition
- **Before**: "add tests"
- **After**: "Add unit tests for `ForwardProxyHandler::process_request()` in `crates/agentgateway/src/forward_proxy/mod.rs`. Cover: (1) Allow decision, (2) Block decision with 403 response, (3) AllowWithInspection with body buffering. Use the existing wiremock test patterns from `tests/` as reference."

### 4. Context Injection
Always include:
- Relevant file paths when known
- Function or struct names
- The expected outcome, not just the action

## Output Format

Present the enhanced prompt in a clear diff-style view:

```
ORIGINAL:
  [original prompt]

ENHANCED:
  [enhanced prompt]

CHANGES:
  • [what was added or clarified]
  • [what constraint was made explicit]
```

Then ask: "Use this enhanced prompt? (yes / edit / no)"
