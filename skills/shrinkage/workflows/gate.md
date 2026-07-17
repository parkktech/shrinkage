# Workflow: Reuse Gate

<objective>
Decide — before any code is written — what will be EXTENDED to achieve the
task, so new code is the justified exception rather than the default. The gate
is where shrinkage happens *preventively*: growth stopped at the door costs
nothing to remove later.
</objective>

<process>
0. **Size the gate (context economy).** Not every change deserves the full
   ceremony. Take the **lite path** when the change is small and low-risk
   (roughly: ≤ ~15 expected lines, at most one new symbol, not touching the
   compatibility surface) OR when the codemap is tiny (< ~30 symbols — a
   near-empty repo has nothing to reuse): one `codemap.py query` for the
   obvious owner symbol, name it, record the gate (step 7), proceed. Full
   ceremony (steps 1–6) for everything larger, and always when the map flags a
   likely duplicate. Don't re-read `rules/<lang>.md` if already loaded this
   session, and do NOT load `safety-model.md` here — that's for deletions
   (shave/audit), not for adding code.

1. **Prepare.** Map current (workflow: map). Language rules loaded (once per
   session). Task stated in one sentence — if you can't state it in one
   sentence, split it.

2. **Harvest candidates.** Query the map for the task's domain nouns AND verbs
   (`codemap.py query invoice`, `query export`, `query notify`). Cast wide:
   synonyms, singular/plural, the framework's vocabulary. Collect 2–5
   candidate symbols with their signatures and ref counts.

2b. **Platform sweep (Composer projects).** Before concluding new code is
   needed, search the vendor surface: `codemap.py vendor <term>` (reads
   Composer's prebuilt classmap — cheap even on a 60k-class Magento install;
   `--deep` lists a match's methods). A framework class that already does the
   job beats every rung of the ladder — calling code you don't own is the
   ultimate shrink. When a framework was detected (build output names it),
   its `rules/frameworks/<fw>.md` seams govern HOW to extend: Laravel macros/
   listeners, Magento plugins/observers, Drupal alters/decorators — not new
   parallel classes.

3. **Judge each candidate** — write one line per candidate, no skipping:
   - **extend** — name the ladder rung (parameter? branch? new method on it?)
   - **not applicable because X** — X must be a *fact* (wrong layer, different
     lifecycle, would couple two change-reasons), not a vibe ("feels off").

4. **Walk the extension ladder** for the chosen approach — stop at the first
   rung that achieves the goal:
   1. value/config change
   2. parameter with a safe default ← the Zeroth Law rung: defaults preserve
      every existing call site's behavior
   3. extend a method body
   4. method on an existing class
   5. function in an existing module
   6. class in an existing file
   7. new file — one-line justification required
   8. new module/package — one-line justification required

   `gate: "hard"` in settings → rungs 7–8 additionally need explicit user
   confirmation before implementation. Soft gate (default) → the stated
   justification suffices, but it must be stated BEFORE the code exists.

5. **Justification quality bar** (rungs 7–8): survives the three checks in
   `references/extend-vs-add.md` §4 — no owning symbol exists, or extension
   couples two change-reasons (name them), or the target is past cohesion
   limit and the plan includes splitting it. "It felt cleaner" fails the bar.

6. **Check the catalog in reverse.** Would this plan create a C1 (near-dup
   sibling), C2 (wrapper), C3 (single-implementer interface), or C9
   (copy-paste)? Then the plan is wrong — return to step 3.

7. **Compatibility pass.** Does the plan touch the compatibility surface
   (safety-model §0)? Then changes must be additive-only; removals/renames go
   through the deprecation cycle instead.

8. **Emit AND persist the gate record.** In the response: candidates +
   verdicts, chosen rung(s), justifications, compat notes, expected net-LOC
   sign. On disk (v0.8 — this is what lets the scoreboard verify you later):

   ```
   python3 $SKILL/scripts/gatelog.py add --task "<task>" --rung <n> \
     --symbols "<symbols this gate justifies>" [--note "<rung 7-8 justification>"]
   ```

   diffstat cross-checks new symbols against this ledger and prints
   `unjustified new symbols` for anything that never passed a gate — the
   discipline becomes mechanical, not honor-system.
</process>

End with a terse result line + a **Next** menu of 1-3 `/srk:` commands (see the command file's <next> block). No wall of prose.

<success_criteria>
- [ ] 2–5 candidates listed with extend / not-applicable-because verdicts
- [ ] Every change names its ladder rung; rungs 7–8 carry justifications
- [ ] Hard gate honored when configured
- [ ] No planned change recreates a catalog smell
- [ ] Compatibility surface changes are additive-only
</success_criteria>
