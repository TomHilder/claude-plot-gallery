# claude-plot-gallery

A Claude Code skill that keeps a live gallery of the plots it makes.

When Claude makes plots during a task, they end up scattered across the file
system and mentioned by path in the scrollback. With this skill, Claude pins
each plot to a single `PLOTS.md` file, grouped by task and category, with a
caption saying what to notice. You keep that file open in a markdown preview
next to your editor and watch plots appear as they are made.

```
## sky · per-fibre LSF · 2026-11-12

Does the per-fibre LSF fix the line wings?

### Results
[residual map image]
Residual map after the LSF fix: residuals < 2% except the two edge fibres · 14:32

### Diagnostics
[trace plots]
...
```

## Install

In Claude Code:

```
/plugin marketplace add TomHilder/claude-plot-gallery
/plugin install plot-gallery@claude-plot-gallery
```

Or copy `skills/plot-gallery/` into `~/.claude/skills/` (all projects) or a
project's `.claude/skills/`.

Needs Python 3.10+ on `PATH` as `python3`. No other dependencies.

## Use

1. Ask Claude to set up a plot gallery in your project (or run
   `python3 skills/plot-gallery/gallery.py init` at the project root
   yourself). This creates `PLOTS.md`, `PLOTS-archive.md` and `.plots.json`.
2. Open `PLOTS.md` in a **locked** markdown preview (see below), so it stays
   on the gallery when you open other markdown files.
3. Work as usual. Claude adds every plot it makes, updates entries when it
   regenerates a plot, and clears throwaway plots at the end of a task.

### Keeping the gallery open in VS Code

A normal markdown preview follows whichever markdown file is active, so it
jumps away from the gallery as soon as you open another `.md`. Lock it:

- With `PLOTS.md` focused, run **Markdown: Open Locked Preview to the Side**
  from the command palette. Or open a preview with Cmd/Ctrl-K V, click into
  it, and run **Markdown: Toggle Preview Locking**. A locked preview's tab
  reads **[Preview] PLOTS.md**.
- Other markdown files can still be previewed: Cmd/Ctrl-K V on them opens a
  second, normal preview alongside the locked gallery.
- To keep the gallery out of the way, drag it into its own editor group, or
  right-click its tab and choose **Move into New Window** (e.g. for a second
  screen).
- If VS Code restores the preview unlocked after a restart, lock it again.

The preview re-renders when `PLOTS.md` changes and reloads images that are
overwritten in place, so it never needs to be closed and reopened.

The skill only activates in projects that have a gallery (a `.plots.json` at
or above the working directory), so it stays out of the way elsewhere.

To make Claude use it consistently, a line in your project's `CLAUDE.md`
helps, e.g. *"Add every plot you make to the plot gallery (plot-gallery
skill)."*

## How it works

`.plots.json` holds the gallery: tasks, each with entries (files, category,
caption, timestamp). `gallery.py` edits it and re-renders the markdown on
every command, under a file lock so parallel sessions don't clash:

| command | does |
| --- | --- |
| `add PATH... --task T --caption C [--cat K] [--note N]` | add or update an entry |
| `task T --note N` | set a task's one-line description |
| `rm PATH...` | remove entries (files stay on disk) |
| `clear T [--cat K\|all]` | drop a task's Scratch entries, a category, or the task |
| `prune [--older DUR \| --all] [--drop]` | archive (or delete) idle or all live tasks |
| `list` | print the gallery |
| `init [--root DIR]` | create a gallery |

Every command also tidies, so sessions that are killed before cleaning up
don't leave clutter: entries whose files are gone are dropped, and Scratch
entries expire after `$PLOT_GALLERY_SCRATCH_TTL` (default `24h`; e.g. `12h`,
`3d`, `never`).

To clear the gallery yourself from inside Claude Code, run it with `!`, e.g.
`! python3 <path-to>/gallery.py prune --all`. A shell alias makes that
shorter: `alias gallery='python3 <path-to>/skills/plot-gallery/gallery.py'`.

Categories: Results, Comparisons, Diagnostics, Scratch, Docs. Images render
inline; other files (PDFs, reports) render as links. Only the five most
recently active tasks stay in `PLOTS.md`; older ones move to
`PLOTS-archive.md`.

If your project is a git repo, you will probably want `.plots.json`,
`.plots.lock`, `PLOTS.md` and `PLOTS-archive.md` in `.gitignore`.

## License

MIT
