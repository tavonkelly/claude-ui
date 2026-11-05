#!/usr/bin/env python3
"""Renders pages in headless Chrome through the checker. Skips when no Chrome or Chromium is installed."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin", "ui-standards")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "bin"))
import ui_render  # noqa: E402

if not ui_render.find_chrome():
    print("render tests skipped: no Chrome or Chromium")
    sys.exit(0)

TMP = tempfile.mkdtemp(prefix="ui-standards-render-")
ENV = dict(os.environ, UI_STANDARDS_STATE=os.path.join(TMP, "state"))
ENV.pop("CLAUDE_CODE_SESSION_ID", None)
failures = []

BAD = """<!doctype html><html><head><meta name="viewport" content="width=device-width">
<style>
  body { margin: 0; font: 16px/1.5 sans-serif; }
  main { padding: 16px; }
  .wide { width: 600px; }
  .banner { display: flex; padding: 8px; }
  .card { border: 1px solid #ccc; border-radius: 8px; padding: 16px; }
  .fill { background: #2f5bd3; color: #fff; border: 0; padding: 8px 16px; }
</style></head><body><main>
  <h1>Reports</h1>
  <div class="banner" hidden>Couldn't save changes</div>
  <div class="wide">Monthly summary for every team</div>
  <div class="card"><h2>Owner</h2><p>Maya Chen</p><div class="card"><p>Invoices</p><p>3 this year</p></div></div>
  <button class="fill">Save</button> <button class="fill">Export</button>
</main></body></html>"""
GOOD = BAD.replace(".wide { width: 600px; }", ".wide { max-width: 600px; }").replace(
    ".banner { display: flex; padding: 8px; }", "[hidden] { display: none !important; } .banner { display: flex; padding: 8px; }").replace(
    '<div class="card"><p>Invoices</p><p>3 this year</p></div>', "<p>Invoices: 3 this year</p>").replace(
    '<button class="fill">Export</button>', "<button>Export</button>")


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else ": " + str(detail)))
    if not cond:
        failures.append(name)


def run(*args):
    return subprocess.run([sys.executable, BIN] + list(args), capture_output=True, text=True, env=ENV, timeout=120)


page = os.path.join(TMP, "page.html")
with open(page, "w") as fh:
    fh.write(BAD)
r = run("render", page, "--session", "render-1", "--out", os.path.join(TMP, "shots"))
out = r.stdout
check("render exits 1 on problems", r.returncode == 1, r.stdout + r.stderr)
for rule in ("overflow-x", "hidden-visible", "nested-card", "multiple-primary"):
    check("render finds %s" % rule, "[%s]" % rule in out, out)
check("render saves two screenshots", out.count(".png") == 2 and all(os.path.isfile(l.strip()) for l in out.splitlines() if l.strip().endswith(".png")), out)

stop = subprocess.run([sys.executable, BIN, "hook", "stop"], input=json.dumps({"session_id": "render-1", "cwd": TMP}),
                      capture_output=True, text=True, env=ENV)
check("stop blocks on open render problems", '"block"' in stop.stdout, stop.stdout)

with open(page, "w") as fh:
    fh.write(GOOD)
r = run("render", page, "--session", "render-1", "--out", os.path.join(TMP, "shots"))
check("render of the fixed page exits 0", r.returncode == 0, r.stdout + r.stderr)
stop = subprocess.run([sys.executable, BIN, "hook", "stop"], input=json.dumps({"session_id": "render-1", "cwd": TMP}),
                      capture_output=True, text=True, env=ENV)
check("stop passes after the fixed render", '"block"' not in stop.stdout, stop.stdout)

r = subprocess.run([sys.executable, BIN, "render", page, "--session", "render-2"], capture_output=True, text=True, env=ENV, timeout=120, cwd=TMP)
gi = os.path.join(TMP, ".ui-standards", ".gitignore")
check("render saves to .ui-standards/render by default, ignored by git",
      os.path.isfile(gi) and open(gi).read().strip() == "*" and os.listdir(os.path.join(TMP, ".ui-standards", "render")), r.stdout + r.stderr)

r = run("render", os.path.join(TMP, "missing.html"))
check("render reports a missing file", r.returncode == 2 and "No file" in r.stderr, r.stderr)

print("render tests %s" % ("passed" if not failures else "FAILED: %d" % len(failures)))
sys.exit(1 if failures else 0)
