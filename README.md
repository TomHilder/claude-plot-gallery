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
2. Open `PLOTS.md` in a markdown preview. In VS Code: open the file, press
   Cmd/Ctrl-K V, then run **Markdown: Toggle Preview Locking** so the preview
   stays on the gallery when you open other markdown files.
3. Work as usual. Claude adds every plot it makes, updates entries when it
   regenerates a plot, and clears throwaway plots at the end of a task.

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
| `check` | drop entries whose files no longer exist |
| `list` | print the gallery |
| `init [--root DIR]` | create a gallery |

Categories: Results, Comparisons, Diagnostics, Scratch, Docs. Images render
inline; other files (PDFs, reports) render as links. Only the five most
recently active tasks stay in `PLOTS.md`; older ones move to
`PLOTS-archive.md`.

If your project is a git repo, you will probably want `.plots.json`,
`.plots.lock`, `PLOTS.md` and `PLOTS-archive.md` in `.gitignore`.

## License

MIT
