---
name: plot-gallery
description: Maintain PLOTS.md, a live plot gallery the user keeps open in a markdown preview (e.g. VS Code), via this skill's gallery.py script. Load whenever you create, regenerate or delete a plot or figure (or a report/PDF worth looking at) in a project that has a gallery (a .plots.json at or above the working directory), when the user asks for a plot gallery, and when tidying up at the end of a task. Covers the commands, categories, captions, and pruning.
---

# plot-gallery

`PLOTS.md` is a single gallery of the plots worth looking at in a project.
The user keeps it open in a markdown preview beside their editor (in VS Code:
Cmd/Ctrl-K V, then "Markdown: Toggle Preview Locking"). The preview re-renders
on save and reloads images overwritten in place, so adding an entry is how a
plot gets in front of the user. It does not replace referencing plots by path
in your responses and write-ups.

**Never edit `PLOTS.md` or `PLOTS-archive.md` by hand.** Both are rendered
from `.plots.json` by `gallery.py` on every command. The script takes a file
lock, so concurrent sessions are safe.

## Finding the gallery

`gallery.py` lives in this skill's base directory (shown when the skill
loads); below, `$G` stands for its absolute path. It needs only Python 3.10+
(no dependencies): `python3 $G ...`.

The script uses `$PLOT_GALLERY_ROOT` if set, else the nearest directory at or
above the current one containing `.plots.json`. Run it from inside the
project. If there is no gallery:

- If the user asked for one, run `python3 $G init` at the project root (the
  repo root or the folder open in their editor) and tell them to open
  `PLOTS.md` in a preview.
- Otherwise don't create one; carry on as usual.

## Commands

```bash
# add (or update: re-adding a file replaces its old entry, wherever it was)
python3 $G add <path> [<path> ...] --task "<task>" --cat <Category> \
    --caption "<what it shows; what to notice>" [--note "<task description>"]

python3 $G task "<task>" --note "<one line: what question this task answers>"
python3 $G rm <path> [...]              # unpin (files stay on disk)
python3 $G clear "<task>"               # drop the task's Scratch entries
python3 $G clear "<task>" --cat all     # drop the whole task
python3 $G list
python3 $G init [--root DIR]            # create a gallery
```

Every command also tidies the gallery: entries whose files are gone are
dropped, and Scratch entries expire after 24h (`$PLOT_GALLERY_SCRATCH_TTL`,
e.g. `12h`, `3d`, `never`). So a session that is killed before cleaning up
leaves nothing behind for long. `prune --older DUR` / `prune --all [--drop]`
archive (or delete) whole tasks; those are mainly for the user, so only run
them when asked.

Paths may be absolute or relative to the current directory; they must be
files under the gallery root. Several paths in one `add` share one caption
(use for a set, e.g. one diagnostic per fit).

## When

- **Every plot you make**, including quick diagnostics: `add` it as soon as it
  is on disk, before describing it in your response. Batch a related set into
  one `add`.
- **Regenerated plot, same path:** `add` again with an updated caption (the
  image reloads by itself; the caption and time update).
- **Superseded or wrong plot:** `rm` it.
- **End of a task:** `clear "<task>"` to drop Scratch, `rm` diagnostics that
  only mattered mid-debugging. Keep everything referenced in a write-up.

## Tasks and categories

- `--task`: a sub-project or area plus a few words, e.g.
  `"sky · per-fibre LSF"`. Reuse the exact same string for the whole task
  (`list` shows existing ones). Set a one-line `--note` on the first `add`.
- Tasks are ordered by last activity; only the 5 most recently active stay in
  `PLOTS.md`, older ones move to `PLOTS-archive.md` automatically, and adding
  to an archived task brings it back.
- `--cat`, rendered in this order:
  - `Results` (default for images): figures carrying a finding.
  - `Comparisons`: truth vs fit, method A vs B, before/after.
  - `Diagnostics`: traces, corner plots, residuals, convergence checks.
  - `Scratch`: throwaway looks; cleared at end of task.
  - `Docs` (default for non-images): PDFs, reports, notes; rendered as links.
  Another name works but prints a note; mention it to the user if you needed one.

## Captions

Say what the plot shows *and* what to notice, so it makes sense a week later
without the conversation: "Residual map after the LSF fix: residuals < 2%
except the two edge fibres", not "residuals".

## In your response

Still reference each plot by path next to the claim it supports, and mention
"added to PLOTS.md" once per batch. Look at each image yourself before
describing it. Don't open files on screen; the gallery is how they're shown.
