"""Layout rules for ui-standards: static checks on HTML, Vue, Svelte, JSX/TSX, CSS, Dart and Swift.

findings(src, path) returns a list of dicts:
  rule, tier ("block" or "report"), line, key (stable across edits, used to diff), text (what was found)

The main script sets scan_literals and STATE_DIR before use.
"""
import bisect
import hashlib
import json
import os
import re
import time
from html.parser import HTMLParser

scan_literals = None  # set by the main script
STATE_DIR = os.path.expanduser("~/.cache/ui-standards")

SCALE = (0, 1, 2, 4, 8, 12, 16, 24, 32, 48, 64)
FONT_SIZES_MAX = 4
WEIGHTS_MAX = 2
DEPTH_MAX = 8
BLOCK, REPORT = "block", "report"

HINTS = {
    "nested-card": "Remove the inner card's border, shadow or background. Group with space, a heading or a divider.",
    "single-control-card": "Drop the card. Put the control or line under its section heading.",
    "multiple-primary": "Keep one primary action in this view. Make the rest secondary buttons or links.",
    "off-scale-spacing": "Use the spacing scale: 4, 8, 12, 16, 24, 32, 48 or 64px, or the project's spacing tokens.",
    "heading-skip": "Go down one heading level at a time, and use one h1 per view.",
    "overflow-x": "The page scrolls sideways at 320px wide. Let rows wrap or stack, and give wide tables or code their own scroll box.",
    "text-overlap": "Text overlaps other text. Fix the position, size or spacing.",
    "hidden-visible": "An element marked hidden is showing because a display rule overrides [hidden]. Add [hidden] { display: none !important; }.",
    "stat-tiles": "Stat tiles belong only on a monitoring screen, each number with context (a target, a prior period or a trend). Otherwise show numbers where they're used.",
    "card-grid": "Identical icon, heading and text cards read as filler. Use a plain list, or keep only what users need.",
    "type-scale": "Use at most 4 font sizes and 2 weights.",
    "deep-nesting": "Remove wrappers that add no layout.",
    "badge-above-h1": "Remove the pill above the main heading.",
    "eyebrow": "Remove the small uppercase labels above headings.",
    "emoji-icon": "Use an icon or plain text, not emoji.",
    "gradient-text": "Use a solid text color.",
    "accent-stripe": "Remove the colored edge stripe. Show status with text or an icon.",
    "repeated-cta": "Show the call to action once.",
    "small-target": "Make the target at least 24px, or leave 24px clear around it.",
    "long-lines": "Cap the text width near 70 characters, such as max-width: 60ch.",
}
BLOCK_RULES = {"nested-card", "single-control-card", "multiple-primary", "off-scale-spacing",
               "heading-skip", "overflow-x", "text-overlap", "hidden-visible"}
RULES = list(HINTS)


def tier_of(rule):
    return BLOCK if rule in BLOCK_RULES else REPORT


PH = "¤"
CSS_EXTS = {".css": "css", ".scss": "css", ".less": "css", ".pcss": "css"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
NO_DEPTH = {"a", "abbr", "b", "bdi", "bdo", "br", "cite", "code", "data", "dfn", "em", "i", "kbd", "mark",
            "q", "s", "small", "span", "strong", "sub", "sup", "time", "u", "var", "wbr", "img", "svg",
            "samp", "path", "html", "head", "body", "script", "style", "template", "link", "meta", "title",
            "option", "optgroup", "thead", "tbody", "tfoot", "tr"}
NOT_CARD_TAGS = {"input", "select", "textarea", "button", "table", "thead", "tbody", "tfoot", "tr", "td",
                 "th", "pre", "code", "img", "picture", "video", "audio", "svg", "dialog", "hr", "label",
                 "option", "iframe", "canvas", "summary", "kbd", "samp", "html", "body", "head", "script",
                 "style", "template", "blockquote", "fieldset", "legend", "ul", "ol", "li", "nav", "header",
                 "footer", "main", "form"}
NOT_CARD_SEGS = {"alert", "banner", "toast", "notice", "notification", "callout", "badge", "chip", "pill",
                 "tag", "kbd", "avatar", "tooltip", "btn", "button", "input", "field", "toolbar", "menu",
                 "dropdown", "popover", "modal", "dialog", "overlay", "backdrop", "skeleton"}
NOT_CARD_ROLES = {"alert", "status", "log", "dialog", "alertdialog", "tabpanel", "button", "tooltip", "menu", "listbox"}
CARD_SEGS = {"card", "panel", "tile", "box"}
MEDIA = {"img", "svg", "video", "canvas", "table", "picture", "ul", "ol", "dl"}
CONTROL_TAGS = {"button", "input", "select", "textarea", "summary"}
CONTROL_COMP = re.compile(r"(Button|Link|Input|Select|Switch|Checkbox|Toggle|Radio|TextField|Slider)$")
SCOPE_COMP = re.compile(r"(Dialog|Modal|Sheet|Drawer|Popover|Aside|Sidebar|SidePanel)$")
HEADING = re.compile(r"^h([1-6])$")
EMOJI = re.compile("[\U0001F300-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF"
                   "☀-⛿✅✨❌❎❓-❕❗❤➕-➗➡"
                   "⭐⭕⌚⌛⏩-⏳⏸-⏺\U0001F1E6-\U0001F1FF]")
NUMERIC = re.compile(r"^[~≈<>+\-−±]?\s?[$€£¥]?\s?(\d[\d,.]*|¤)\s?"
                     r"(%|[kKmMbB]|ms|s|sec|min|h|d|x|×|GB|MB|KB|TB|/\s?\d+)?$")
WORD = re.compile(r"[A-Za-z0-9¤](?:[A-Za-z0-9'’\-.]*[A-Za-z0-9])?")


class Lines(object):
    def __init__(self, src):
        self.nl = [m.start() for m in re.finditer("\n", src)]

    def at(self, idx):
        return bisect.bisect_right(self.nl, idx - 1) + 1


def segs(token):
    token = re.sub(r"^(?:[\w-]+:)+", "", token)  # Tailwind variants like md:
    parts = re.split(r"[-_]+|(?<=[a-z0-9])(?=[A-Z])", token)
    return [p.lower() for p in parts if p]


def find(rule, line, key, text, tier=None):
    return {"rule": rule, "tier": tier or tier_of(rule), "line": line, "key": "%s|%s" % (rule, key), "text": text}


# ---------- CSS ----------

def _match_brace(s, i, end):
    depth = 0
    while i < end:
        c = s[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        elif c in "\"'":
            j = s.find(c, i + 1)
            i = end if j < 0 else j
        i += 1
    return end


def _combine(parent, head):
    if not parent:
        return head
    out = []
    for part in head.split(","):
        part = part.strip()
        for p in parent.split(","):
            p = p.strip()
            out.append(part.replace("&", p) if "&" in part else p + " " + part)
    return ", ".join(out)


def parse_decls(text, line=0, line_at=None, base=0):
    """'a: b; c: d' -> [(prop, value, line)]"""
    out = []
    pos = 0
    for raw in text.split(";"):
        start = pos
        pos += len(raw) + 1
        if ":" not in raw:
            continue
        prop, val = raw.split(":", 1)
        prop = prop.strip().lower()
        val = re.sub(r"\s*!important\s*$", "", val.strip(), flags=re.I)
        if not prop or not val or not re.match(r"^-?-?[a-z][\w-]*$", prop):
            continue
        lead = len(raw) - len(raw.lstrip())
        ln = line_at(base + start + lead) if line_at else line
        out.append((prop, val, ln))
    return out


def parse_css(text, line_off=0):
    """[(selector, [(prop, value, line)])] for every style rule, nested rules and @media included."""
    clean = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    lines = Lines(clean)
    line_at = lambda i: lines.at(i) + line_off
    out = []

    def block(i, end, sel):
        decl_txt, seg = [], i
        while i < end:
            c = clean[i]
            if c == "{":
                head = clean[seg:i].strip()
                j = _match_brace(clean, i, end)
                low = head.lower()
                if head.startswith("@"):
                    if low.startswith(("@media", "@supports", "@layer", "@container", "@scope", "@document")):
                        block(i + 1, j - 1, sel)
                    elif low.startswith("@theme"):
                        block(i + 1, j - 1, ":root")
                elif head:
                    block(i + 1, j - 1, _combine(sel, head))
                i = seg = j
                continue
            if c == ";":
                decl_txt.append((seg, clean[seg:i]))
                seg = i + 1
            elif c == "}":
                seg = i + 1
            i += 1
        if clean[seg:end].strip():
            decl_txt.append((seg, clean[seg:end]))
        if sel:
            decls = []
            for start, t in decl_txt:
                decls.extend(parse_decls(t, line_at=line_at, base=start))
            if decls:
                out.append((sel, decls))

    block(0, len(clean), None)
    return out


SIMPLE = re.compile(r"([.#]-?[A-Za-z_][\w-]*)|(\[[^\]]*\])|(::?[\w-]+(?:\([^)]*\))?)|(\*)|(-?[A-Za-z][\w-]*)")


def compound_of(part):
    """The last compound selector of a selector chain: (tag, classes, ids, attrs, stateful)."""
    stateful = bool(re.search(r":(?!root\b|is\(|where\(|not\()", part))
    last = re.split(r"\s*[>+~]\s*|\s+", re.sub(r"\([^)]*\)", "", part.strip()))[-1]
    tag, classes, ids, attrs = None, set(), set(), set()
    for m in SIMPLE.finditer(last):
        tok = m.group(0)
        if tok.startswith("."):
            classes.add(tok[1:])
        elif tok.startswith("#"):
            ids.add(tok[1:])
        elif tok.startswith("["):
            am = re.match(r"\[\s*([\w-]+)", tok)
            if am:
                attrs.add(am.group(1).lower())
        elif tok.startswith(":") or tok == "*":
            continue
        else:
            tag = tok.lower()
    return tag, frozenset(classes), frozenset(ids), frozenset(attrs), stateful


class Sheet(object):
    def __init__(self):
        self.rules = []
        self.by_class, self.by_tag, self.by_id, self.univ = {}, {}, {}, []
        self.local = []  # (prop, value, line, selector) declared in the checked file itself

    def add(self, css_text, line_off=0, local=True):
        for sel, decls in parse_css(css_text, line_off):
            self.add_rule(sel, decls, local)

    def add_rule(self, sel, decls, local=True):
        if local:
            for p, v, ln in decls:
                self.local.append((p, v, ln, sel))
        for part in sel.split(","):
            tag, classes, ids, attrs, stateful = compound_of(part)
            if stateful or not (tag or classes or ids or attrs):
                continue
            idx = len(self.rules)
            self.rules.append((tag, classes, ids, attrs, decls))
            if classes:
                self.by_class.setdefault(sorted(classes)[0], []).append(idx)
            elif ids:
                self.by_id.setdefault(sorted(ids)[0], []).append(idx)
            elif tag:
                self.by_tag.setdefault(tag, []).append(idx)
            else:
                self.univ.append(idx)

    def resolve(self, node):
        if node.decl is not None:
            return node.decl
        cand = set(self.univ)
        cand.update(self.by_tag.get(node.tag, ()))
        for c in node.cls:
            cand.update(self.by_class.get(c, ()))
        nid = node.attrs.get("id") if isinstance(node.attrs.get("id"), str) else None
        if nid:
            cand.update(self.by_id.get(nid, ()))
        d = {}
        cls = set(node.cls)
        for idx in sorted(cand):
            tag, classes, ids, attrs, decls = self.rules[idx]
            if tag and tag != node.tag:
                continue
            if not classes <= cls:
                continue
            if ids and nid not in ids:
                continue
            if any(a not in node.attrs for a in attrs):
                continue
            for p, v, _ in decls:
                d[p] = v
        for p, v, _ in node.style:
            d[p] = v
        node.decl = d
        return d


# ---------- element trees ----------

class Node(object):
    __slots__ = ("tag", "attrs", "cls", "style", "line", "kids", "parent", "text", "comp", "decl")

    def __init__(self, tag, attrs, line, parent=None, comp=False):
        self.tag, self.attrs, self.line, self.parent, self.comp = tag, attrs, line, parent, comp
        self.kids, self.text, self.cls, self.style, self.decl = [], [], [], [], None

    def walk(self):
        for k in self.kids:
            yield k
            for d in k.walk():
                yield d

    def ancestors(self):
        p = self.parent
        while p is not None and p.tag != "#root":
            yield p
            p = p.parent

    def attr(self, name):
        v = self.attrs.get(name)
        return v if isinstance(v, str) else ""


def html_classes(a):
    out = (a.get("class") or "").split()
    for k in (":class", "v-bind:class"):
        if a.get(k):
            out.extend(t for s in re.findall(r"['\"`]([^'\"`]*)['\"`]", a[k]) for t in s.split())
            out.extend(re.findall(r"([A-Za-z][\w-]*)\s*:", a[k]))
    for k in a:
        if k.startswith("class:"):
            out.append(k[6:])
    return [c for c in out if c and PH not in c]


class _Tree(HTMLParser):
    def __init__(self, off):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.off = off
        self.root = Node("#root", {}, 0)
        self.cur = self.root
        self.css, self.scripts, self.links = [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict((k.lower(), v if v is not None else "") for k, v in attrs)
        line = self.getpos()[0] + self.off
        if tag == "link" and "stylesheet" in a.get("rel", "").lower() and a.get("href"):
            self.links.append(a["href"])
        n = Node(tag, a, line, self.cur)
        n.cls = html_classes(a)
        if a.get("style"):
            n.style = parse_decls(a["style"], line)
        self.cur.kids.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.cur.tag == tag:
            self.cur = self.cur.parent

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        if self.cur.tag == "style":
            self.css.append((data, self.getpos()[0] + self.off - 1))
        elif self.cur.tag == "script":
            if (self.cur.attr("type") or "text/javascript").lower() in ("", "module", "text/javascript", "application/javascript"):
                self.scripts.append((self.getpos()[0] + self.off - 1, data))
        elif data.strip():
            self.cur.text.append(data)


def blank_expr(src):
    """Replace {{ }} and { } template expressions outside script and style, keeping newlines."""
    parts = re.split(r"(<script\b.*?</script>|<style\b.*?</style>)", src, flags=re.S | re.I)
    keep = lambda m: PH + "\n" * m.group(0).count("\n")
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r"\{\{.*?\}\}", keep, parts[i], flags=re.S)
        parts[i] = re.sub(r"\{[^{}]*\}", keep, parts[i])
    return "".join(parts)


def html_tree(src, off=0, embedded=False):
    t = _Tree(off)
    try:
        t.feed(src if embedded else blank_expr(src))
        t.close()
    except Exception:
        pass
    return t


JSX_PREV = set("(,=:?&|{}[;>")
NAME = re.compile(r"[A-Za-z][\w.:-]*")
ATTR = re.compile(r"[A-Za-z_$][\w:.$-]*")


def jsx_tree(src):
    """Element tree for JSX/TSX. Elements inside {expressions} attach to the enclosing element."""
    root = Node("#root", {}, 0)
    lines = Lines(src)
    n = len(src)

    def skip_str(i):
        q, j = src[i], i + 1
        while j < n:
            c = src[j]
            if c == "\\":
                j += 2
                continue
            if q == "`" and src.startswith("${", j):
                j = js(j + 2, None, True)
                continue
            if c == q or (q != "`" and c == "\n"):
                return j + 1
            j += 1
        return n

    def jsx_start(i):
        if i + 1 >= n or not (src[i + 1].isalpha() or src[i + 1] == ">"):
            return False
        k = i - 1
        while k >= 0 and src[k] in " \t\r\n":
            k -= 1
        if k < 0 or src[k] in JSX_PREV:
            return True
        return bool(re.search(r"\b(return|yield|default|in|of)$", src[max(0, k - 8):k + 1]))

    def js(i, parent, until_brace):
        depth = 0
        while i < n:
            c = src[i]
            if c in "'\"`":
                i = skip_str(i)
                continue
            if c == "/" and src.startswith("//", i):
                j = src.find("\n", i)
                i = n if j < 0 else j
                continue
            if c == "/" and src.startswith("/*", i):
                j = src.find("*/", i + 2)
                i = n if j < 0 else j + 2
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                if depth == 0 and until_brace:
                    return i + 1
                depth -= 1
            elif c == "<" and jsx_start(i):
                i = element(i, parent if parent is not None else Node("#tmp", {}, 0))
                continue
            i += 1
        return n

    def make(name, attrs, exprs, i, parent):
        comp = name[0].isupper() or "." in name
        node = Node(name if comp else name.lower(), attrs, lines.at(i), parent, comp)
        cls = []
        cv = attrs.get("className") or attrs.get("class")
        if isinstance(cv, str):
            cls.extend(cv.split())
        ce = exprs.get("className") or exprs.get("class")
        if ce:
            for s in re.findall(r"[\"'`]([^\"'`]*)[\"'`]", ce):
                cls.extend(t for t in s.split() if "${" not in t)
            cls.extend(re.findall(r"\b(?:styles|classes|css|s|cx)\.([A-Za-z_][\w-]*)", ce))
            cls.extend(re.findall(r"\b(?:styles|classes|css|s)\[\s*[\"']([\w-]+)[\"']\s*\]", ce))
        node.cls = cls
        se = exprs.get("style")
        if se:
            node.style = js_style(se, node.line)
        for k, v in exprs.items():
            m = re.match(r"^\s*[\"'`]([^\"'`]*)[\"'`]\s*$", v)
            if m and k not in attrs:
                attrs[k] = m.group(1)
        parent.kids.append(node)
        return node

    def children(j, node):
        while j < n:
            c = src[j]
            if c == "<":
                if src.startswith("</", j):
                    k = src.find(">", j)
                    return n if k < 0 else k + 1
                before = len(node.kids)
                k = element(j, node)
                if k == j + 1 and len(node.kids) == before:
                    j += 1  # stray '<'
                else:
                    j = k
                continue
            if c == "{":
                before = len(node.kids)
                k = js(j + 1, node, True)
                inner = src[j + 1:k - 1].strip()
                if len(node.kids) == before and inner and not inner.startswith("/*"):
                    node.text.append(PH)
                j = k
                continue
            k = j
            while k < n and src[k] not in "<{":
                k += 1
            if src[j:k].strip():
                node.text.append(src[j:k])
            j = k
        return n

    def element(i, parent):
        j = i + 1
        if j < n and src[j] == ">":
            return children(j + 1, parent)
        m = NAME.match(src, j)
        if not m:
            return i + 1
        name, j = m.group(0), m.end()
        attrs, exprs = {}, {}
        while j < n:
            while j < n and src[j].isspace():
                j += 1
            if j >= n:
                return n
            c = src[j]
            if src.startswith("/>", j):
                make(name, attrs, exprs, i, parent)
                return j + 2
            if c == ">":
                return children(j + 1, make(name, attrs, exprs, i, parent))
            if c == "{":
                j = js(j + 1, None, True)
                continue
            am = ATTR.match(src, j)
            if not am:
                return i + 1
            an, j = am.group(0), am.end()
            while j < n and src[j].isspace():
                j += 1
            if j < n and src[j] == "=":
                j += 1
                while j < n and src[j].isspace():
                    j += 1
                if j < n and src[j] in "\"'":
                    k = skip_str(j)
                    attrs[an] = src[j + 1:k - 1]
                    j = k
                elif j < n and src[j] == "{":
                    k = js(j + 1, None, True)
                    exprs[an] = src[j + 1:k - 1]
                    j = k
                else:
                    return i + 1
            else:
                attrs[an] = True
        return n

    js(0, root, False)
    return root


JS_SPACING_KEYS = {"padding": "padding", "paddingTop": "padding-top", "paddingRight": "padding-right",
                   "paddingBottom": "padding-bottom", "paddingLeft": "padding-left",
                   "paddingInline": "padding-inline", "paddingBlock": "padding-block",
                   "paddingX": "padding-inline", "paddingY": "padding-block",
                   "margin": "margin", "marginTop": "margin-top", "marginRight": "margin-right",
                   "marginBottom": "margin-bottom", "marginLeft": "margin-left",
                   "marginInline": "margin-inline", "marginBlock": "margin-block",
                   "gap": "gap", "rowGap": "row-gap", "columnGap": "column-gap",
                   "fontSize": "font-size", "fontWeight": "font-weight", "borderRadius": "border-radius",
                   "border": "border", "boxShadow": "box-shadow", "background": "background",
                   "backgroundColor": "background-color", "textTransform": "text-transform",
                   "borderLeft": "border-left", "borderTop": "border-top", "backgroundClip": "background-clip",
                   "WebkitBackgroundClip": "-webkit-background-clip"}
SPACING_PX_KEYS = {"padding", "padding-top", "padding-right", "padding-bottom", "padding-left", "padding-inline",
                   "padding-block", "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
                   "margin-inline", "margin-block", "gap", "row-gap", "column-gap", "font-size", "border-radius"}


def js_style(expr, line):
    out = []
    for m in re.finditer(r"\b([A-Za-z]+)\s*:\s*(?:([\"'`])([^\"'`]*)\2|(-?[\d.]+)\b)", expr):
        k = JS_SPACING_KEYS.get(m.group(1))
        if not k:
            continue
        v = m.group(3) if m.group(2) else m.group(4)
        if m.group(4) and k in SPACING_PX_KEYS:
            v = v + "px"
        out.append((k, v, line))
    return out


# ---------- facts about elements ----------

def tw(node):
    """Tailwind-style tokens without state variants (hover:, focus:) but with responsive ones."""
    out = []
    for c in node.cls:
        parts = c.split(":")
        if len(parts) > 1 and any(p not in ("sm", "md", "lg", "xl", "2xl", "dark") for p in parts[:-1]):
            continue
        out.append(parts[-1].lstrip("!"))
    return out


def px(v):
    v = v.strip().lower()
    m = re.match(r"^(-?[\d.]+)(px|rem)?$", v)
    if not m:
        return None
    try:
        num = float(m.group(1))
    except ValueError:
        return None
    if m.group(2) == "rem":
        num *= 16
    elif m.group(2) is None and num != 0:
        return None
    return num


def has_padding(node, d):
    for k, v in d.items():
        if k.startswith("padding") and any((px(t) or 0) > 0 or t.startswith(("var(", "calc(", "clamp(", "max(", "min("))
                                           or (t.endswith(("em", "%", "ch")) and not t.startswith("0")) for t in v.split()):
            return True
    return any(re.match(r"^p[xytrblse]?-(?!0$)", t) for t in tw(node))


def edge(node, d):
    """A visible edge: a full border, a shadow, or a background with rounded corners."""
    b = d.get("border")
    if b and not re.search(r"\b(none|hidden)\b|^0(px)?\b", b):
        return True
    bw, bs = d.get("border-width"), d.get("border-style")
    if bw and bs and bs != "none" and (px(bw.split()[0]) or 0) > 0:
        return True
    if all(d.get("border-" + s) and not re.search(r"\bnone\b|^0", d.get("border-" + s)) for s in ("top", "right", "bottom", "left")):
        return True
    sh = d.get("box-shadow")
    if sh and sh.strip() not in ("none", "0", "unset", "initial"):
        return True
    bg = d.get("background") or d.get("background-color")
    rad = d.get("border-radius")
    if bg and not re.search(r"^(none|transparent|inherit|unset|initial)\b", bg.strip()) and rad and not re.match(r"^0(px)?$", rad.strip()):
        return True
    toks = tw(node)
    if any(re.match(r"^(border(-\d+|-\[[^\]]+\])?|ring(-[1-8])?|shadow(-sm|-md|-lg|-xl|-2xl|-inner)?)$", t) for t in toks):
        return True
    if any(re.match(r"^bg-(?!transparent|none|clip|cover|contain|center|no-repeat|repeat|fixed|local|scroll|origin|blend|bottom|top|left|right|auto|gradient)", t) for t in toks) \
            and any(re.match(r"^rounded(?!-none)", t) for t in toks):
        return True
    return False


def is_card(node, sheet):
    if node.tag in NOT_CARD_TAGS or node.tag.startswith("#"):
        return False
    role = node.attr("role").lower()
    if role in NOT_CARD_ROLES:
        return False
    all_segs = set(s for c in node.cls for s in segs(c))
    if all_segs & NOT_CARD_SEGS:
        return False
    if node.comp:
        base = node.tag.split(".")[-1]
        if re.search(r"(Card|Panel|Tile)$", base) and not re.search(r"(Dialog|Modal|Sheet)", base):
            return True
        if SCOPE_COMP.search(base) or CONTROL_COMP.search(base):
            return False
    named = any(s in CARD_SEGS for c in node.cls if not re.match(r"^box-(border|content|decoration)", c) for s in segs(c)[-1:])
    if named or node.tag in NO_DEPTH:
        return named
    d = sheet.resolve(node)
    return edge(node, d) and has_padding(node, d)


def is_control(node):
    if node.comp:
        return bool(CONTROL_COMP.search(node.tag.split(".")[-1]))
    if node.tag in CONTROL_TAGS:
        return node.attr("type").lower() != "hidden"
    if node.tag == "a" and "href" in node.attrs:
        return True
    return node.attr("role").lower() in ("button", "link", "switch", "checkbox", "tab", "menuitem")


def is_heading(node):
    m = HEADING.match(node.tag)
    if m:
        return int(m.group(1))
    as_ = HEADING.match(node.attr("as"))
    if as_:
        return int(as_.group(1))
    v = HEADING.match(node.attr("variant"))
    if node.comp and v:
        return int(v.group(1))
    if node.attr("role") == "heading":
        try:
            return int(node.attr("aria-level") or 2)
        except ValueError:
            return 2
    return 0


def is_primary(node):
    if not (is_control(node) or node.tag in ("a", "button")):
        return False
    if node.attr("aria-pressed") == "true" or node.attr("aria-selected") == "true" or node.attr("aria-current"):
        return False
    for k in ("variant", "kind", "appearance", "type", "data-variant", "color", "intent"):
        v = node.attr(k).lower()
        if not v:
            continue
        if "primary" in v and (k != "color" or node.attr("variant").lower() in ("contained", "filled", "solid", "")):
            return True
        if k != "type" and v in ("filled", "solid", "contained", "cta"):
            return True
    return any("primary" in segs(c) for c in node.cls)


def scope_of(node):
    for a in node.ancestors():
        if a.tag in ("dialog", "aside", "template") or a.attr("role") in ("dialog", "alertdialog") \
                or "hidden" in a.attrs or "popover" in a.attrs:
            return a
        if a.comp and SCOPE_COMP.search(a.tag.split(".")[-1]):
            return a
    return None


def sig(node):
    if node is None:
        return "page"
    cls = [c for c in node.cls if ":" not in c][:2]
    s = node.tag + "".join("." + c for c in cls)
    if node.attr("id"):
        s += "#" + node.attr("id")
    return s


def texts(node, skip=None):
    """Text runs in the subtree, as (text, owner) pairs."""
    out = [(t.strip(), node) for t in node.text if t.strip()]
    for k in node.kids:
        if k.tag in ("script", "style", "svg") or (skip and skip(k)):
            continue
        out.extend(texts(k, skip))
    return out


def words(t):
    return len(WORD.findall(t))


def numeric(t):
    return bool(NUMERIC.match(t.strip()))


def norm_text(t):
    return re.sub(r"\s+", " ", t).strip()


# ---------- tree rules ----------

def tree_findings(root, sheet, component):
    out = []
    nodes = list(root.walk())
    cards = set(id(n) for n in nodes if is_card(n, sheet))

    for n in nodes:
        if id(n) not in cards:
            continue
        outer = next((a for a in n.ancestors() if id(a) in cards), None)
        if outer is not None:
            out.append(find("nested-card", n.line, "%s>%s" % (sig(outer), sig(n)), "%s inside %s" % (sig(n), sig(outer))))
            continue
        sub = list(n.walk())
        if any(d.tag in MEDIA for d in sub) or any(id(d) in cards for d in sub):
            continue
        controls = [d for d in sub if is_control(d)]
        ctrl_ids = set(id(c) for c in controls)
        controls = [c for c in controls if not any(id(a) in ctrl_ids for a in c.ancestors())]
        other = [t for t, _ in texts(n, skip=lambda k: bool(is_heading(k)) or id(k) in ctrl_ids or k.tag == "label")]
        if (len(controls) == 1 and not other) or (not controls and len(other) == 1 and words(other[0]) <= 12):
            what = "one control" if controls else "one line"
            label = norm_text(" ".join(t for t, _ in texts(n)))[:40]
            out.append(find("single-control-card", n.line, "%s|%s" % (sig(n), label), '%s "%s" holds %s' % (sig(n), label, what)))

    prim = {}
    for n in nodes:
        if is_primary(n) and not any(is_primary(a) for a in n.ancestors()):
            s = scope_of(n)
            prim.setdefault(id(s) if s else 0, (s, []))[1].append(n)
    for key, (s, ps) in prim.items():
        if len(ps) > 1:
            names = ", ".join('"%s"' % norm_text(" ".join(t for t, _ in texts(p)))[:30] for p in ps[:4])
            out.append(find("multiple-primary", ps[1].line, "%s|%d" % (sig(s), len(ps)),
                            "%d primary actions in %s: %s" % (len(ps), "the page" if s is None else sig(s), names),
                            REPORT if component else None))

    heads = {}
    for n in nodes:
        lvl = is_heading(n)
        if lvl:
            s = scope_of(n)
            heads.setdefault(id(s) if s else 0, (s, []))[1].append((lvl, n))
    for key, (s, hs) in heads.items():
        prev = None
        for lvl, n in hs:
            if prev is not None and lvl > prev + 1:
                t = norm_text(" ".join(x for x, _ in texts(n)))[:40]
                out.append(find("heading-skip", n.line, "h%d>h%d|%s" % (prev, lvl, t), 'h%d "%s" follows an h%d' % (lvl, t, prev)))
            prev = lvl
        h1 = [n for lvl, n in hs if lvl == 1]
        if len(h1) > 1:
            out.append(find("heading-skip", h1[1].line, "h1x%d|%s" % (len(h1), sig(s)),
                            "%d h1 headings in %s" % (len(h1), "the page" if s is None else sig(s)),
                            REPORT if component else None))

    # runs of identical siblings: stat tiles and icon card grids
    for n in [root] + nodes:
        kids = [k for k in n.kids if not k.tag.startswith("#")]
        i = 0
        while i < len(kids):
            j = i
            while j + 1 < len(kids) and sig(kids[j + 1]) == sig(kids[i]):
                j += 1
            run = kids[i:j + 1]
            if len(run) >= 3:
                if all(stat_like(k) for k in run):
                    out.append(find("stat-tiles", run[0].line, sig(run[0]), "%d stat tiles (%s)" % (len(run), sig(run[0]))))
                elif all(id(k) in cards and icon_card(k) for k in run):
                    out.append(find("card-grid", run[0].line, sig(run[0]), "%d icon cards (%s)" % (len(run), sig(run[0]))))
            i = j + 1
    for n in nodes:
        sg = set(s for c in n.cls for s in segs(c))
        if sg & {"stat", "kpi", "kpis", "metric"} and stat_like(n, loose=True):
            out.append(find("stat-tiles", n.line, sig(n), "stat tile (%s)" % sig(n)))

    # landing-page habits
    eyebrows = []
    for n in nodes:
        lvl = is_heading(n)
        if not lvl or n.parent is None:
            continue
        sibs = [k for k in n.parent.kids]
        i = sibs.index(n)
        prev = sibs[i - 1] if i > 0 else None
        if prev is None or is_heading(prev) or any(is_control(d) for d in [prev] + list(prev.walk())):
            continue
        t = norm_text(" ".join(x for x, _ in texts(prev)))
        if not t or words(t) > 6:
            continue
        psegs = set(s for c in prev.cls for s in segs(c))
        ptw = tw(prev)
        if lvl == 1 and (psegs & {"badge", "pill", "chip", "tag", "announcement", "announce"}
                         or ("rounded-full" in ptw and any(t_.startswith("px-") for t_ in ptw))):
            out.append(find("badge-above-h1", prev.line, "%s|%s" % (sig(prev), t[:30]), 'pill "%s" above the h1' % t[:40]))
            continue
        d = sheet.resolve(prev)
        if lvl <= 3 and words(t) <= 4 and ("uppercase" in (d.get("text-transform") or "") or "uppercase" in ptw
                                           or psegs & {"eyebrow", "kicker", "overline", "kicker"}):
            eyebrows.append((prev, t))
    if len(eyebrows) >= 2:
        out.append(find("eyebrow", eyebrows[1][0].line, "%d" % len(eyebrows),
                        "%d uppercase labels above headings, such as \"%s\"" % (len(eyebrows), eyebrows[0][1][:30])))

    for n in nodes:
        for t in n.text:
            s = t.strip()
            if s and EMOJI.match(s) and (len(s) <= 2 or re.match(r"^\S+\s+[A-Za-z]", s)) and words(s) <= 6:
                out.append(find("emoji-icon", n.line, s[:30], 'emoji in "%s"' % s[:40]))
        toks = tw(n)
        if "bg-clip-text" in toks:
            out.append(find("gradient-text", n.line, sig(n), "gradient text on %s" % sig(n)))
        if any(re.match(r"^border-[lt]-(\[([3-9]|\d\d)px\]|[3-8])$", t) for t in toks) and \
                any(re.match(r"^(rounded|bg-|p[xy]?-)", t) for t in toks) and n.tag != "blockquote":
            out.append(find("accent-stripe", n.line, sig(n), "colored edge stripe on %s" % sig(n)))

    # the same call-to-action band twice in a file
    bands = cta_bands(nodes)
    seen = {}
    for b, s in bands:
        seen.setdefault(s, []).append(b)
    for s, bs in seen.items():
        if len(bs) > 1:
            out.append(find("repeated-cta", bs[1].line, s[:60], 'call to action "%s" appears %d times' % (s.split("|")[0][:40], len(bs))))

    # depth
    best = (0, None)
    for n in nodes:
        dep = 0 if n.tag in NO_DEPTH else 1
        for a in n.ancestors():
            if a.tag == "svg":
                dep = 0
                break
            if a.tag not in NO_DEPTH:
                dep += 1
        if dep > best[0]:
            best = (dep, n)
    if best[0] > DEPTH_MAX:
        out.append(find("deep-nesting", best[1].line, "%d" % best[0], "%s is nested %d levels deep" % (sig(best[1]), best[0])))
    return out


def stat_like(node, loose=False):
    if any(is_control(d) for d in node.walk()):
        return False
    ts = [t for t, _ in texts(node)]
    if not ts or sum(words(t) for t in ts) > 8:
        return False
    nums = [t for t in ts if numeric(t)]
    if loose:
        return len(ts) >= 2 and bool(nums)
    return bool(nums) and len(ts) > len(nums)


def icon_card(node):
    sub = list(node.walk())
    icon = any(d.tag in ("svg", "img", "i") or any("icon" in segs(c) for c in d.cls) for d in sub) or \
        any(EMOJI.match(t) for t, _ in texts(node))
    head = any(is_heading(d) or d.tag in ("strong", "b") for d in sub)
    body = any(d.tag == "p" for d in sub) or any(words(t) >= 4 for t, _ in texts(node))
    return icon and head and body


def cta_bands(nodes):
    out = []
    cand = {}
    for n in nodes:
        if n.tag not in ("section", "div", "aside", "footer") and not n.comp:
            continue
        sub = list(n.walk())
        hs = [d for d in sub if is_heading(d) in (2, 3)]
        cs = [d for d in sub if is_control(d) and d.tag not in ("input", "select", "textarea")]
        if len(hs) != 1 or not 1 <= len(cs) <= 2 or any(d.tag in ("input", "select", "textarea", "form") for d in sub):
            continue
        band = set(s for c in n.cls for s in segs(c)) & {"cta", "callout", "promo", "signup", "hero", "banner", "action"}
        if not band and not any(is_primary(c) for c in cs):
            continue
        total = sum(words(t) for t, _ in texts(n))
        if total > 30:
            continue
        s = norm_text(" ".join(t for t, _ in texts(hs[0]))) + "|" + "|".join(norm_text(" ".join(t for t, _ in texts(c))) for c in cs)
        if PH in s or len(s) < 4:
            continue
        cand[id(n)] = (n, s)
    for k, (n, s) in cand.items():
        if any(id(d) in cand for d in n.walk()):
            continue
        out.append((n, s))
    return out


# ---------- declaration rules ----------

def spacing_allowed(path, extra_css):
    toks, base = project_tokens(path)
    toks = set(toks)
    t2, b2 = tokens_in(extra_css)
    toks.update(t2)
    base = base or b2
    if base:
        return lambda v: v in (0, 1, 2) or abs(v / base - round(v / base)) < 1e-6, "multiples of %gpx" % base
    if toks:
        ok = set(toks) | {0, 1, 2}
        return lambda v: v in ok, "the project's tokens (%s)" % ", ".join("%g" % x for x in sorted(ok) if x > 2)
    return lambda v: v in SCALE, None


SPACING_PROPS = re.compile(r"^(padding|margin)(-(top|right|bottom|left|inline|block)(-(start|end))?)?$|^(row-|column-|grid-)?gap$")


def decl_findings(decls, allowed, scale_note):
    """decls: (prop, value, line, where)."""
    out = []
    sizes, weights = {}, {}
    context = {}
    for prop, val, ln, where in decls:
        context.setdefault(where, set()).add(prop)
    for prop, val, ln, where in decls:
        v = val.strip()
        if SPACING_PROPS.match(prop) and not re.search(r"\w\(", v):
            for tok in v.split():
                num = px(tok)
                if num is None or tok.endswith("em") and not tok.endswith("rem"):
                    continue
                if not allowed(abs(num)):
                    out.append(find("off-scale-spacing", ln, "%s|%s|%s" % (prop, tok, where),
                                    "%s: %s in %s%s" % (prop, v, where, " (scale: %s)" % scale_note if scale_note else "")))
                    break
        if prop in ("font-size", "font"):
            m = re.search(r"(-?[\d.]+)(px|rem)\b", v) if prop == "font" else re.match(r"^(-?[\d.]+)(px|rem)$", v)
            if m:
                size = float(m.group(1)) * (16 if m.group(2) == "rem" else 1)
                sizes.setdefault(round(size, 2), ln)
        if prop == "font-weight":
            w = {"normal": 400, "bold": 700}.get(v.lower(), v)
            if re.match(r"^\d+$", str(w)):
                weights.setdefault(int(w), ln)
        if prop in ("background-clip", "-webkit-background-clip") and v.lower() == "text":
            out.append(find("gradient-text", ln, where, "gradient text in %s" % where))
        if prop in ("border-left", "border-top", "border-inline-start", "border-left-width", "border-top-width") \
                and not re.search(r"blockquote|\b(nav|tab|menu|sidebar|toc)", where) \
                and context.get(where, set()) & {"border-radius", "background", "background-color", "box-shadow"}:
            m = re.match(r"^([\d.]+)px", v)
            if m and float(m.group(1)) >= 3:
                out.append(find("accent-stripe", ln, "%s|%s" % (where, prop), "%s: %s in %s" % (prop, v, where)))
    if len(sizes) > FONT_SIZES_MAX:
        ln = sorted(sizes.items(), key=lambda kv: kv[1])[FONT_SIZES_MAX][1]
        out.append(find("type-scale", ln, "sizes:%d" % len(sizes),
                        "%d font sizes (%s)" % (len(sizes), ", ".join("%gpx" % s for s in sorted(sizes)))))
    if len(weights) > WEIGHTS_MAX:
        ln = sorted(weights.items(), key=lambda kv: kv[1])[WEIGHTS_MAX][1]
        out.append(find("type-scale", ln, "weights:%d" % len(weights),
                        "%d font weights (%s)" % (len(weights), ", ".join(str(w) for w in sorted(weights)))))
    return out


TW_SIZES = {"text-xs": 12, "text-sm": 14, "text-base": 16, "text-lg": 18, "text-xl": 20, "text-2xl": 24, "text-3xl": 30,
            "text-4xl": 36, "text-5xl": 48, "text-6xl": 60, "text-7xl": 72, "text-8xl": 96, "text-9xl": 128}
TW_WEIGHTS = {"font-thin": 100, "font-extralight": 200, "font-light": 300, "font-normal": 400, "font-medium": 500,
              "font-semibold": 600, "font-bold": 700, "font-extrabold": 800, "font-black": 900}
TW_SPACING = re.compile(r"^-?(p|px|py|pt|pr|pb|pl|ps|pe|m|mx|my|mt|mr|mb|ml|ms|me|gap|gap-x|gap-y|space-x|space-y)-\[([^\]]+)\]$")


def tailwind_decls(nodes):
    out = []
    for n in nodes:
        for t in tw(n):
            m = TW_SPACING.match(t)
            if m:
                g = m.group(1)
                prop = "padding" if g[0] == "p" else "margin" if g[0] == "m" else "gap"
                out.append((prop, m.group(2).replace("_", " "), n.line, "class %s" % t))
            elif t in TW_SIZES:
                out.append(("font-size", "%dpx" % TW_SIZES[t], n.line, "class %s" % t))
            elif t.startswith("text-[") and re.match(r"^text-\[[\d.]+(px|rem)\]$", t):
                out.append(("font-size", t[6:-1], n.line, "class %s" % t))
            elif t in TW_WEIGHTS:
                out.append(("font-weight", str(TW_WEIGHTS[t]), n.line, "class %s" % t))
    return out


# ---------- project spacing tokens ----------

TOKEN_DECL = re.compile(r"(--(?:space|spacing|gap|gutter|sp|stack|inset)(?:-[\w-]*)?)\s*:\s*([^;}{]+)")
ROOT_MARKERS = ("package.json", "pubspec.yaml", "Package.swift", ".git", "pyproject.toml", "deno.json")


def tokens_in(text):
    toks, base = set(), None
    for m in TOKEN_DECL.finditer(text or ""):
        v = px(m.group(2).strip())
        if v is None:
            continue
        if m.group(1) == "--spacing":
            base = v or None
        else:
            toks.add(v)
    for m in re.finditer(r"spacing\s*:\s*\{([^}]*)\}", text or ""):
        for vm in re.finditer(r"['\"]([\d.]+(?:px|rem))['\"]", m.group(1)):
            v = px(vm.group(1))
            if v is not None:
                toks.add(v)
    return toks, base


def project_root(path):
    d = os.path.dirname(os.path.abspath(path))
    home = os.path.expanduser("~")
    for _ in range(12):
        if any(os.path.exists(os.path.join(d, m)) for m in ROOT_MARKERS):
            return d
        parent = os.path.dirname(d)
        if parent == d or d == home:
            break
        d = parent
    return os.path.dirname(os.path.abspath(path))


def project_tokens(path):
    root = project_root(path)
    cache_file = os.path.join(STATE_DIR, "tokens.json")
    try:
        with open(cache_file) as fh:
            cache = json.load(fh)
    except Exception:
        cache = {}
    hit = cache.get(root)
    if hit and time.time() - hit.get("t", 0) < 300:
        return hit.get("toks", []), hit.get("base")
    toks, base, count = set(), None, 0
    skip = {"node_modules", ".git", "dist", "build", ".venv", "venv", "Pods", ".dart_tool", ".next", ".svelte-kit",
            "vendor", "coverage", ".cache"}
    for r, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in skip and not x.startswith(".")]
        for name in files:
            if not re.search(r"\.(css|scss|less|pcss)$|^tailwind\.config\.\w+$", name):
                continue
            count += 1
            if count > 400:
                break
            try:
                with open(os.path.join(r, name), encoding="utf-8", errors="replace") as fh:
                    t, b = tokens_in(fh.read(2000000))
                toks.update(t)
                base = base or b
            except OSError:
                pass
        if count > 400:
            break
    cache[root] = {"t": time.time(), "toks": sorted(toks), "base": base}
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(cache_file, "w") as fh:
            json.dump(cache, fh)
    except OSError:
        pass
    return sorted(toks), base


# ---------- Dart and Swift ----------

def _masked(src, lang):
    lits, comments = scan_literals(src, lang)
    spans = sorted([(a, b) for a, b, _, _ in lits] + comments)
    out, last = [], 0
    for a, b in spans:
        if a < last:
            continue
        out.append(src[last:a])
        out.append(re.sub(r"[^\n]", " ", src[a:b]))
        last = b
    out.append(src[last:])
    return "".join(out)


def _paren_end(s, i):
    depth = 0
    while i < len(s):
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(s)


def native_findings(src, path, lang, allowed, note):
    m_src = _masked(src, lang)
    lines = Lines(m_src)
    out = []
    card_re = r"\bCard(?:\.\w+)?\s*\(" if lang == "dart" else r"\bGroupBox\s*[({]"
    spans = []
    for m in re.finditer(card_re, m_src):
        start = m.end() - 1
        if m_src[start] == "(":
            end = _paren_end(m_src, start) + 1
            k = end
            while k < len(m_src) and m_src[k] in " \t\r\n":
                k += 1
            if lang == "swift" and k < len(m_src) and m_src[k] == "{":
                end = _match_brace(m_src, k, len(m_src))
        else:
            end = _match_brace(m_src, start, len(m_src))
        spans.append((m.start(), end))
    for a, b in spans:
        for c, d in spans:
            if a < c and d <= b:
                out.append(find("nested-card", lines.at(c), "%s>%s" % (lines.at(a), lines.at(c)),
                                "card on line %d inside the card on line %d" % (lines.at(c), lines.at(a))))
    prim_re = r"\b(FilledButton|ElevatedButton)(\.\w+)?\s*\(" if lang == "dart" else r"\.buttonStyle\(\s*\.borderedProminent\s*\)"
    prims = [lines.at(m.start()) for m in re.finditer(prim_re, m_src)]
    if len(prims) > 1:
        out.append(find("multiple-primary", prims[1], "%d" % len(prims), "%d primary buttons in this file" % len(prims), REPORT))
    decls = []
    if lang == "dart":
        for m in re.finditer(r"\bEdgeInsets(?:Directional)?\.(all|symmetric|only|fromLTRB|fromSTEB)\s*\(([^()]*)\)", m_src):
            for v in re.findall(r"(?<![\w.])(-?\d+(?:\.\d+)?)(?![\w.])", m.group(2)):
                decls.append(("padding", v + "px", lines.at(m.start()), "EdgeInsets.%s" % m.group(1)))
        for m in re.finditer(r"\bSizedBox\s*\(\s*(?:height|width)\s*:\s*(-?\d+(?:\.\d+)?)\s*,?\s*\)", m_src):
            decls.append(("gap", m.group(1) + "px", lines.at(m.start()), "SizedBox"))
        for m in re.finditer(r"\b(?:Gap|spacing:|runSpacing:)\s*\(?\s*(-?\d+(?:\.\d+)?)\b", m_src):
            decls.append(("gap", m.group(1) + "px", lines.at(m.start()), "spacing"))
        for m in re.finditer(r"\bfontSize\s*:\s*(\d+(?:\.\d+)?)", m_src):
            decls.append(("font-size", m.group(1) + "px", lines.at(m.start()), "TextStyle"))
        for m in re.finditer(r"\bFontWeight\.(w\d00|bold|normal)\b", m_src):
            w = {"bold": "700", "normal": "400"}.get(m.group(1), m.group(1)[1:])
            decls.append(("font-weight", w, lines.at(m.start()), "TextStyle"))
    else:
        for m in re.finditer(r"\.padding\(\s*(?:\.\w+|\[[^\]]*\])?\s*,?\s*(-?\d+(?:\.\d+)?)\s*\)", m_src):
            decls.append(("padding", m.group(1) + "px", lines.at(m.start()), ".padding"))
        for m in re.finditer(r"\bspacing\s*:\s*(-?\d+(?:\.\d+)?)", m_src):
            decls.append(("gap", m.group(1) + "px", lines.at(m.start()), "stack spacing"))
        for m in re.finditer(r"\.system\(\s*size\s*:\s*(\d+(?:\.\d+)?)", m_src):
            decls.append(("font-size", m.group(1) + "px", lines.at(m.start()), ".font"))
    out.extend(decl_findings(decls, allowed, note))
    return out


# ---------- entry point ----------

def lang_of(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in CSS_EXTS:
        return "css"
    return {".html": "html", ".htm": "html", ".vue": "html", ".svelte": "html", ".jsx": "jsx", ".tsx": "jsx",
            ".dart": "dart", ".swift": "swift"}.get(ext)


def _read(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read(2000000)
    except OSError:
        return None


def _template_trees(code, line_off):
    """HTML built in JS template literals, as separate trees."""
    trees = []
    if scan_literals is None:
        return trees
    lits, _ = scan_literals(code, "js")
    lines = Lines(code)
    for a, b, text, q in lits:
        if q == "`" and re.search(r"<[A-Za-z][^>]*>", text):
            trees.append(html_tree(text, lines.at(a) - 1 + line_off, embedded=True))
    return trees


def _styled_css(code, line_off, sheet):
    if scan_literals is None:
        return
    lits, _ = scan_literals(code, "js")
    lines = Lines(code)
    for a, b, text, q in lits:
        if q == "`" and re.search(r"(styled\.\w+|styled\([^)]*\)|\bcss|createGlobalStyle|\.attrs\([^)]*\))\s*$", code[max(0, a - 60):a]):
            sheet.add("x{%s}" % text.replace(PH, "0"), lines.at(a) - 1 + line_off)


def findings(src, path):
    lang = lang_of(path)
    if not lang or src is None:
        return []
    out = []
    sheet = Sheet()
    if lang == "css":
        sheet.add(src)
        allowed, note = spacing_allowed(path, src)
        return decl_findings([d for d in sheet.local], allowed, note)
    if lang in ("dart", "swift"):
        allowed, note = spacing_allowed(path, "")
        return native_findings(src, path, lang, allowed, note)
    base = os.path.dirname(os.path.abspath(path))
    roots, local_css = [], []
    if lang == "html":
        t = html_tree(src)
        roots.append(t.root)
        for css, off in t.css:
            sheet.add(css, off)
            local_css.append(css)
        for href in t.links:
            if not re.match(r"^[a-z]+:|^//", href):
                ext = _read(os.path.join(base, href.split("?")[0]))
                if ext:
                    sheet.add(ext, local=False)
        for off, code in t.scripts:
            roots.extend(tr.root for tr in _template_trees(code, off))
        component = path.lower().endswith((".vue", ".svelte"))
    else:
        roots.append(jsx_tree(src))
        _styled_css(src, 0, sheet)
        for m in re.finditer(r"""^\s*import\s+(?:[\w{}\s,*]+\s+from\s+)?["'](\.{1,2}/[^"']+\.(?:css|scss|less))["']""", src, re.M):
            ext = _read(os.path.join(base, m.group(1)))
            if ext:
                sheet.add(ext, local=False)
        roots.extend(tr.root for tr in _template_trees(src, 0))
        component = True
    allowed, note = spacing_allowed(path, "\n".join(local_css))
    nodes = []
    for r in roots:
        out.extend(tree_findings(r, sheet, component))
        nodes.extend(r.walk())
    inline = [(p, v, ln, sig(n)) for n in nodes for p, v, ln in n.style]
    out.extend(decl_findings(sheet.local + inline + tailwind_decls(nodes), allowed, note))
    return out


def cta_signatures(src, path):
    """Call-to-action bands in a file, for the cross-file check."""
    lang = lang_of(path)
    if lang not in ("html", "jsx"):
        return []
    root = html_tree(src).root if lang == "html" else jsx_tree(src)
    return [(n.line, s) for n, s in cta_bands(list(root.walk()))]
