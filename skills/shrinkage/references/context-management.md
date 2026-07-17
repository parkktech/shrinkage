# Context management for long runs

A `--auto` shave over a big backlog, or a deep audit, can fill the context
window. Shrinkage is built to handle this cleanly because **its durable state
is on disk, not in the conversation**:

- **git** holds every completed transform (one atomic commit each).
- **SHRINK-PLAN.md** holds what's left (open rows) and what's done (struck /
  Done section), re-stamped after each item.
- **the codemap** holds the repo's symbols.

So a `/clear` or `/compact` mid-run loses *nothing* — re-running the command
re-reads the plan and continues. Conversation context is scratch space, not
state. Design every long loop around that fact.

## Monitor

During an `--auto` loop (and any long sequence), watch two things:

1. **Item budget** (deterministic): `auto_max_items` in settings caps how many
   items one run processes (default 8). Predictable, no guesswork.
2. **Context pressure** (adaptive): if the harness signals the context window
   is getting full (low-context warning, or `/context` shows past the
   `auto_context_stop` percent — default 75%), treat it as a stop condition.

## Checkpoint & stop (never mid-transform)

When a stop condition hits, **finish the current atomic item first** (or revert
it if incomplete — an in-flight transform is never left half-applied), ensure
SHRINK-PLAN.md reflects reality (done rows struck, `map-fp` re-stamped), then
STOP and report: items done this run, cumulative net LOC, and the resume line.

## Clear & resume

Tell the user, verbatim, how to continue:

> Context is filling. Progress is committed and SHRINK-PLAN.md is up to date.
> Run **`/clear`** (or `/compact`), then **`/srk:shave --auto`** to resume —
> it picks up from the remaining open plan items. Nothing is lost.

Prefer `/clear` for a clean slate on a fresh batch; `/compact` if you want to
keep the conversation thread. Either is safe. On resume, the map refreshes at
task start and the plan's open rows are the worklist — no re-audit needed
unless the plan reads stale (code moved on).

## PreCompact breadcrumb

The plugin ships a PreCompact hook that writes the resume state into the
compaction summary (`shrinkage: N/M plan items done · resume /srk:shave
--auto`), so even an *automatic* compaction mid-run leaves the next context
knowing exactly where to continue.

## Audit is naturally context-light

`/srk:audit` fans work out to read-only subagents (each its own context) and
keeps only their structured findings on the main thread — so auditing a huge
repo doesn't itself blow context. The shave loop is where budgeting matters.
