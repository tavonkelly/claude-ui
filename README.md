# claude-ui

Coding agents build screens the way they write documents. Headings get a paragraph underneath, buttons describe themselves, and every section lands in its own bordered card, with a row of stat tiles on top and three buttons of equal weight at the bottom. People scan screens instead of reading them: in Nielsen Norman Group's tests, 79% of users scanned a new page, and cutting a site's text by half made it 58% more usable. Extra words and extra boxes both get in the way.

This repo gives the agent two short standards, one for UI text and one for layout, and a checker that runs on every UI file it edits. It works in Claude Code, Codex and opencode.

## What's in it

| Path | Contents |
|---|---|
| `skills/ui-text/SKILL.md` | The text standard: word limits per element, rules, screen states, text accessibility (WCAG 2.2 AA), CLI and API text, and 22 before-and-after pairs |
| `skills/ui-layout/SKILL.md` | The layout standard: a plan before each new screen, what goes on a screen, order and grouping, cards, primary actions, spacing and type, responsive layout, and patterns for forms, settings, lists, dashboards, empty states, tool pages and landing pages |
| `skills/ui-text/bin/ui-standards` | The checker. Python 3.9 or later, no dependencies. Reads HTML, Vue, Svelte, JSX/TSX, CSS, Dart and Swift |
| `.claude-plugin/`, `hooks/hooks.json` | The Claude Code plugin |
| `codex/hooks.json` | Hooks for Codex |
| `opencode/ui-standards.js` | A plugin for opencode |
| `examples/` | Two pages built to both standards. Both pass the checker and the render with 0 flags |

## How it works

With the hooks or the plugin installed:

1. When a session starts, the agent gets a short text rule and a short layout rule (Claude Code and Codex).
2. The agent's first UI edit in a session is refused until it loads both skills. This happens once per session.
3. After each edit of a UI file, the agent gets a list of flags. Only what the edit added or changed is checked, so old files don't bury it in flags.
4. While problems are open, the agent can't end its turn (Claude Code and Codex). The stop is blocked once. The agent fixes them, or waives the ones that are intended and lists the waivers for you.

Layout flags come in two tiers. Problems block the end of the turn like text flags. Advice appears after the edit and never blocks, because those checks are more likely to be wrong.

### Text rules

| Rule | Flags |
|---|---|
| `long-label` | A button, label, heading, tab or menu item over 4 words, or a question heading over 8 |
| `long-text` | Any other string over 12 words |
| `multi-sentence` | A string with two or more sentences of 5 or more words each |
| `phrase` | "you can", "lets you", "allows you", "this page", "this screen", "so that", "how it works", "under the hood", "please", "sorry", "thank you", "thanks for", "click here", "simply", "oops" |
| `generic-button` | A button labeled OK, Submit, Yes or No |
| `instruction-label` | A label or heading that starts with Enter, Type, Select, Choose or Pick |

### Layout rules

| Rule | Tier | Flags |
|---|---|---|
| `nested-card` | Problem | A card inside a card |
| `single-control-card` | Problem | A card around a single control or a single line |
| `multiple-primary` | Problem in HTML, advice in components | More than one primary-styled action in a view |
| `off-scale-spacing` | Problem | A margin, padding or gap that isn't 4, 8, 12, 16, 24, 32, 48 or 64px, or one of the project's spacing tokens |
| `heading-skip` | Problem | A skipped heading level, or more than one h1 in a view |
| `stat-tiles` | Advice | A row of stat tiles or big numbers |
| `card-grid` | Advice | 3 or more identical cards with an icon, heading and text |
| `type-scale` | Advice | More than 4 font sizes or 2 font weights |
| `deep-nesting` | Advice | Elements nested more than 8 levels deep |
| `badge-above-h1`, `eyebrow`, `emoji-icon`, `gradient-text`, `accent-stripe`, `repeated-cta` | Advice | Landing-page habits |

A card is a box with a border, a shadow, or a fill with rounded corners, or anything named card, panel, tile or box. A primary action is a button or link with `primary` in its class or variant, `variant="filled"`, `variant="solid"`, SwiftUI `.borderedProminent` or Flutter `FilledButton`. A component file isn't a whole view, so its primary-action and h1 counts are advice only.

Patterns can't judge meaning or purpose, so short narration and a layout that buries the main task can both pass. The skills cover what the checker can't see.

A project's own content guide, design system or spacing tokens win over the skills.

### Rendering

`ui-standards render FILE|URL` opens a page in headless Chrome or Chromium. It saves screenshots at 1280 and 375px wide and checks the layout at 320px:

| Rule | Tier | Flags |
|---|---|---|
| `overflow-x` | Problem | The page scrolls sideways at 320px |
| `text-overlap` | Problem | Text overlapping other text |
| `hidden-visible` | Problem | An element marked `hidden` that still shows |
| `nested-card`, `single-control-card`, `multiple-primary` | Problem | The same rules, measured on the rendered page, including markup built at runtime |
| `small-target` | Advice | A click target under 24px with no clear space around it |
| `long-lines` | Advice | Text lines over 80 characters |

The checker talks to Chrome over its debugging pipe, so nothing else needs installing. Rendering isn't required. The ui-layout skill tells the agent when a render is worth it: after building a screen or changing its structure, once per kind of page.

## Install

All three agents need `python3` 3.9 or later on your PATH. Rendering also needs Chrome or Chromium.

### Claude Code

Run these in Claude Code:

```
/plugin marketplace add tavonkelly/claude-ui
/plugin install ui-standards@claude-ui
```

On Claude Code 2.1.275 or later, one command does both:

```
/plugin install ui-standards --marketplace tavonkelly/claude-ui
```

Start a new session to load it. The plugin installs both skills and all four hooks, so there is nothing else to set up.

### Claude Code without the plugin

```bash
git clone https://github.com/tavonkelly/claude-ui.git
```

```bash
mkdir -p ~/.claude/skills && cp -R claude-ui/skills/ui-text claude-ui/skills/ui-layout ~/.claude/skills/
```

Then add this `hooks` block to `~/.claude/settings.json`. If the file already has a `hooks` block, add each entry to the matching list.

```json
"hooks": {
  "SessionStart": [{"hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/skills/ui-text/bin/ui-standards\" hook session", "timeout": 10}]}],
  "PreToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/skills/ui-text/bin/ui-standards\" hook pre", "timeout": 10}]}],
  "PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/skills/ui-text/bin/ui-standards\" hook post", "timeout": 15}]}],
  "Stop": [{"hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/skills/ui-text/bin/ui-standards\" hook stop", "timeout": 15}]}]
}
```

### Codex

```bash
git clone https://github.com/tavonkelly/claude-ui.git
```

```bash
mkdir -p ~/.codex/skills && cp -R claude-ui/skills/ui-text claude-ui/skills/ui-layout ~/.codex/skills/
```

If you don't have a `~/.codex/hooks.json` yet, copy the one in this repo:

```bash
cp claude-ui/codex/hooks.json ~/.codex/hooks.json
```

If you already have one, add the four entries from `codex/hooks.json` to it. Then start Codex, run `/hooks` and trust the new hooks. Codex skips a hook until you trust it, and again each time it changes.

Codex sends file edits as `apply_patch` text, and the checker reads the patch to find which files and lines changed. The Codex hooks are tested with sample payloads in each shape Codex has used for edits, not yet in a live Codex session. If they don't fire for you, please open an issue with your Codex version.

### opencode

```bash
git clone https://github.com/tavonkelly/claude-ui.git
```

```bash
mkdir -p ~/.config/opencode/skills ~/.config/opencode/plugins
```

```bash
cp -R claude-ui/skills/ui-text claude-ui/skills/ui-layout ~/.config/opencode/skills/ && cp claude-ui/opencode/ui-standards.js ~/.config/opencode/plugins/
```

Then add the rules below to `~/.config/opencode/AGENTS.md`. opencode has no hook for the end of a turn, so flags appear only in each edit's result. The plugin looks for the checker in `~/.config/opencode/skills`, `~/.claude/skills` and `~/.agents/skills`. Set `UI_STANDARDS_BIN` to the checker's path if you put it somewhere else.

### The rules

The session hook adds these rules in Claude Code and Codex. Without hooks, or in opencode, add them to `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` or `~/.config/opencode/AGENTS.md`:

```markdown
## UI text

Text on a screen is not prose. Name the thing or the action in a few words, show state as state, and keep explanations of how the system works off the screen. Before writing or changing any text a product's user sees, load the ui-text skill.

## UI layout

A screen has one job and one primary action. Put what users need first, group with space before boxes, don't nest cards, and keep internals in a developer view. Before building or rearranging a screen, load the ui-layout skill.
```

### Upgrading from 1.x

Version 1 was a plugin named `ui-text` in a repo named `claude-ui-text`. GitHub redirects the old URL, but the plugin and marketplace names changed, so remove the old plugin first:

```
/plugin uninstall ui-text@claude-ui-text
/plugin marketplace remove claude-ui-text
```

Then install as above. For a manual install, copy both skill folders again. Hooks that still call `bin/ui-text` keep working, because that file now runs `ui-standards`.

## Commands

```
ui-standards check PATH... [--ignore-rule RULE] [--only GLOB] [--json]
ui-standards render FILE|URL [--out DIR] [--wait MS] [--session ID]
ui-standards flags
ui-standards waive ID [ID...] --reason TEXT
ui-standards selftest
```

`check` reads whole files or folders, text and layout together, and exits with 1 when it finds problems, so it also works in CI. Advice doesn't change the exit code.

```bash
python3 skills/ui-text/bin/ui-standards check src/
```

There are no inline ignore comments and no ignored folders. To skip a rule for one run, pass `--ignore-rule`.

Flags and waivers last for one session. The checker keeps them in `~/.cache/ui-standards`, outside your repos. Render screenshots go to `.ui-standards/render` in the folder you run it from, so the agent can open them; that folder has its own `.gitignore`, so git skips it. Set `UI_STANDARDS_STATE` to keep them somewhere else. The checker makes no network calls. A render opens only the page you give it, plus whatever that page loads itself.

## Updating

For the plugin, run `/plugin marketplace update claude-ui` in Claude Code. For a manual install, run `git pull` in your clone and copy the files again.

## Tests

```bash
python3 skills/ui-text/bin/ui-standards selftest
```

```bash
python3 skills/ui-text/tests/test_hooks.py
```

```bash
python3 skills/ui-text/tests/test_render.py
```

The first runs the checker on good and bad samples in each file type. The second sends Claude Code, Codex and opencode hook payloads to the checker. The third renders pages in headless Chrome, and skips when there is no Chrome.

## Sources

The text standard draws on the GOV.UK Service Manual (writing for user interfaces), the Microsoft Win32 UI text guide and Writing Style Guide, Apple's Human Interface Guidelines (Writing, Buttons, Alerts), Material 3 content design, and the content guidelines from Shopify, Atlassian and Mailchimp.

The layout standard draws on Nielsen Norman Group research on visual hierarchy, scanning patterns, proximity, common region, cards, progressive disclosure, empty states, dashboards and form design; the GOV.UK Design System; Apple's Human Interface Guidelines (Layout, Buttons); Material 3 layout and cards; Microsoft Fluent 2; IBM Carbon; Shopify Polaris; Atlassian Design; GitHub Primer; Refactoring UI; and Stephen Few on dashboard design. Several landing-page checks follow rules in [impeccable](https://github.com/pbakaus/impeccable) and [design-slop-cop](https://github.com/AdrianKrebs/design-slop-cop).

Both use WCAG 2.2 and ISO 9241-110, 9241-112 and 9241-125. Where sources disagree, the skills pick one default and state it, so the agent doesn't have to choose.

## License

MIT
