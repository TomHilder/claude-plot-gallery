#!/usr/bin/env python3
"""A live plot gallery: a markdown file listing the plots worth looking at.

The gallery's state lives in ``.plots.json`` at the gallery root; ``PLOTS.md``
(live tasks) and ``PLOTS-archive.md`` (archived tasks) are rendered from it on
every command, so never edit the markdown by hand.

The gallery root is ``$PLOT_GALLERY_ROOT`` if set, otherwise the nearest
directory at or above the current one that contains ``.plots.json``. Create
one with ``gallery.py init``.

Examples
--------
    gallery.py init                                 # gallery in the current directory
    gallery.py add figs/resid.png --task "sky · LSF fix" \\
        --cat Results --caption "Residuals < 2% except edge fibres"
    gallery.py add a.png b.png c.png --task ... --cat Diagnostics --caption ...
    gallery.py task "sky · LSF fix" --note "Does the per-fibre LSF fix the wings?"
    gallery.py rm figs/resid.png
    gallery.py clear "sky · LSF fix"                # drops its Scratch entries
    gallery.py clear "sky · LSF fix" --cat all      # drops the whole task
    gallery.py check                                # drop entries whose files are gone
    gallery.py list
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = STATE = LOCK = GALLERY = ARCHIVE = Path()

CATEGORIES = ["Results", "Comparisons", "Diagnostics", "Scratch", "Docs"]
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
KEEP_LIVE = 5

HEADER = """# Plots

Live gallery of plots worth looking at, most recently active task first.
Rendered from `.plots.json` by the plot-gallery skill's `gallery.py`;
don't edit by hand. Older tasks move to `PLOTS-archive.md`.
"""

ARCHIVE_HEADER = """# Plots archive

Tasks moved out of `PLOTS.md`, most recently active first. Rendered from
`.plots.json`; don't edit by hand.
"""


def set_root(root: Path) -> None:
    global ROOT, STATE, LOCK, GALLERY, ARCHIVE
    ROOT = root.resolve()
    STATE = ROOT / ".plots.json"
    LOCK = ROOT / ".plots.lock"
    GALLERY = ROOT / "PLOTS.md"
    ARCHIVE = ROOT / "PLOTS-archive.md"


def find_root() -> Path | None:
    if env := os.environ.get("PLOT_GALLERY_ROOT"):
        return Path(env).expanduser()
    here = Path.cwd().resolve()
    for d in (here, *here.parents):
        if (d / ".plots.json").is_file():
            return d
    return None


def now() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def rel(path: str) -> str:
    p = Path(path).expanduser()
    p = (Path.cwd() / p) if not p.is_absolute() else p
    p = p.resolve()
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        sys.exit(f"error: {p} is outside {ROOT}")


@contextlib.contextmanager
def state():
    """Load the state under an exclusive lock, then save and re-render."""
    with open(LOCK, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = json.loads(STATE.read_text()) if STATE.exists() else {"tasks": []}
        yield data
        archive_old(data)
        write_atomic(STATE, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        write_atomic(GALLERY, render(data, archived=False))
        write_atomic(ARCHIVE, render(data, archived=True))


def write_atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def find_task(data: dict, name: str) -> dict | None:
    for t in data["tasks"]:
        if t["name"] == name:
            return t
    return None


def ensure_task(data: dict, name: str) -> dict:
    t = find_task(data, name)
    if t is None:
        t = {"name": name, "note": "", "created": now(), "updated": now(),
             "archived": False, "entries": []}
        data["tasks"].append(t)
    return t


def find_entry(data: dict, path: str) -> tuple[dict, dict] | None:
    for t in data["tasks"]:
        for e in t["entries"]:
            if path in e["paths"]:
                return t, e
    return None


def archive_old(data: dict) -> None:
    live = sorted((t for t in data["tasks"] if not t["archived"]),
                  key=lambda t: t["updated"], reverse=True)
    for t in live[KEEP_LIVE:]:
        t["archived"] = True
    data["tasks"] = [t for t in data["tasks"] if t["entries"] or t["note"]]


def md_dest(path: str) -> str:
    return f"<{path}>"


def fmt_time(ts: str, day: str) -> str:
    d = datetime.fromisoformat(ts)
    return d.strftime("%H:%M") if d.date().isoformat() == day else d.strftime("%m-%d %H:%M")


def render_entry(e: dict, day: str) -> str:
    lines = []
    for p in e["paths"]:
        if Path(p).suffix.lower() in IMAGE_EXTS:
            lines.append(f"![{e['caption']}]({md_dest(p)})")
        else:
            lines.append(f"[{Path(p).name}]({md_dest(p)})")
    missing = [p for p in e["paths"] if not (ROOT / p).exists()]
    flag = " · **missing file**" if missing else ""
    body = "\n\n".join(lines)
    return f"{body}\n\n*{e['caption']}* · `{fmt_time(e['updated'], day)}`{flag}"


def render(data: dict, archived: bool) -> str:
    out = [ARCHIVE_HEADER if archived else HEADER]
    tasks = sorted((t for t in data["tasks"] if t["archived"] == archived),
                   key=lambda t: t["updated"], reverse=True)
    for t in tasks:
        day = t["updated"][:10]
        out.append(f"---\n\n## {t['name']} · {day}\n")
        if t["note"]:
            out.append(t["note"] + "\n")
        cats = CATEGORIES + sorted({e["cat"] for e in t["entries"]} - set(CATEGORIES))
        for c in cats:
            es = sorted((e for e in t["entries"] if e["cat"] == c),
                        key=lambda e: e["updated"], reverse=True)
            if not es:
                continue
            out.append(f"### {c}\n")
            out.extend(render_entry(e, day) + "\n" for e in es)
    return "\n".join(out)


def cmd_add(a) -> None:
    paths = [rel(p) for p in a.paths]
    for p in paths:
        if not (ROOT / p).is_file():
            sys.exit(f"error: {p} is not an existing file")
    cat = a.cat or ("Docs" if all(Path(p).suffix.lower() not in IMAGE_EXTS for p in paths)
                    else "Results")
    if cat not in CATEGORIES:
        print(f"note: new category {cat!r} (standard: {', '.join(CATEGORIES)})")
    with state() as data:
        task = ensure_task(data, a.task)
        task["archived"] = False
        if a.note:
            task["note"] = a.note
        verb = "added"
        for p in paths:  # re-adding a file replaces whatever entry held it
            while (hit := find_entry(data, p)) is not None:
                t, e = hit
                t["entries"].remove(e)
                verb = "updated"
        task["entries"].append({"paths": paths, "cat": cat, "caption": a.caption,
                                "updated": now()})
        task["updated"] = now()
    print(f"{verb}: {', '.join(paths)} → {a.task} / {cat}")


def cmd_task(a) -> None:
    with state() as data:
        t = ensure_task(data, a.task)
        t["note"] = a.note
        t["archived"] = False
        t["updated"] = now()
    print(f"task: {a.task}")


def cmd_rm(a) -> None:
    with state() as data:
        for raw in a.paths:
            p = rel(raw)
            hit = find_entry(data, p)
            if hit is None:
                print(f"not in gallery: {p}")
                continue
            t, e = hit
            e["paths"].remove(p)
            if not e["paths"]:
                t["entries"].remove(e)
            print(f"removed: {p}")


def cmd_clear(a) -> None:
    with state() as data:
        t = find_task(data, a.task)
        if t is None:
            sys.exit(f"error: no task {a.task!r}")
        if a.cat == "all":
            data["tasks"].remove(t)
            print(f"dropped task: {a.task}")
        else:
            n = len(t["entries"])
            t["entries"] = [e for e in t["entries"] if e["cat"] != a.cat]
            print(f"cleared {n - len(t['entries'])} {a.cat} entries from {a.task}")


def cmd_check(a) -> None:
    with state() as data:
        for t in data["tasks"]:
            for e in list(t["entries"]):
                gone = [p for p in e["paths"] if not (ROOT / p).exists()]
                for p in gone:
                    print(f"missing, removed: {p}")
                    e["paths"].remove(p)
                if not e["paths"]:
                    t["entries"].remove(e)


def cmd_list(a) -> None:
    data = json.loads(STATE.read_text()) if STATE.exists() else {"tasks": []}
    for t in sorted(data["tasks"], key=lambda t: t["updated"], reverse=True):
        tag = " [archived]" if t["archived"] else ""
        print(f"{t['name']}{tag}")
        for e in t["entries"]:
            print(f"  {e['cat']:<12} {', '.join(e['paths'])}")


def cmd_init(a) -> None:
    if STATE.exists():
        print(f"gallery already exists: {GALLERY}")
        return
    with state():
        pass
    print(f"created {GALLERY} (state in {STATE})")


def cmd_render(a) -> None:
    with state():
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="create a gallery here (or at --root)")
    p.add_argument("--root", default=".")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("add", help="add or update an entry (one caption, 1+ files)")
    p.add_argument("paths", nargs="+")
    p.add_argument("--task", required=True, help="e.g. 'lvm/sky · LSF fix'")
    p.add_argument("--caption", required=True, help="what it shows and what to notice")
    p.add_argument("--cat", help=f"one of {CATEGORIES}; default Results (Docs for non-images)")
    p.add_argument("--note", help="set the task's one-line description")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("task", help="create a task or set its description")
    p.add_argument("task")
    p.add_argument("--note", required=True)
    p.set_defaults(func=cmd_task)

    p = sub.add_parser("rm", help="remove files from the gallery (files stay on disk)")
    p.add_argument("paths", nargs="+")
    p.set_defaults(func=cmd_rm)

    p = sub.add_parser("clear", help="drop a task's category (default Scratch) or 'all'")
    p.add_argument("task")
    p.add_argument("--cat", default="Scratch")
    p.set_defaults(func=cmd_clear)

    sub.add_parser("check", help="remove entries whose files no longer exist"
                   ).set_defaults(func=cmd_check)
    sub.add_parser("list", help="print the gallery contents").set_defaults(func=cmd_list)
    sub.add_parser("render", help="re-render the markdown from state"
                   ).set_defaults(func=cmd_render)

    a = ap.parse_args()
    if a.cmd == "init":
        set_root(Path(a.root))
    else:
        root = find_root()
        if root is None:
            sys.exit("error: no .plots.json here or in any parent directory; "
                     "run `gallery.py init` at the project root or set PLOT_GALLERY_ROOT")
        set_root(root)
    a.func(a)


if __name__ == "__main__":
    main()
