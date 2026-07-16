# Workflow: Map

<objective>
Produce and maintain the codemap — the token-lean symbol index every other
workflow orients from. The map replaces repo-wide exploration: one ~4k-token
read instead of 15k–40k tokens of greps and file dumps per task.
</objective>

<process>
1. **Resolve locations.** $SKILL = the shrinkage skill directory. Map default:
   `.claude/codemap.txt`, or `.planning/intel/codemap.txt` when `.planning/`
   exists (GSD project — the scripts detect this automatically).

2. **Refresh.** `python $SKILL/scripts/codemap.py refresh` — no-op when
   current (mtime-based), full rebuild otherwise. Run this at the START of
   every coding task; it costs nothing when the map is fresh.

3. **First build in a repo (interactive only):** ask the user once — commit
   the map (team-shared, needs refresh discipline) or keep it gitignored
   (default; always rebuilt fresh)? Record as `commit_map` in
   `.claude/shrinkage.json`. Unattended sessions take the default silently.

4. **Read the build report.** It prints: file/symbol counts, estimated map
   tokens, files collapsed to fit budget, detected languages, and the exact
   `rules/<lang>.md` paths to load. Load the rules for languages the task
   touches — they are part of the map step, not an optional extra.

5. **Size to the repo.**
   - Map over budget with many collapsed files → raise `budget` in settings,
     or work scoped: `codemap.py scope <dir>` builds a standalone deep map
     for one subtree (monorepos: scope to the project you're changing).
   - Repo has unsupported languages → they're listed as unmapped; add an
     adapter (two files — see SKILL.md "Growing to a new language") or
     accept grep-based work for those files.

6. **GSD sync.** In a GSD project the build also syncs every symbol into
   `.planning/intel/api-map.json` (`_meta.generator: shrinkage`). This feeds
   GSD's `plan_review.source_grounding_authority: intel` and API-SURFACE.md
   for every mapped language. Nothing to do manually — verify the "gsd intel
   synced" line appears.

7. **Trust but verify staleness.** The map is a snapshot. Before acting on a
   surprising map fact (a symbol that should exist and doesn't), re-run
   `refresh` and re-query before concluding anything.
</process>

<success_criteria>
- [ ] Map exists at the correct location and `refresh` reports current
- [ ] Language rules for the task's languages have been read
- [ ] Map tokens within budget, or scoping decision made consciously
- [ ] GSD project → api-map.json sync confirmed
- [ ] commit-vs-ignore decision recorded (first run only)
</success_criteria>
