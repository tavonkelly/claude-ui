---
name: ui-text
description: Standard for text that users of a product see, in any project. Covers labels, buttons, headings, field hints, errors, empty, loading and success states, confirmations, notifications, CLI prompts and errors, and API errors that reach users. Load it before writing or changing UI text. Docs, READMEs, explainer pages and chat replies are prose and don't use it.
---

# UI text

People scan screens. They read control labels first, read other text only when they think they need it, and stop reading once they know what to do. So a screen names things and actions. It doesn't explain itself. If a screen needs an explanation of how it works, fix the screen.

## Where it applies

Applies to anything a user of the product sees: web and app screens, tool and dashboard pages, CLI prompts and errors, notifications, emails the product sends, and API error messages that reach users.

Doesn't apply to docs, READMEs, explainer pages, articles or chat replies. Those are prose. A help panel or help page inside an app is prose too. Prose style rules, such as plain-language standards or edits that add voice, never apply to UI text.

A project's own content guide, design system wording or term list wins over this skill. This skill fills the gaps.

## Procedure

1. Before writing code for a screen, list every string it will show, each with its element type and limit.
2. For each string, ask whether the user needs it to act right now. If not, cut it. If they need it only sometimes, it goes in help or a tooltip.
3. Check the list against the rules below. Then write the code.
4. Fix whatever the checker flags.

| Element | Limit |
|---|---|
| Button, menu item, tab | 1 to 4 words. Verb first for actions |
| Field label, column header, heading, legend | 1 to 4 words. A noun phrase |
| Heading or label phrased as a question | Up to 8 words: "Where do you live?" |
| Field hint | One short line, only when the format isn't obvious |
| Error, toast, banner, empty state | 12 words or fewer. One idea |
| Supporting text under a heading | Usually none |

## Rules

### Name things and actions

- Buttons say what happens, as a verb plus an object: "Delete file", "Place order", "Send invite". Never "OK", "Submit", "Yes" or "No" as an action.
- When the object is obvious from context, the verb alone is fine: "Save", "Cancel".
- Labels name the field. They don't instruct: "Email:", not "Enter your email". Never start a label with Enter, Type, Select or Choose.
- Headings name the topic: "Notifications", not "Here you can manage notifications".
- Put the words that matter first.
- One name per thing, everywhere. Don't switch between "project", "workspace" and "space" for the same object.
- Use the words users use, not the system's: "Notifications", not "Webhook config".
- Word a list of options the same way, and move shared words into the group label.
- Every icon-only control gets a visible text label. A tooltip alone isn't enough.
- Show state as state: a chip, a count, a timestamp, a progress bar. "Running, 3 min left", not "The build is currently running and should finish soon".

### Keep off the screen

- How the system works, why it was built, what happens behind the scenes.
- Restating what the layout already shows: "Below is a list of your files".
- Filler: "simply", "just", "in order to", "please", "please note".
- Welcome and thank-you lines. "Thank you for your order" becomes "Order placed".
- Sections called "How it works" or "Under the hood". Diagnostics belong in a developer view, not the product UI.

### Mechanics

- Sentence case everywhere: "Create project", not "Create Project". Proper nouns keep their capitals.
- A colon after a field or group label that sits outside its control: "Email:". No colon on headings, buttons, checkbox labels or tabs.
- A fragment standing alone gets no period: "Changes saved". A full sentence gets one. When a message has two parts, each ends with a period: "Couldn't save changes. Check your connection."
- System errors have no subject: "Couldn't save changes", not "You entered an invalid date" or "We couldn't save". Never make "you" the cause. Use "we" only when real people will act: "We'll email you within 2 days".
- Contractions are fine ("can't", "don't"), except in warnings and destructive confirmations. There, write "do not" and "cannot" so a missed "not" can't flip the meaning.
- Mark optional fields with "(optional)" after the label: "Phone (optional):". No asterisks.
- Tone is neutral. Light warmth only in rare success messages and empty states. No humor and no "Oops" in errors, warnings or messages people see often.

### Defaults where the guides differ

- No placeholder text in fields. Format help goes in a hint that stays visible. A search field may use a placeholder if it has a label for screen readers.
- No ellipsis on buttons that open a dialog. Use "…" for progress ("Saving…") and truncated text. Native desktop menus follow their platform.
- "Close" dismisses a view with nothing to commit. "Cancel" discards. "OK" only acknowledges a message. "Done" only finishes a multi-step flow.
- "Continue", not "Next".
- Drop the pronoun when you can: "Account", "Files". Use "your" if you need one. "I" and "my" only in consent checkboxes: "I agree to the terms".
- "Sorry" only for data loss or an outage the product caused. "Thanks" only after the user did the product a favor, such as sending feedback.
- "Select", not "click" or "tap", except in help written for one platform.
- Numerals: "3 files", "1 error". Don't start a sentence with a numeral.
- No exclamation points. One is allowed for a rare milestone, never in an error.
- "and", not "&".
- "Sign in" and "Sign out", not "Log in".
- When text names a control, use its exact label with no quotes, in bold where formatting exists: Select **Export**.
- Dates and times come from the locale formatter (`Intl.DateTimeFormat`, `DateFormatter`, `DateFormat`), never a hand-written format. Recent events can use relative time: "2 min ago".
- No em dashes. Split the sentence.

## Screen states

- **Empty.** Say what's missing and give the action that fills it: "No messages yet" with a **New message** button. Don't explain what messages are.
- **Loading.** Name what's loading: "Loading calendar…". For waits over a few seconds, show progress or the current step. Never "Please wait while we…".
- **Field error.** State the fix, next to the field: "Use at least 8 characters", "Date must be in the past".
- **System error.** Say what failed and give the next step, as a button where possible: "Couldn't save changes" with **Try again**. Name the cause when it's known: "File is over 25 MB".
- **Success.** Object first, past tense: "Invite sent", "Changes saved". Toasts disappear, so never put the only copy of important information in one.
- **Confirmation.** Ask the specific question and label both choices by their action: "Delete 3 events?" with **Delete events** and **Cancel**. State the consequence only if it isn't obvious: "This cannot be undone." Never "Are you sure?".
- **Disabled control.** Show what's missing next to it ("Select a file"), not a paragraph about why it's disabled.

## Text accessibility (WCAG 2.2 AA)

- Every control has a programmatic label: `<label for>`, `aria-label`, `accessibilityLabel`, `semanticsLabel`. (1.3.1, 4.1.2)
- The accessible name contains the visible label and starts with it. (2.5.3)
- Link text makes sense alone: "Privacy policy", not "Click here" or "Read more". Repeated "Change" links get hidden text that names what they change. (2.4.4)
- Headings and labels describe their topic or purpose. (2.4.6)
- Never point to things by color, shape or position alone, like "the green button" or "the menu on the left". (1.3.3, 1.4.1)
- Alt text on a functional image says what it does ("Search"). Decorative images get empty alt.
- Errors are tied to their field (`aria-describedby`) and announced. (3.3.1)

## CLI and API text

- An error says what failed, where, and the fix: `config.yaml line 12: expected a value`. Then the command that fixes it, if there is one: `Run: app init`.
- No banners, taglines or paragraphs on startup. Progress is state: `Uploading 3/12`.
- A prompt ends with the expected input: `Overwrite build/? [y/N]`.
- API error messages a user may see follow the error rules. Codes and details go in other fields.

## Before and after

| Domain | Before | After |
|---|---|---|
| Settings | Heading "Here you can manage how and when you receive notifications" | "Notifications" |
| Settings | "Your Account Settings" | "Account" |
| Settings | Options "Send me an email when someone comments", "Send me an email when someone mentions me" | Group label "Email me when someone:", options "Comments", "Mentions me" |
| Settings | Toast "Your changes have been saved successfully!" | "Changes saved" |
| Checkout | Button "Submit" | "Place order" |
| Checkout | "Phone number *" with a "* required" legend | "Phone (optional):", required fields unmarked |
| Checkout | "Thank you for your order!" | "Order placed" |
| Checkout | Field error "Invalid card number" | "Card number must be 16 digits" |
| Sign-in | Label "Please enter your email address" | "Email:" |
| Sign-in | "Log In" | "Sign in" |
| Sign-in | "Oops! You entered the wrong password." | "Wrong password. Try again or reset it." |
| Files | "Are you sure?" with Yes and No | "Delete 3 files?" with **Delete files** and **Cancel** |
| Files | "It looks like this folder is empty. Files you upload will appear here." | "No files" with **Upload files** |
| Files | "We couldn't find anything matching your search. Try using different keywords." | `No results for "budget"` with **Clear search** |
| Email | Icon-only trash button | Trash icon with "Delete" |
| Email | "Click here to see older messages" | "Older messages" |
| Calendar | "Please wait while we load your calendar..." | "Loading calendar…" |
| Calendar | "This event repeats every week on Monday" | "Weekly on Monday" |
| Dev tool | "The build is currently running and should be finished in about 3 minutes." | Chip "Running" and "3 min left" |
| Dev tool | Paragraph under the title: "This dashboard shows how tickets move through each stage so that you can spot bottlenecks early." | No paragraph. Title "Tickets by stage" |
| Dev tool | `Error: something went wrong` | `config.yaml line 12: expected a value` |
| Any app | A "How it works" section that explains the pipeline | Removed. A **Help** link if users need it |

## Checker

`bin/ui-standards` in this skill's folder is a Python 3 script with no dependencies. It reads HTML, JSX/TSX, Svelte, Vue, Dart and Swift. It also runs the layout rules from the ui-layout skill. Its text rules flag:

| Rule | Flags |
|---|---|
| `long-label` | A button, label, heading, tab or menu item over 4 words, or a question heading over 8 |
| `long-text` | Any other string over 12 words |
| `multi-sentence` | A string with two or more sentences of 5+ words each |
| `phrase` | "you can", "lets you", "allows you", "this page", "this screen", "so that", "how it works", "under the hood", "please", "sorry", "thank you", "thanks for", "click here", "simply", "oops" |
| `generic-button` | A button labeled OK, Submit, Yes or No |
| `instruction-label` | A label or heading that starts with Enter, Type, Select, Choose or Pick |

When hooks are installed (Claude Code and Codex) or the plugin is (opencode):

- **Before the first UI edit in a session**, the edit is refused until this skill and the ui-layout skill are loaded. Load them and send the edit again.
- **After each edit of a UI file**, it checks only the strings you added or changed and reports each flag with an id.
- **At the end of the turn** (Claude Code and Codex), open flags block the stop once. Fix them, or waive the ones that are prose on purpose. If any stay open, list them for the user in your closing message.

Commands, run from this skill's folder or by the full path the hook messages show:

- `bin/ui-standards check PATH... [--ignore-rule RULE] [--only GLOB]` checks whole files or folders.
- `bin/ui-standards flags` lists open flags in the current session.
- `bin/ui-standards waive ID [ID...] --reason "help panel"` waives flags for this session. Waivers are kept outside the repo. List every waiver in your closing message.
- `bin/ui-standards render FILE|URL` renders a page and checks its layout. See the ui-layout skill.
- `bin/ui-standards selftest` runs the cases in `tests/`.

Patterns can't judge meaning, so short narration gets past the checker. The rules above still apply to it.

Without hooks, run `bin/ui-standards check` on the files you changed before you finish.

## Sources

GOV.UK Service Manual, writing for user interfaces. Microsoft Win32 UI text guide and Writing Style Guide. Apple HIG: Writing, Buttons, Alerts. Material 3 content design. Shopify content guidelines. Atlassian content guidelines. Mailchimp content style guide. NN/g: how users read on the web, icon usability, 10 usability heuristics. WCAG 2.2. ISO 9241-110 and ISO 9241-112.
