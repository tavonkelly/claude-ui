# claude-ui-text

Coding agents write UI text like prose. Headings get a paragraph underneath, buttons describe themselves, and pages grow "How it works" sections. People scan screens instead of reading them: in Nielsen Norman Group's tests, 79% of users scanned a new page, and cutting a site's text by half made it 58% more usable. Text written like prose gets in their way.

This repo gives the agent a short standard for UI text and checks every UI string it writes. It works in Claude Code, Codex and opencode.

## What's in it

| Path | Contents |
|---|---|
| `skills/ui-text/SKILL.md` | The standard: word limits per element, rules, screen states, text accessibility (WCAG 2.2 AA), CLI and API text, and 22 before-and-after pairs |
| `skills/ui-text/bin/ui-text` | The checker. Python 3.9 or later, no dependencies. Reads HTML, JSX/TSX, Svelte, Vue, Dart and Swift |
| `.claude-plugin/`, `hooks/hooks.json` | The Claude Code plugin |
| `codex/hooks.json` | Hooks for Codex |
| `opencode/ui-text.js` | A plugin for opencode |
| `examples/` | Two pages written to the standard. Both pass the checker with 0 flags |

## How it works

With the hooks or the plugin installed:

1. When a session starts, the agent gets a three-line UI text rule (Claude Code and Codex).
2. The agent's first UI edit in a session is refused until it loads the skill. This happens once per session.
3. After each edit of a UI file, the agent gets a list of flags. Only the strings it added or changed are checked, so old files don't bury it in flags.
4. While flags are open, the agent can't end its turn (Claude Code and Codex). The stop is blocked once. The agent fixes the strings, or waives the ones that are prose on purpose and lists the waivers for you.

The checker flags:

| Rule | Flags |
|---|---|
| `long-label` | A button, label, heading, tab or menu item over 4 words, or a question heading over 8 |
| `long-text` | Any other string over 12 words |
| `multi-sentence` | A string with two or more sentences of 5 or more words each |
| `phrase` | "you can", "lets you", "allows you", "this page", "this screen", "so that", "how it works", "under the hood", "please", "sorry", "thank you", "thanks for", "click here", "simply", "oops" |
| `generic-button` | A button labeled OK, Submit, Yes or No |
| `instruction-label` | A label or heading that starts with Enter, Type, Select, Choose or Pick |

Patterns can't judge meaning, so short narration still passes the checker. The skill covers what the checker can't see.

A project's own content guide, design system wording or term list wins over the skill.

## Install

All three need `python3` 3.9 or later on your PATH.

### Claude Code

Run these in Claude Code:

```
/plugin marketplace add tavonkelly/claude-ui-text
/plugin install ui-text@claude-ui-text
```

Start a new session to load it. The plugin installs the skill and all four hooks, so there is nothing else to set up.

### Claude Code without the plugin

```bash
git clone https://github.com/tavonkelly/claude-ui-text.git
```

```bash
mkdir -p ~/.claude/skills && cp -R claude-ui-text/skills/ui-text ~/.claude/skills/
```

Then add this `hooks` block to `~/.claude/settings.json`. If the file already has a `hooks` block, add each entry to the matching list.

```json
"hooks": {
  "SessionStart": [{"hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/skills/ui-text/bin/ui-text\" hook session", "timeout": 10}]}],
  "PreToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/skills/ui-text/bin/ui-text\" hook pre", "timeout": 10}]}],
  "PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/skills/ui-text/bin/ui-text\" hook post", "timeout": 10}]}],
  "Stop": [{"hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/skills/ui-text/bin/ui-text\" hook stop", "timeout": 10}]}]
}
```

### Codex

```bash
git clone https://github.com/tavonkelly/claude-ui-text.git
```

```bash
mkdir -p ~/.codex/skills && cp -R claude-ui-text/skills/ui-text ~/.codex/skills/
```

If you don't have a `~/.codex/hooks.json` yet, copy the one in this repo:

```bash
cp claude-ui-text/codex/hooks.json ~/.codex/hooks.json
```

If you already have one, add the four entries from `codex/hooks.json` to it. Then start Codex, run `/hooks` and trust the new hooks. Codex skips a hook until you trust it, and again each time it changes.

Codex sends file edits as `apply_patch` text, and the checker reads the patch to find which files and strings changed. The Codex hooks are tested with sample payloads in each shape Codex has used for edits, not yet in a live Codex session. If they don't fire for you, please open an issue with your Codex version.

### opencode

```bash
git clone https://github.com/tavonkelly/claude-ui-text.git
```

```bash
mkdir -p ~/.config/opencode/skills ~/.config/opencode/plugins
```

```bash
cp -R claude-ui-text/skills/ui-text ~/.config/opencode/skills/ && cp claude-ui-text/opencode/ui-text.js ~/.config/opencode/plugins/
```

Then add the rule below to `~/.config/opencode/AGENTS.md`. opencode has no hook for the end of a turn, so flags appear only in each edit's result. The plugin looks for the checker in `~/.config/opencode/skills`, `~/.claude/skills` and `~/.agents/skills`. Set `UI_TEXT_BIN` to the checker's path if you put it somewhere else.

### The rule

The session hook adds this rule in Claude Code and Codex. Without hooks, or in opencode, add it to `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` or `~/.config/opencode/AGENTS.md`:

```markdown
## UI text

Text on a screen is not prose. Name the thing or the action in a few words, show state as state, and keep explanations of how the system works off the screen. Before writing or changing any text a product's user sees, load the ui-text skill.
```

## Commands

```
ui-text check PATH... [--ignore-rule RULE] [--only GLOB] [--json]
ui-text flags
ui-text waive ID [ID...] --reason TEXT
ui-text selftest
```

`check` reads whole files or folders and exits with 1 when it finds flags, so it also works in CI:

```bash
python3 skills/ui-text/bin/ui-text check src/
```

There are no inline ignore comments and no ignored folders. To skip a rule for one run, pass `--ignore-rule`.

Flags and waivers last for one session. The checker keeps them in `~/.cache/ui-text`, outside your repos. Set `UI_TEXT_STATE` to keep them somewhere else. The checker makes no network calls.

## Updating

For the plugin, run `/plugin marketplace update claude-ui-text` in Claude Code. For a manual install, run `git pull` in your clone and copy the files again.

## Tests

```bash
python3 skills/ui-text/bin/ui-text selftest
```

```bash
python3 skills/ui-text/tests/test_hooks.py
```

The first runs the checker on good and bad samples in each file type. The second sends Claude Code, Codex and opencode hook payloads to the checker.

## Sources

The standard draws on the GOV.UK Service Manual (writing for user interfaces), the Microsoft Win32 UI text guide and Writing Style Guide, Apple's Human Interface Guidelines (Writing, Buttons, Alerts), Material 3 content design, and the content guidelines from Shopify, Atlassian and Mailchimp. It also uses Nielsen Norman Group research on how users read on the web, icon usability and the 10 usability heuristics, plus WCAG 2.2, ISO 9241-110 and ISO 9241-112.

Where these guides disagree, the skill picks one default and states it, so the agent doesn't have to choose.

## License

MIT
