---
name: ui-layout
description: Standard for how screens are laid out, in any project. Covers what goes on a screen, order and grouping, primary actions, cards, spacing, type sizes, responsive layout, and patterns for forms, settings, lists, dashboards, empty states, tool pages and landing pages. Load it before building a screen or changing a screen's structure. The ui-text skill covers the words.
---

# UI layout

A screen has one job. People scan it for the thing they came to do, and every extra box, tile and button competes with that thing. So decide what the screen is for before writing markup, show only what serves that job, and put it where the eye lands first. If a layout needs explaining, fix the layout.

## Where it applies

Every screen someone uses outside of development: public pages, client portals, app screens, admin and internal tools, and personal tools. Hidden developer and diagnostic views are the only exception. Waive their flags with the reason "developer view".

A project's own design system, grid or component library wins over this skill. This skill fills the gaps.

## Plan first

Before writing markup for a new screen, write a short plan in your reply:

- **Job:** what the user comes here to do, in one line.
- **Primary action:** the one action that does that job.
- **Sections:** in order of use, most needed first.
- **Cut:** what you left out, and where it went instead: a help link, a details view, a developer view, or nowhere.

Edits that keep an existing screen's structure don't need a plan.

## What goes on the screen

- Show what users need for the job. Move what they rarely need behind one clearly labeled control, such as a disclosure, a tab or a details page, at most 2 levels deep. Cut the rest.
- No stat tiles or big numbers unless the screen's job is monitoring. On a monitoring screen, every number gets context, such as a target, a prior period or a trend, and no tile repeats a table on the same screen.
- Show each fact once. Don't repeat the page title in a card title, a count in both a tile and a table, or a command in two places.
- System internals go in a developer view: a separate route or a hidden toggle. That covers logs, timings, pipeline or model status and "written by" stamps. Never give them a pane on the user's screen.
- No decoration standing in for hierarchy: gradients, glows, fake browser chrome, decorative badges or emoji icons.

## Order and grouping

- Put the main task at the top and on the leading side. Supporting content goes below it or in a side pane.
- Order sections by how often and how soon users need them, never by the order you built them.
- Lead with the answer or the current state. Details come after.
- Group with space first. Related items sit close together, and the gap between groups is at least one step larger on the spacing scale than the gaps inside them.
- A heading sits closer to its own content than to the content above it.
- Put each control next to what it changes. A filter sits above the list it filters, a row's actions sit in the row, and Save sits at the end of the form it saves.
- Keep the DOM order the same as the visual order, so keyboard and screen reader order make sense (WCAG 1.3.2, 2.4.3).
- Keep repeated navigation in the same place and order on every page (WCAG 3.2.3).

## Cards and containers

- No cards by default. Separate sections with space and a heading, and a divider at most.
- Use cards only for a collection of mixed items people browse, or when the project's design system is card-based.
- Never put a card inside a card.
- Never put a card around a single control or a single line.
- Show items of one kind as a list or a table, not a grid of cards. Lists are faster to scan, compare and sort.
- A box with a border, a shadow, or a fill with rounded corners counts as a card. So does anything named card, panel, tile or box.

## Primary actions

- One primary action per view, plus one in each dialog or side panel.
- Make it the only filled button in its view. Secondary actions are outlined or plain buttons, and tertiary actions are links. Keep at most 3 secondary actions in view and put the rest in an overflow menu.
- On a page, align the primary action with the content's left edge, such as under the last field of a form. In a dialog, put it at the trailing edge with Cancel before it. A project's design system wins on placement.
- A destructive action is never a page's primary action. In a confirmation dialog, the destructive button may be the filled one.
- Never style row actions in a table or list as primary.

## Visual weight

- One focal point per screen: the content or action the screen is for. At most 2 large elements.
- At most 4 font sizes and 2 weights per screen. Build hierarchy with size, weight and color contrast, not with boxes.
- Blur the screenshot or squint at it. The element the screen is for should still stand out first.

## Spacing, alignment and size

- Take every margin, padding and gap from one scale: 4, 8, 12, 16, 24, 32, 48 or 64px. If the project defines its own spacing tokens, use those. 0, 1 and 2px are fine for hairlines.
- Align content to one left edge. Center only short empty states and dialogs.
- Keep running text near 70 characters wide (`max-width: 70ch`).
- Forms use one column, labels above fields, and fields as wide as their expected input.
- Click targets are at least 24 by 24px (WCAG 2.5.8), and 44px on touch screens.
- Use one density per page.

## Screen patterns

- **Form.** One column. For a long flow, one topic per page. The submit button names its action and sits under the last field on the left, with a weaker Cancel. No Reset button.
- **Settings.** Sections with a heading, separated by space or a divider. On wide screens, put the section heading in a narrow left column and its controls in a wider right column; stack them on narrow screens. Save at the end, or save each control as it changes.
- **List and detail.** A list or table of items, where selecting one opens its detail. Show two panes from about 840px wide, and separate pages below that.
- **Dashboard.** Only when the job is monitoring. It fits one screen, with the key metric at the top left and context for every number. Prefer bars and lines to gauges, pies and 3D.
- **Empty state.** Replaces the region it fills, with no table headers. Says what's missing and offers one action.
- **Tool page.** Inputs on the leading side or the top, the result on the other side, both visible at once. On narrow screens, the result goes below the inputs.
- **Landing page.** One message and one primary call to action. No pill badge above the headline, no uppercase labels above every heading, no grid of identical icon, heading and text cards, no row of stats, no gradient text, and the same call-to-action band at most once.

## Responsive

- Lay out for 320px wide first. Nothing scrolls sideways at 320px (WCAG 1.4.10). Wide tables and code get their own scroll box.
- Use one pane below 600px wide.
- Every function stays available at every width.
- Recheck grouping after things stack. A label must still sit next to its field.

## Render to check

`ui-standards render FILE|URL` opens the page in headless Chrome. It saves screenshots at 1280 and 375px wide and checks the layout at 320px. For an app that needs a dev server, pass its URL.

Render when:

- You built a new screen or changed a screen's structure. Render before calling the work done.
- Many pages share a template. Render one page of each kind, not every page.

Skip it for text-only edits, small style tweaks, and work where the user's goal doesn't involve how the screen looks.

After a render, look at both screenshots. Does the eye land on the screen's job first? Is there one primary action? Does anything look boxed, crowded or repeated?

## Checker

ui-layout uses the checker in the ui-text skill's folder, `../ui-text/bin/ui-standards` from this skill's folder. It checks HTML, Vue, Svelte, JSX/TSX, CSS, Dart and Swift. Blocking rules stop the end of the turn once, like ui-text flags. Advice appears after the edit and never blocks.

| Rule | Tier | Flags |
|---|---|---|
| `nested-card` | Blocks | A card inside a card |
| `single-control-card` | Blocks | A card around a single control or a single line |
| `multiple-primary` | Blocks in HTML, advice in components | More than one primary-styled action in a view |
| `off-scale-spacing` | Blocks | A margin, padding or gap off the spacing scale |
| `heading-skip` | Blocks | A skipped heading level, or more than one h1 in a view |
| `overflow-x` | Blocks (render) | The page scrolls sideways at 320px |
| `text-overlap` | Blocks (render) | Text overlapping other text |
| `hidden-visible` | Blocks (render) | An element marked hidden that still shows |
| `stat-tiles` | Advice | A row of stat tiles or big numbers |
| `card-grid` | Advice | 3 or more identical cards with an icon, heading and text |
| `type-scale` | Advice | More than 4 font sizes or 2 font weights |
| `deep-nesting` | Advice | Elements nested more than 8 levels deep |
| `badge-above-h1`, `eyebrow`, `emoji-icon`, `gradient-text`, `accent-stripe`, `repeated-cta` | Advice | Landing-page habits |
| `small-target` | Advice (render) | A click target under 24px with no clear space around it |
| `long-lines` | Advice (render) | Text lines over 80 characters |

Static checks see only the markup in the file. A component file isn't a whole view, so its primary-action and h1 counts are advice. Markup built at runtime is invisible to them; a render sees it.

Commands:

- `ui-standards render FILE|URL [--out DIR] [--wait MS]` renders and checks a page. Screenshots go to `.ui-standards/render` in the current folder, which git ignores, unless you pass `--out`. It needs Chrome or Chromium; without one it says so and skips.
- `ui-standards check PATH...` checks whole files or folders for text and layout.
- `ui-standards flags` and `ui-standards waive ID [ID...] --reason "..."` work as in ui-text. List every waiver in your closing message.

A layout can pass every check and still bury the main task. The rules above still apply.

## Sources

NN/g: visual hierarchy, F-shaped and layer-cake scanning, proximity, common region, cards, progressive disclosure, empty states, dashboards, web form design, aesthetic and minimalist design. GOV.UK Design System and Service Manual: layout, question pages, form structure, buttons. Apple HIG: layout, buttons. Material 3: layout, breakpoints, canonical layouts, cards. Microsoft Fluent 2: layout, buttons. IBM Carbon: 2x grid, spacing, buttons, empty states. Shopify Polaris and App Design Guidelines: page layout, actions. Atlassian Design: spacing, buttons. GitHub Primer: layout, buttons. Refactoring UI. Stephen Few, Common Pitfalls in Dashboard Design. Edward Tufte on data-ink. WCAG 2.2. ISO 9241-110, 9241-112 and 9241-125. Rule ideas for landing-page habits from impeccable (github.com/pbakaus/impeccable), design-slop-cop (github.com/AdrianKrebs/design-slop-cop) and OpenAI's frontend design guidance.
