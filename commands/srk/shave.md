---
name: srk:shave
description: "Safe subtraction pass: remove/consolidate code with evidence chains, atomic commits, and zero behavior change"
argument-hint: "[plan item # | --auto [--dangerous] | dir | file] [--dry-run]"
allowed-tools: [Bash, Read, Grep, Edit, Write, Agent]
---

<objective>
Execute a subtraction pass on $ARGUMENTS (or the files touched by the current
change) with zero behavior change. Deleting is part of the feature — and it
follows the safety model to the letter.
</objective>

<execution_context>
Locate the shrinkage skill dir ($SKILL: `${CLAUDE_PLUGIN_ROOT}/skills/shrinkage` when installed as a plugin, else `.claude/skills/shrinkage`,
`~/.claude/skills/shrinkage`, or `.agents/skills/shrinkage`), then follow
`$SKILL/workflows/shave.md` exactly. Required reading first:
`$SKILL/references/safety-model.md` and
`$SKILL/references/consolidation-catalog.md`.
</execution_context>

<execution_context_extra>
FIRST: the TODO gate. If SHRINK-PLAN.md carries unchecked `- [ ]` items under
`## TODO before shaving`, stop and report them instead of executing — the
audit marked them as prerequisites (bugs to fix first, security hazards, stale
tooling). Only an explicit user "shave anyway" overrides; record the waiver.

Targets: a plan item number (default one-at-a-time), `--auto`/`all` (work the
whole backlog until a stop condition), a dir/file path, or nothing (current
diff). After a single item, ALWAYS prompt for the next one (name it + its
tier + est LOC); `--auto` runs without prompting and halts on the first T2/T3 item,
first red gate, or empty backlog. `--auto --dangerous` (alias --full-send)
proceeds THROUGH T2/public-surface too (direct removal, no deprecation cycle) —
still atomic + tests-green-or-revert per item, still hard-stops on a red/absent
suite; refused if allow_dangerous:false. When --auto halts safely, report what
got done + why it stopped + the two continue options (never a bare '0 done').

When `--full-send` FINISHES, anything still open is something autonomy must NOT
do on its own — a target dirty with the user's uncommitted work, a red/absent
baseline, or a behavior-divergence adjudication that needs a human decision.
That is COMPLETION, not a shortfall: say so ("full-send done — everything I can
safely execute is committed"), then list each leftover with WHY it needs the
USER (commit or stash in-flight work → re-audit unblocks dirty targets; make the
divergence calls). Do NOT end with a bare `/srk:shave <n>` as if more autonomous
shaving remains — it doesn't; the leftovers are blocked on a person, not a run.
</execution_context_extra>

<success_criteria>
- [ ] Suite green before, after every transform, and at the end
- [ ] One atomic commit per transform with the evidence template
- [ ] T2 candidates escalated with evidence, never executed silently
- [ ] Compatibility surface intact; net app LOC negative or justified
- [ ] Single item → prompted for the next; `--auto` → ran to a stop condition
</success_criteria>

<next>
Lead with the ONE concrete action for the mode; if it's a human step, say it
plainly — don't just list a command:
• single item done → next up: /srk:shave <next #> (name the item)
• halted with items blocked on YOU → lead with the human action: "Commit or
  stash your in-flight work, then /srk:shave <n>", or "Land your branch, then
  /srk:audit" — never a bare command or a buried "becomes executable after…".
  Do NOT re-suggest items full-send already handed back.
• clean finish, backlog drained → /srk:score <base>..HEAD, then /srk:trend
</next>
