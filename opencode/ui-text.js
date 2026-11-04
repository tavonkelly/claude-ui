// ui-text plugin for opencode. Runs the ui-text checker around file edits:
// refuses the first UI edit in a session until the skill is loaded, and adds
// flags for changed UI strings to the edit's result.
//
// Install: copy this file to ~/.config/opencode/plugins/ and the skill folder
// to ~/.config/opencode/skills/ui-text. Set UI_TEXT_BIN to use a checker
// somewhere else.
import { spawnSync } from "node:child_process"
import { existsSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

const CANDIDATES = [
  process.env.UI_TEXT_BIN,
  join(homedir(), ".config/opencode/skills/ui-text/bin/ui-text"),
  join(homedir(), ".claude/skills/ui-text/bin/ui-text"),
  join(homedir(), ".agents/skills/ui-text/bin/ui-text"),
].filter(Boolean)

const EDIT_TOOLS = new Set(["edit", "write", "multiedit", "patch", "apply_patch"])

function runHook(bin, event, payload) {
  const r = spawnSync("python3", [bin, "hook", event], {
    input: JSON.stringify(payload),
    encoding: "utf8",
    timeout: 10000,
  })
  try {
    return JSON.parse(r.stdout || "{}")
  } catch {
    return {}
  }
}

export const UiText = async ({ directory }) => {
  const bin = CANDIDATES.find((p) => existsSync(p))
  if (!bin) return {}
  const loaded = new Set()
  const payload = (input, args) => ({
    session_id: `opencode-${input.sessionID}`,
    tool_name: input.tool,
    tool_use_id: input.callID,
    tool_input: args ?? {},
    cwd: directory,
    skill_loaded: loaded.has(input.sessionID),
  })

  return {
    "tool.execute.before": async (input, output) => {
      const args = output.args ?? {}
      if (input.tool === "skill" && String(args.name ?? "").endsWith("ui-text")) loaded.add(input.sessionID)
      if (input.tool === "read" && String(args.filePath ?? "").endsWith("ui-text/SKILL.md")) loaded.add(input.sessionID)
      if (!EDIT_TOOLS.has(input.tool)) return
      const out = runHook(bin, "pre", payload(input, args)).hookSpecificOutput
      if (out?.permissionDecision === "deny") throw new Error(out.permissionDecisionReason)
    },
    "tool.execute.after": async (input, output) => {
      if (!EDIT_TOOLS.has(input.tool)) return
      const ctx = runHook(bin, "post", payload(input, input.args)).hookSpecificOutput?.additionalContext
      if (ctx) output.output = `${output.output ?? ""}\n\n${ctx}`
    },
  }
}
