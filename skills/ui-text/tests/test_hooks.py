#!/usr/bin/env python3
"""Sends Claude Code, Codex and opencode hook payloads to the checker and checks the replies."""
import json
import os
import subprocess
import sys
import tempfile

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "bin", "ui-text")
TMP = tempfile.mkdtemp(prefix="ui-text-test-")
ENV = dict(os.environ, UI_TEXT_STATE=os.path.join(TMP, "state"))
BAD_OLD = "<p>This page lets you see every report that was made by your team last month.</p>"
BAD_NEW = "<p>Here you can simply manage how and when the reports get sent to you.</p>"
failures = []


def hook(event, payload):
    r = subprocess.run([sys.executable, BIN, "hook", event], input=json.dumps(payload),
                       capture_output=True, text=True, env=ENV, timeout=20)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else {}


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else ": " + str(detail)))
    if not cond:
        failures.append(name)


def write(path, text):
    with open(path, "w") as fh:
        fh.write(text)


def context(out):
    return (out.get("hookSpecificOutput") or {}).get("additionalContext", "")


def denied(out):
    return (out.get("hookSpecificOutput") or {}).get("permissionDecision") == "deny"


def loaded_transcript(line):
    p = os.path.join(TMP, "transcript-%d.jsonl" % abs(hash(line)))
    write(p, line + "\n")
    return p


page = os.path.join(TMP, "page.html")
base = "<h1>Reports</h1>\n" + BAD_OLD + "\n<button>Save</button>\n"

# Session rule
out = hook("session", {"session_id": "s0", "hook_event_name": "SessionStart"})
check("session hook adds the rule", "load the ui-text skill" in context(out), out)

# Claude Code: gate, then only changed strings
write(page, base)
edit = {"session_id": "claude", "tool_name": "Edit", "cwd": TMP, "tool_use_id": "t1",
        "transcript_path": loaded_transcript('{"type":"user"}'),
        "tool_input": {"file_path": page, "old_string": "<button>Save</button>", "new_string": BAD_NEW + "\n<button>Save</button>"}}
check("gate refuses first UI edit without the skill", denied(hook("pre", edit)))
check("gate runs once per session", not denied(hook("pre", edit)))
write(page, base.replace("<button>Save</button>", BAD_NEW + "\n<button>Save</button>"))
ctx = context(hook("post", edit))
check("Claude Edit flags the new string", "Here you can simply" in ctx, ctx)
check("Claude Edit skips strings that were already there", "This page lets you" not in ctx, ctx)

for name, line in [("Skill tool", '{"input":{"skill":"ui-text"}}'),
                   ("plugin skill", '{"input":{"skill":"ui-text:ui-text"}}'),
                   ("skill read", '"Base directory for this skill: /x/plugins/cache/claude-ui-text/ui-text/1.0.0/skills/ui-text"')]:
    p = {"session_id": "loaded-" + name, "tool_name": "Write", "cwd": TMP, "transcript_path": loaded_transcript(line),
         "tool_input": {"file_path": page, "content": base}}
    check("gate passes after %s" % name, not denied(hook("pre", p)))

write(page, base)
noprev = dict(edit, session_id="claude-nopre", tool_use_id="t9")
write(page, base.replace("<button>Save</button>", BAD_NEW + "\n<button>Save</button>"))
ctx = context(hook("post", noprev))
check("Claude Edit without a snapshot rebuilds the old file", "Here you can simply" in ctx and "This page lets you" not in ctx, ctx)

new_page = os.path.join(TMP, "new.html")
wr = {"session_id": "claude-write", "tool_name": "Write", "cwd": TMP, "skill_loaded": True,
      "tool_input": {"file_path": new_page, "content": base}}
hook("pre", wr)
write(new_page, base)
check("Claude Write of a new file flags its strings", "This page lets you" in context(hook("post", wr)))

# Stop: blocks once, then lets the turn end
stop = {"session_id": "claude", "cwd": TMP, "stop_hook_active": False}
out = hook("stop", stop)
check("stop blocks while a flag is open", out.get("decision") == "block", out)
out = hook("stop", dict(stop, stop_hook_active=True))
check("stop does not block twice", out.get("decision") != "block", out)

# Waiver
write(page, base)
wv = dict(edit, session_id="claude-waive", tool_use_id="w1", skill_loaded=True)
hook("pre", wv)
write(page, base.replace("<button>Save</button>", BAD_NEW + "\n<button>Save</button>"))
ctx = context(hook("post", wv))
ids = [l.split()[0] for l in ctx.split("\n") if l[:1] == "U"]
r = subprocess.run([sys.executable, BIN, "waive"] + ids + ["--reason", "test"], capture_output=True, text=True, env=ENV)
check("waive accepts the flag id", r.returncode == 0, r.stderr)
out = hook("stop", {"session_id": "claude-waive", "cwd": TMP})
check("stop lets waived flags through", out.get("decision") != "block", out)

# Codex: apply_patch text, in each shape the payload may take
patch = ("*** Begin Patch\n*** Update File: page.html\n@@\n <h1>Reports</h1>\n " + BAD_OLD +
         "\n+" + BAD_NEW + "\n <button>Save</button>\n*** End Patch")
for i, (tool, ti) in enumerate([("apply_patch", {"command": patch}),
                                 ("apply_patch", {"patch": patch}),
                                 ("apply_patch", {"input": patch}),
                                 ("shell", {"command": ["apply_patch", patch]}),
                                 ("Bash", {"command": "apply_patch <<'EOF'\n" + patch + "\nEOF"})]):
    for with_pre in (True, False):
        write(page, base)
        p = {"session_id": "codex-%d-%s" % (i, with_pre), "tool_name": tool, "tool_use_id": "c%d" % i,
             "cwd": TMP, "transcript_path": None, "skill_loaded": True, "tool_input": ti}
        if with_pre:
            hook("pre", p)
        write(page, base.replace("<button>Save</button>", BAD_NEW + "\n<button>Save</button>"))
        ctx = context(hook("post", p))
        check("Codex %s %s (%s)" % (tool, list(ti)[0], "snapshot" if with_pre else "hunks"),
              "Here you can simply" in ctx and "This page lets you" not in ctx, ctx)

add = "*** Begin Patch\n*** Add File: added.tsx\n+export const A = () => <p>" + BAD_NEW[3:-4] + "</p>;\n*** End Patch"
p = {"session_id": "codex-add", "tool_name": "apply_patch", "cwd": TMP, "skill_loaded": True, "tool_input": {"command": add}}
hook("pre", p)
write(os.path.join(TMP, "added.tsx"), "export const A = () => <p>" + BAD_NEW[3:-4] + "</p>;\n")
check("Codex Add File flags its strings", "Here you can simply" in context(hook("post", p)))
p = {"session_id": "codex-gate", "tool_name": "apply_patch", "cwd": TMP, "transcript_path": None, "tool_input": {"command": patch}}
check("Codex gate refuses the first UI patch", denied(hook("pre", p)))
p = {"session_id": "codex-bash", "tool_name": "Bash", "cwd": TMP, "tool_input": {"command": "ls -la"}}
check("Codex ignores other shell commands", hook("pre", p) == {} and hook("post", p) == {})

# opencode: the plugin sends its tool name and args
write(page, base)
oc = {"session_id": "opencode-1", "tool_name": "edit", "tool_use_id": "o1", "cwd": TMP, "skill_loaded": True,
      "tool_input": {"filePath": page, "oldString": "<button>Save</button>", "newString": BAD_NEW + "\n<button>Save</button>"}}
check("opencode edit passes the gate when the skill is loaded", not denied(hook("pre", oc)))
write(page, base.replace("<button>Save</button>", BAD_NEW + "\n<button>Save</button>"))
ctx = context(hook("post", oc))
check("opencode edit flags the new string only", "Here you can simply" in ctx and "This page lets you" not in ctx, ctx)

# Files that aren't UI
py = os.path.join(TMP, "x.py")
write(py, "msg = 'Here you can simply manage how and when the reports get sent to you.'\n")
p = {"session_id": "claude", "tool_name": "Write", "cwd": TMP, "tool_input": {"file_path": py, "content": ""}}
check("non-UI files are ignored", hook("pre", p) == {} and hook("post", p) == {})

print("hook tests %s" % ("passed" if not failures else "FAILED: %d" % len(failures)))
sys.exit(1 if failures else 0)
