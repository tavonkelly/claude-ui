// ui-standards plugin for opencode. Runs the ui-standards checker around file
// edits: refuses the first UI edit in a session until the ui-text and ui-layout
// skills are loaded, and adds text and layout flags for each edit to its result.
//
// Install: copy this file to ~/.config/opencode/plugins/ and both skill folders
// to ~/.config/opencode/skills/. Set UI_STANDARDS_BIN to use a checker
// somewhere else.
import { spawnSync } from "node:child_process"
import { existsSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join } from "node:path"

const CANDIDATES = [
  process.env.UI_STANDARDS_BIN,
  process.env.UI_TEXT_BIN,
  join(homedir(), ".config/opencode/skills/ui-text/bin/ui-standards"),
  join(homedir(), ".claude/skills/ui-text/bin/ui-standards"),
  join(homedir(), ".agents/skills/ui-text/bin/ui-standards"),
].filter(Boolean)

const EDIT_TOOLS = new Set(["edit", "write", "multiedit", "patch", "apply_patch"])
const SKILLS = ["ui-text", "ui-layout"]

function runHook(bin, event, payload) {
  const r = spawnSync("python3", [bin, "hook", event], {
    input: JSON.stringify(payload),
    encoding: "utf8",
    timeout: 15000,
  })
  try {
    return JSON.parse(r.stdout || "{}")
  } catch {
    return {}
  }
}

export const UiStandards = async ({ directory }) => {
  const bin = CANDIDATES.find((p) => existsSync(p))
  if (!bin) return {}
  const skillsDir = dirname(dirname(dirname(bin)))
  const needed = SKILLS.filter((s) => existsSync(join(skillsDir, s, "SKILL.md")))
  const loaded = new Map()
  const mark = (session, name) => {
    if (!loaded.has(session)) loaded.set(session, new Set())
    loaded.get(session).add(name)
  }
  const payload = (input, args) => ({
    session_id: `opencode-${input.sessionID}`,
    tool_name: input.tool,
    tool_use_id: input.callID,
    tool_input: args ?? {},
    cwd: directory,
    skill_loaded: needed.every((s) => loaded.get(input.sessionID)?.has(s)),
  })

  return {
    "tool.execute.before": async (input, output) => {
      const args = output.args ?? {}
      for (const s of SKILLS) {
        if (input.tool === "skill" && String(args.name ?? "").endsWith(s)) mark(input.sessionID, s)
        if (input.tool === "read" && String(args.filePath ?? "").endsWith(`${s}/SKILL.md`)) mark(input.sessionID, s)
      }
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
