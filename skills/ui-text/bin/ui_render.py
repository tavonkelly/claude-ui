"""Render a page in headless Chrome and measure its layout.

Talks to Chrome over --remote-debugging-pipe, so it needs no packages. render(target, out_dir) returns
{"shots": [paths], "findings": [...], "error": text or None}.
"""
import base64
import json
import os
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time

CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]
NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "brave-browser", "chrome"]

# Each pass: (width, height, checks, screenshot)
PASSES = [
    (1280, 800, ["hidden", "overlap", "cards", "primary", "targets", "lines"], True),
    (375, 812, ["overlap", "targets"], True),
    (320, 800, ["overflow"], False),
]

MEASURE = r"""
(async (checks, W) => {
  try { await document.fonts.ready; } catch (e) {}
  await new Promise(r => setTimeout(r, 150));
  const out = [];
  const cs = e => getComputedStyle(e);
  const shown = e => { for (let x = e; x; x = x.parentElement) { const s = cs(x); if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) return false; } const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const name = e => { let s = e.tagName.toLowerCase(); if (e.id) return s + '#' + e.id; const c = [...e.classList].filter(x => !x.includes(':')).slice(0, 2); return s + c.map(x => '.' + x).join(''); };
  const path = e => { const p = []; for (let x = e; x && x !== document.body && p.length < 3; x = x.parentElement) p.unshift(name(x)); return p.join(' > '); };
  const label = e => ((e.innerText || e.getAttribute('aria-label') || e.value || e.getAttribute('title') || '') + '').trim().replace(/\s+/g, ' ').slice(0, 40);
  const rgba = s => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return [0, 0, 0, 0]; const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const contrast = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const bgOf = e => { for (let x = e; x; x = x.parentElement) { const c = rgba(cs(x).backgroundColor); if (c[3] > 0.5) return c; } return [255, 255, 255, 1]; };
  const fixed = e => { for (let x = e; x && x !== document.body; x = x.parentElement) { const p = cs(x).position; if (p === 'fixed' || p === 'sticky') return true; } return false; };
  // text nobody can see: inside a closed <details>, or clipped to nothing (screen-reader-only text, honeypot fields)
  const hiddenText = el => {
    const d = el.closest('details:not([open])');
    if (d && !el.closest('summary')) return true;
    for (let x = el; x && x !== document.body; x = x.parentElement) {
      const st = cs(x), r = x.getBoundingClientRect();
      if (st.clip !== 'auto' || st.clipPath !== 'none' || r.width <= 1 || r.height <= 1) return true;
      if (st.overflow !== 'visible' && (r.width < 4 || r.height < 4)) return true;
    }
    return false;
  };
  const all = [...document.body.querySelectorAll('*')].filter(e => !e.closest('svg') || e.tagName.toLowerCase() === 'svg');
  const NOTCARD = new Set('input select textarea button table thead tbody tfoot tr td th pre code img picture video audio svg dialog hr label option iframe canvas summary html body ul ol li nav header footer main form fieldset blockquote'.split(' '));
  const NOTSEG = /(^|[-_])(alert|banner|toast|notice|notification|callout|badge|chip|pill|tag|kbd|avatar|tooltip|btn|button|menu|dropdown|popover|modal|dialog|overlay|backdrop|skeleton)($|[-_])/i;
  const CONTROL = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=link],[role=switch],[role=checkbox],[role=tab]';

  if (checks.includes('hidden')) {
    for (const e of document.querySelectorAll('[hidden]')) {
      if (cs(e).display !== 'none' && e.getBoundingClientRect().height > 0)
        out.push({rule: 'hidden-visible', where: path(e), text: path(e) + ' has the hidden attribute but shows'});
    }
  }

  if (checks.includes('overflow')) {
    const sw = document.documentElement.scrollWidth;
    if (sw > W + 1) {
      const scrollBox = e => { for (let x = e.parentElement; x && x !== document.body && x !== document.documentElement; x = x.parentElement) { const o = cs(x).overflowX; if (o !== 'visible') return true; } return false; };
      const wide = all.filter(e => { if (!shown(e) || cs(e).position === 'fixed' || scrollBox(e)) return false; const r = e.getBoundingClientRect(); return r.right > W + 1 || r.left < -1; });
      const set = new Set(wide);
      let top = wide.filter(e => !set.has(e.parentElement)).slice(0, 3);
      if (!top.length) top = all.filter(e => cs(e).position === 'absolute' && e.getBoundingClientRect().right > W + 1).slice(0, 3);
      out.push({rule: 'overflow-x', where: top.map(path).join('; ') || 'page', text: 'page is ' + sw + 'px wide at ' + W + 'px' + (top.length ? ', from ' + top.map(path).join('; ') : '')});
    }
  }

  if (checks.includes('overlap')) {
    const boxes = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n && boxes.length < 1500; n = walker.nextNode()) {
      if (!n.nodeValue.trim()) continue;
      const el = n.parentElement;
      if (!el || ['SCRIPT', 'STYLE', 'NOSCRIPT', 'OPTION', 'TITLE'].includes(el.tagName) || !shown(el) || fixed(el) || hiddenText(el)) continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) if (r.width > 2 && r.height > 2) boxes.push({r, el});
    }
    const seen = new Set();
    boxes.sort((a, b) => a.r.top - b.r.top);
    for (let i = 0; i < boxes.length; i++) {
      const a = boxes[i];
      for (let j = i + 1; j < boxes.length && boxes[j].r.top < a.r.bottom; j++) {
        const b = boxes[j];
        if (a.el === b.el || a.el.contains(b.el) || b.el.contains(a.el)) continue;
        const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
        const h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
        if (w > 3 && h > 3) {
          const k = path(a.el) + '|' + path(b.el);
          if (seen.has(k)) continue; seen.add(k);
          out.push({rule: 'text-overlap', where: k, text: '"' + label(a.el) + '" overlaps "' + label(b.el) + '"'});
          if (seen.size > 5) break;
        }
      }
    }
  }

  let cards = [];
  if (checks.includes('cards')) {
    const isCard = e => {
      const t = e.tagName.toLowerCase();
      if (NOTCARD.has(t) || e.closest('svg') || e.matches(CONTROL)) return false;
      const role = (e.getAttribute('role') || '').toLowerCase();
      if (['alert', 'status', 'log', 'dialog', 'alertdialog', 'tabpanel', 'button', 'tooltip', 'menu', 'listbox'].includes(role)) return false;
      if ([...e.classList].some(c => NOTSEG.test(c))) return false;
      const s = cs(e);
      if (s.display.startsWith('inline') || s.position === 'fixed') return false;
      if (!shown(e)) return false;
      const r = e.getBoundingClientRect();
      if (r.width < 80 || r.height < 32) return false;
      const pad = ['Top', 'Right', 'Bottom', 'Left'].some(k => parseFloat(s['padding' + k]) > 0);
      if (!pad) return false;
      const border = ['Top', 'Right', 'Bottom', 'Left'].every(k => parseFloat(s['border' + k + 'Width']) > 0 && s['border' + k + 'Style'] !== 'none' && rgba(s['border' + k + 'Color'])[3] > 0);
      const shadow = s.boxShadow && s.boxShadow !== 'none';
      const bg = rgba(s.backgroundColor);
      const pbg = e.parentElement ? bgOf(e.parentElement) : [255, 255, 255, 1];
      const radius = parseFloat(s.borderTopLeftRadius) > 0;
      const fill = bg[3] > 0.5 && (Math.abs(bg[0] - pbg[0]) + Math.abs(bg[1] - pbg[1]) + Math.abs(bg[2] - pbg[2]) > 6) && radius;
      return border || shadow || fill;
    };
    cards = all.filter(isCard);
    const cset = new Set(cards);
    const seen = new Set();
    for (const c of cards) {
      let o = c.parentElement; while (o && !cset.has(o)) o = o.parentElement;
      if (o) {
        const k = name(o) + '>' + name(c);
        if (!seen.has(k)) { seen.add(k); out.push({rule: 'nested-card', where: k, text: path(c) + ' inside ' + name(o)}); }
        continue;
      }
      if (c.querySelector('img,svg,video,canvas,table,ul,ol,dl') || cards.some(d => d !== c && c.contains(d))) continue;
      const controls = [...c.querySelectorAll(CONTROL)].filter(shown);
      const outer = controls.filter(x => !controls.some(y => y !== x && y.contains(x)));
      let lines = 0;
      const w = document.createTreeWalker(c, NodeFilter.SHOW_TEXT);
      for (let n = w.nextNode(); n; n = w.nextNode()) {
        if (!n.nodeValue.trim() || !shown(n.parentElement)) continue;
        if (n.parentElement.closest('h1,h2,h3,h4,h5,h6,legend,label,[role=heading]') || controls.some(x => x.contains(n))) continue;
        lines++;
      }
      if ((outer.length === 1 && lines === 0) || (outer.length === 0 && lines === 1)) {
        const k = name(c);
        if (!seen.has(k)) { seen.add(k); out.push({rule: 'single-control-card', where: k, text: path(c) + ' holds ' + (outer.length ? 'one control' : 'one line')}); }
      }
    }
  }

  if (checks.includes('primary')) {
    const scopes = new Map();
    for (const e of document.querySelectorAll('button,a[href],input[type=submit],input[type=button],[role=button]')) {
      if (!shown(e) || e.getAttribute('aria-pressed') === 'true' || e.getAttribute('aria-selected') === 'true' || e.hasAttribute('aria-current')) continue;
      const r = e.getBoundingClientRect();
      if (r.height < 20 || r.width < 40) continue;
      const bg = rgba(cs(e).backgroundColor);
      if (bg[3] < 0.5) continue;
      const pb = e.parentElement ? bgOf(e.parentElement) : [255, 255, 255, 1];
      if (contrast(bg, pb) < 3) continue;
      const scope = e.closest('dialog,[role=dialog],[role=alertdialog],aside,[popover]') || document.body;
      if (!scopes.has(scope)) scopes.set(scope, []);
      scopes.get(scope).push(e);
    }
    for (const [scope, list] of scopes) {
      if (list.length > 1) out.push({rule: 'multiple-primary', where: scope === document.body ? 'page' : name(scope),
        text: list.length + ' filled buttons in ' + (scope === document.body ? 'the page' : name(scope)) + ': ' + list.slice(0, 4).map(e => '"' + label(e) + '"').join(', ')});
    }
  }

  if (checks.includes('targets')) {
    const ts = [...document.querySelectorAll(CONTROL)].filter(e => shown(e) && !hiddenText(e));
    const rects = ts.map(e => {
      let x = e;
      if (e.matches('input[type=checkbox],input[type=radio]') && e.closest('label')) x = e.closest('label');
      return {e, r: x.getBoundingClientRect()};
    }).filter(o => o.r.width > 1 && o.r.height > 1);
    const inline = e => { if (e.tagName !== 'A') return false; const p = e.parentElement; if (!p || !p.matches('p,li,td,dd,span,small,label,figcaption')) return false; return (p.innerText || '').trim().length > (e.innerText || '').trim().length + 3; };
    let n = 0;
    for (const a of rects) {
      if ((a.r.width >= 24 && a.r.height >= 24) || inline(a.e)) continue;
      const cx = a.r.left + a.r.width / 2, cy = a.r.top + a.r.height / 2;
      let crowded = false;
      for (const b of rects) {
        if (b === a || b.e.contains(a.e) || a.e.contains(b.e)) continue;
        const small = b.r.width < 24 || b.r.height < 24;
        if (small) { const bx = b.r.left + b.r.width / 2, by = b.r.top + b.r.height / 2; if (Math.hypot(cx - bx, cy - by) < 24) { crowded = true; break; } }
        else { const dx = Math.max(b.r.left - cx, 0, cx - b.r.right), dy = Math.max(b.r.top - cy, 0, cy - b.r.bottom); if (Math.hypot(dx, dy) < 12) { crowded = true; break; } }
      }
      if (crowded) {
        out.push({rule: 'small-target', where: path(a.e), text: path(a.e) + ' "' + label(a.e) + '" is ' + Math.round(a.r.width) + 'x' + Math.round(a.r.height) + 'px'});
        if (++n >= 8) break;
      }
    }
  }

  if (checks.includes('lines')) {
    let n = 0;
    for (const e of document.querySelectorAll('p,li,dd,blockquote,figcaption,td')) {
      if (!shown(e) || e.querySelector('p,li,div,ul,ol,table')) continue;
      const t = (e.innerText || '').trim();
      if (t.length < 160) continue;
      const rg = document.createRange(); rg.selectNodeContents(e);
      const tops = new Set([...rg.getClientRects()].filter(r => r.width > 1).map(r => Math.round(r.top)));
      const lines = tops.size;
      if (lines >= 2 && t.length / lines > 80) {
        out.push({rule: 'long-lines', where: path(e), text: path(e) + ' runs about ' + Math.round(t.length / lines) + ' characters per line'});
        if (++n >= 5) break;
      }
    }
  }
  return {findings: out, width: innerWidth, title: document.title};
})
"""


def find_chrome():
    env = os.environ.get("UI_STANDARDS_CHROME") or os.environ.get("CHROME_PATH")
    if env and os.path.isfile(env):
        return env
    for c in CANDIDATES:
        if os.path.isfile(c):
            return c
    for n in NAMES:
        p = shutil.which(n)
        if p:
            return p
    return None


class Chrome(object):
    def __init__(self, exe):
        r1, self.w = os.pipe()
        self.r, w2 = os.pipe()
        hr, hw = os.dup(r1), os.dup(w2)

        def child():
            os.dup2(hr, 3)
            os.dup2(hw, 4)
            os.set_inheritable(3, True)
            os.set_inheritable(4, True)

        self.profile = tempfile.mkdtemp(prefix="ui-standards-chrome-")
        args = [exe, "--headless=new", "--remote-debugging-pipe", "--no-first-run", "--no-default-browser-check",
                "--disable-gpu", "--hide-scrollbars", "--mute-audio", "--disable-extensions",
                "--user-data-dir=" + self.profile, "about:blank"]
        if sys.platform.startswith("linux") and hasattr(os, "geteuid") and os.geteuid() == 0:
            args.insert(1, "--no-sandbox")
        self.proc = subprocess.Popen(args, preexec_fn=child, close_fds=False,
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for fd in (r1, w2, hr, hw):
            os.close(fd)
        self.buf, self.mid, self.events = b"", 0, []

    def _recv(self, timeout):
        end = time.time() + timeout
        while b"\0" not in self.buf:
            left = end - time.time()
            if left <= 0:
                raise TimeoutError("Chrome did not answer")
            ready, _, _ = select.select([self.r], [], [], left)
            if not ready:
                raise TimeoutError("Chrome did not answer")
            chunk = os.read(self.r, 1 << 20)
            if not chunk:
                raise EOFError("Chrome closed")
            self.buf += chunk
        i = self.buf.index(b"\0")
        msg, self.buf = self.buf[:i], self.buf[i + 1:]
        return json.loads(msg.decode("utf-8", "replace"))

    def call(self, method, params=None, session=None, timeout=20):
        self.mid += 1
        msg = {"id": self.mid, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        os.write(self.w, json.dumps(msg).encode() + b"\0")
        while True:
            m = self._recv(timeout)
            if m.get("id") == self.mid:
                if "error" in m:
                    raise RuntimeError("%s: %s" % (method, m["error"].get("message")))
                return m.get("result", {})
            self.events.append(m)

    def wait_event(self, name, timeout):
        for i, m in enumerate(self.events):
            if m.get("method") == name:
                del self.events[i]
                return m
        end = time.time() + timeout
        while time.time() < end:
            m = self._recv(end - time.time())
            if m.get("method") == name:
                return m
            self.events.append(m)
        raise TimeoutError(name)

    def close(self):
        try:
            self.call("Browser.close", timeout=3)
        except Exception:
            pass
        try:
            self.proc.wait(3)
        except Exception:
            self.proc.kill()
        for fd in (self.r, self.w):
            try:
                os.close(fd)
            except OSError:
                pass
        shutil.rmtree(self.profile, ignore_errors=True)


def slug(target):
    base = re.sub(r"^[a-z]+://", "", target)
    base = re.sub(r"[^A-Za-z0-9]+", "-", base).strip("-")
    return base[-60:] or "page"


def render(target, out_dir, wait_ms=0):
    exe = find_chrome()
    if not exe:
        return {"shots": [], "findings": [], "error": "no-chrome"}
    url = target if re.match(r"^[a-z]+://", target) else "file://" + os.path.abspath(target)
    os.makedirs(out_dir, exist_ok=True)
    shots, found = [], []
    ch = Chrome(exe)
    try:
        tid = ch.call("Target.createTarget", {"url": "about:blank"})["targetId"]
        sid = ch.call("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
        ch.call("Page.enable", session=sid)
        ch.call("Runtime.enable", session=sid)
        for width, height, checks, shot in PASSES:
            ch.call("Emulation.setDeviceMetricsOverride",
                    {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False}, session=sid)
            ch.events = [e for e in ch.events if e.get("method") != "Page.loadEventFired"]
            nav = ch.call("Page.navigate", {"url": url}, session=sid)
            if nav.get("errorText"):
                return {"shots": shots, "findings": found, "error": "Couldn't load %s: %s" % (url, nav["errorText"])}
            try:
                ch.wait_event("Page.loadEventFired", 20)
            except TimeoutError:
                pass
            if wait_ms:
                time.sleep(wait_ms / 1000.0)
            res = ch.call("Runtime.evaluate", {"expression": "%s(%s, %d)" % (MEASURE, json.dumps(checks), width),
                                               "awaitPromise": True, "returnByValue": True}, session=sid, timeout=30)
            val = (res.get("result") or {}).get("value") or {}
            if res.get("exceptionDetails"):
                return {"shots": shots, "findings": found,
                        "error": "The layout script failed: %s" % res["exceptionDetails"].get("text", "")}
            for f in val.get("findings", []):
                f["width"] = width
                found.append(f)
            if shot:
                m = ch.call("Page.getLayoutMetrics", session=sid)
                full = m.get("cssContentSize") or m.get("contentSize") or {}
                h = int(min(max(full.get("height", height), height), 8000))
                img = ch.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
                                                         "clip": {"x": 0, "y": 0, "width": width, "height": h, "scale": 1}},
                              session=sid, timeout=40)
                p = os.path.join(out_dir, "%s-%d.png" % (slug(target), width))
                with open(p, "wb") as fh:
                    fh.write(base64.b64decode(img["data"]))
                shots.append(p)
    except Exception as e:
        return {"shots": shots, "findings": found, "error": "Render failed: %s" % e}
    finally:
        ch.close()
    return {"shots": shots, "findings": found, "error": None}
