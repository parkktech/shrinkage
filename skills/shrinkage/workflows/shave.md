# Workflow: Shave

<objective>
Execute a subtraction pass — remove or consolidate code the repo no longer
needs — with zero behavior change, following the safety model to the letter.
Deleting is part of the feature; this workflow is how deletion earns trust.
</objective>

<required_reading>
`references/safety-model.md` (the whole thing — especially §0 Zeroth Law,
§3 evidence chain, §6 transformation protocol) and
`references/consolidation-catalog.md` for the transforms in play.
</required_reading>

<process>
0. **Dry-run mode (v0.8).** If invoked with `--dry-run`: execute steps 1–4
   fully (scope, baseline check, hunt, tier + evidence), then produce the
   complete transform plan — per candidate: catalog entry, tier, evidence
   chain, the exact edit intended, expected net LOC — and STOP. No file is
   modified, no commit made. This is the review artifact before letting the
   surgeon loose.

1. **Scope.** The target argument is one of:
   - **a SHRINK-PLAN.md item number** (`1`, `3`, or `#3`) — execute exactly
     that plan entry: its file(s) are the scope, its catalog entry and
     evidence come pre-loaded from the plan (re-verify per §3 anyway);
   - **`--auto`** (alias: `all`) — **keep going until done**: work the whole
     backlog top-to-bottom, unattended, one gated commit per item (batch loop
     below). The answer to "why doesn't it do the whole project?";
   - **a directory or file path** — hunt within it;
   - **nothing** — the files in `git diff --name-only HEAD` (riding along
     with a feature change).
   A number/`--auto` with no SHRINK-PLAN.md present → say so and suggest
   `/srk:audit` first. Keep a single-item shave scoped — a repo-wide *hunt* is
   the audit workflow's job.

   **Dirty targets (default: SKIP).** Before executing any item, run
   `git status --porcelain -- <target file(s)>`. Non-empty → the file carries
   the user's uncommitted work: SKIP the item and list it in the completion
   report as "blocked on your uncommitted work — commit/stash, then re-audit."
   Never shave a file with unrelated dirty changes — that's exactly the
   WIP-sweep incident (§7). Opt-in exception **`--allow-dirty-disjoint`**: only
   when the audit verified the dirty hunk is DISJOINT from the shave region, use
   the scripted park/unpark so the user's hunk is never entangled or lost —
   `python3 $SKILL/scripts/dirty_apply.py park <file>` → apply the shave on the
   clean base → `safe_commit.py -- <file>` → `dirty_apply.py unpark <file>`
   (re-applies the user hunk; on overlap it aborts and restores the exact
   pre-shave file, and you revert the shave commit). Never hand-roll hunk
   staging.

   ### Interactive vs --auto
   - **Single item / bare** (no `--auto`): do the ONE item, then **prompt for
     the next** — end with "next up: #N `<candidate>` (Tstier, ~N LOC) —
     `/srk:shave N`, or `/srk:shave --auto` to run the rest." One reviewable
     step at a time; you stay in the loop.
   - **`--auto`**: don't prompt between items — keep going until a stop
     condition. This is the "set it running on the backlog" mode.

   ### Batch loop (`--auto`)
   Process every OPEN plan item in ranked order, each as its own gated commit —
   throughput without giving up the per-commit safety guarantee:

   ```
   for each open item, highest rank first:
     if item.tier is T2/T3 or plan-routed-as-a-phase:
         if NOT --dangerous:       STOP — needs your judgment (report, halt)
         else (--dangerous):       proceed (remove public surface directly;
                                   no deprecation cycle — the accepted risk)
     if auto_max_items set and reached:  STOP (optional review checkpoint)
     dispatch the item to a fresh srk-surgeon subagent (see below): it
       re-verifies evidence, gates, applies ONE transform, runs tests, commits,
       marks the plan row done, returns a one-line result
     if it returned RED/reverted:  STOP (even in --dangerous — you cannot verify
                                   against a red suite; a break means the plan's
                                   assumptions are off)
   ```

   `--auto` runs **until done** — it halts on the first T2/T3 item, the first
   red gate, an empty backlog, or an optional `auto_max_items` review cap
   (default 0). Never a whole-repo rampage of *unreviewed* commits: each is
   atomic and `git revert`-able, and on a production codebase you review the
   batch before pushing. Report cumulative net LOC, a per-item line (done /
   reverted), and what stopped it.

   ### Communicate the halt clearly (this is NOT a failure)
   0 transforms with a drained T0/T1 backlog is the tool working, not breaking.
   When `--auto` halts, say so plainly with a report the user can act on:

   ```
   --auto complete for the safe backlog.
     done this session: <n> items, <net LOC>    total: <N>/<M> plan items
     stopped at: #<k> <candidate> — <why: T2 public surface / planned phase>
     remaining (<r>): all need your judgment —
       #k <candidate> (T2, ~<LOC>) — <recommended: confirm / deprecation cycle>
       ...
   To continue:
     • /srk:shave <k>            — confirm this one (deprecation cycle for T2)
     • /srk:shave --auto --dangerous  — execute ALL remaining autonomously
                                        (removes public surface directly; each
                                        commit still tested + revertible)
     • /gsd-plan-phase           — for a plan-routed big merge
   ```

   Lead with what got DONE and that it's safe-drained — never a bare "0
   transforms, nothing to do" that reads like a bug.

   **After `--full-send` specifically:** it already went THROUGH T2/public
   surface, so anything still open is something autonomy must NOT do on its own —
   a target dirty with the user's uncommitted work, a red/absent baseline, or a
   behavior-divergence adjudication. Frame it as COMPLETION: "full-send done —
   everything I can safely execute is committed." List each leftover with the
   reason it needs the USER (commit/stash in-flight work → re-audit unblocks
   dirty targets; decide which behavior is correct for adjudications). Do NOT end
   with a bare `/srk:shave <n>` as if more autonomous shaving is pending — it
   isn't; the leftovers are blocked on a human decision or a prerequisite.

   ### --dangerous ("full send") — explicit escape hatch
   `/srk:shave --auto --dangerous` (alias `--full-send`) proceeds through T2 and
   public-surface items without stopping for confirmation. What it KEEPS (the
   free safety, never dropped): one atomic commit per item, tests green before
   and after or auto-revert, evidence re-verified, and a **hard stop on a red or
   absent test suite** — "revertible" is only meaningful with a green baseline.
   What it DROPS: the human-confirmation halt and the deprecation cycle — it
   removes public methods/interfaces directly. The real risk it accepts:
   **external consumers of your public API aren't covered by your tests**, so a
   direct removal can break callers outside the repo. Use only when you own or
   control all consumers. Refused when `allow_dangerous: false` in settings
   (team kill-switch). Open the run with a loud one-line banner naming the risk
   and the item count, then go.

   ### Keep the main context flat — dispatch each item to a subagent
   The way `--auto` runs the whole backlog WITHOUT needing a manual `/clear`:
   run each item's work (re-verify evidence → gate → apply one transform →
   tests → commit → mark the plan row done) inside a **fresh `srk-surgeon`
   subagent** (economy: it's the cheap model, and the test gate guarantees
   safety). The subagent returns one line — `done: <item> | <net LOC> | <sha>`
   or `reverted: <what broke>`. The main orchestrator holds only the plan and
   the running tally, so its context stays nearly flat no matter how many items
   run. A 50-item backlog completes in one session; **no manual clear needed.**
   High-stakes (T1 touching shared code) items also get an `srk-verifier`
   subagent before the loop moves on.

   ### Context is a fallback, not the normal stop
   Because per-item work is offloaded, the main context rarely fills. If it
   still does (very long run, or subagents unavailable so work ran inline),
   the durable-state safety net kicks in: state is on disk (git +
   SHRINK-PLAN.md), so finish the current atomic item, confirm the plan is
   current, and either let Claude Code auto-compact (the PreCompact hook leaves
   a resume breadcrumb and the loop continues) or, if you prefer a clean batch,
   tell the user:

   > Progress committed, SHRINK-PLAN.md current. `/clear` then `/srk:shave
   > --auto` resumes from the remaining items — nothing lost.

   Manual `/clear` is thus optional (a fresh-batch/review convenience), never
   required. Read `references/context-management.md`.

2. **Baseline.** Relevant test suite green. Red baseline → stop and report;
   you cannot detect breakage against a red baseline.

3. **Hunt, using signals in this order (cheap → expensive):**
   - `codemap.py refresh` then scan the target's symbols for `x0` refs (C6
     candidates) and one-method classes (C7)
   - `codemap.py dupes` scoped output for same-name / similar-signature
     groups (C1, C9)
   - read the target files once, flagging: dead branches & expired flags
     (C4), pass-through wrappers (C2), single-implementer abstractions (C3),
     switch ladders (C8), comment noise (C10), hand-rolled platform features
     (C5)

4. **Tier every candidate** (safety-model §2). T0 → proceed. T1 → build the
   full evidence chain (§3) including the language's dynamic-reference
   checklist from `rules/<lang>.md`, AND run
   `coverage_check.py <target files>` — unreported/low-coverage targets
   auto-escalate to T2 unless you write characterization tests first
   (safety-model §4). T2 → do NOT execute; record in the report with
   evidence and the recommended deprecation-cycle plan. T3 → not a shave;
   route to the normal gate/plan flow.

5. **Execute, one transform per commit,** per the transformation protocol
   (§6). First **activate the staging guard** for the run:
   `mkdir -p .claude && touch .claude/srk-shave-active` — a PreToolUse hook then
   rejects broad `git add -A` / `git commit -a` until you clear it. Then per
   candidate: apply one catalog entry → gates green → **commit through the
   staging guard**: `python3 $SKILL/scripts/safe_commit.py -m "<evidence msg>"
   -- <your files>` (stages + commits only those paths and verifies nothing else
   landed) → next. Any red → revert that transform fully, record the hidden
   dependency you just discovered in the report. When the run ends OR halts,
   `rm -f .claude/srk-shave-active` so normal work isn't guarded afterward. **Economy:** spawn the
   `srk-surgeon` agent to apply each transform — it runs on the cheap model
   (the what/how is already decided here), with the test gate guaranteeing
   safety. Reserve the capable model for the analysis (this workflow) and the
   `srk-verifier` pass.

6. **Compatibility check per transform:** old entry points on the surface
   keep working (deprecation shims where needed, marked and scheduled). Every
   shim created gets a line in **DEPRECATIONS.md** at the repo root:
   `- [ ] <old entry point> -> <replacement> (remove <date/release>)`. The
   trend report nags about unchecked entries, so shims can't accumulate
   silently forever — check the box when the shim is finally removed.

7. **Score.** `python3 $SKILL/scripts/diffstat.py` — the shave should read
   net-negative in app LOC with test LOC steady or up (characterization tests
   added count as investment, not weight). Report the scoreboard line and, in
   a GSD project, put it in the plan SUMMARY.md.

8. **Update SHRINK-PLAN.md** so it stays current: mark each executed item done
   (strike the row with `~~...~~` or move it to a `## Done` section — the
   startup line counts unstruck `| N |` rows as open), append reverted
   attempts to `## Hidden dependencies discovered`, and re-stamp `map-fp` to
   the post-shave fingerprint so the plan doesn't read as stale from your own
   changes.

9. **Report:** transforms executed (catalog # + tier + net LOC each), T2
   candidates escalated with evidence, reverted attempts and what they
   revealed, suite status, and remaining open plan items.
</process>

End with a terse result line + a **Next** menu of 1-3 `/srk:` commands (see the command file's <next> block). No wall of prose.

<success_criteria>
- [ ] Suite green before, after every transform, and at the end
- [ ] One atomic commit per transform, evidence template in each message
- [ ] No T2 executed without human confirmation; escalations documented
- [ ] Compatibility surface intact (shims in place where required)
- [ ] Net app LOC negative (or every exception justified in the report)
- [ ] Test LOC not reduced to flatter the score
</success_criteria>
