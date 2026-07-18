# The Consolidation Catalog

The complete taxonomy of reduction transformations. Every shave, audit finding,
and surgeon assignment names its catalog entry — that's how we keep each change
atomic, reviewable, and tied to a known safety profile.

Format per entry: what it looks like, the detection signal, the transform, the
risk tier (see `safety-model.md`), and the gotchas that bite.

---

## C1 — Parameterize near-duplicate siblings

**Smell:** `exportCsv()` / `exportJson()`, `notifyAssignee()` / `notifyOwner()`
— same skeleton, one varying value or branch.
**Detect:** `codemap.py dupes` (same name-stem or matching param shapes in
sibling scopes); map groups with similar signatures in one file/module.
**Transform:** merge bodies into one function; the difference becomes a
parameter with a default that preserves the most common current behavior.
Existing entry points keep working — on the compatibility surface they remain
as deprecation shims (Zeroth Law), internally call sites are migrated in the
same commit.
**Tier:** T1 internal; T2 if any sibling is public.
**Gotchas:** siblings that *look* alike but diverge subtly (error handling,
logging, transactions) — diff them line by line before merging; a
characterization test per sibling first. Siblings in DIFFERENT domains → the
cross-domain home-selection rule (below): neutral home or no merge, never one
domain calling the other's method.
**Payoff:** estimate and rank like C9 (below) — subtract the merged home's cost
(shared body + parameterized signature + migrated call sites); the real win is
one canonical definition and less drift risk, not raw LOC.

## C2 — Collapse pass-through wrappers

**Smell:** a function/method whose entire body is one delegated call with the
same arguments; a component that only forwards props.
**Detect:** map + read; body ≤ 2 lines with a single call expression.
**Transform:** point callers at the target directly; delete the wrapper.
**Tier:** T1 internal; T2 if exported. Deprecation shims (safety-model §0) are
exempt — they're *supposed* to be wrappers; check for the deprecation marker
before flagging.
**Gotchas:** the wrapper may exist to break an import cycle, pin an interface
for DI, or provide a mocking seam the test suite patches. `grep` the test
suite for patches of the wrapper's path before removing.

## C3 — Inline single-implementer abstractions

**Smell:** interface/ABC/abstract class with exactly one implementer;
factory that can only ever produce one type.
**Detect:** map: `i`/`c` symbol whose name is referenced only by one
implementing class and its DI wiring.
**Transform:** delete the abstraction, use the concrete type; keep the
concrete type's name if it's the one on the compatibility surface.
**Tier:** T1 internal; T2 if the interface is exported or the DI container
binds it by name.
**Gotchas:** test doubles implementing the interface count as implementers of
*intent* — if the suite mocks against it heavily, converting tests to mock the
concrete class is part of the transform's cost; weigh before starting.

## C4 — Eliminate dead branches and expired flags

**Smell:** `if (FEATURE_X_ENABLED)` where the flag has been 100% rolled out
for months; platform branches for platforms no longer supported; `else` arms
no input can reach.
**Detect:** grep flag names against the flag config/service; git history
(`git log -S<flag>`) shows rollout completed long ago.
**Transform:** keep the winning branch, delete the flag check, the losing
branch, and the flag's registration/config entry.
**Tier:** T0 when the flag value is a repo-visible constant; T1 when it comes
from a flag service (confirm rollout state first).
**Gotchas:** kill-switch flags are dead-looking *on purpose* — confirm with
the owner that the flag is retired, not dormant. Delete the flag definition
too, or the next audit re-finds half the work.

## C5 — Replace hand-rolled code with the platform

**Smell:** a utility reimplementing `pathlib`, `Array.prototype.groupBy`,
Laravel collections, lodash-already-in-deps, or the framework's own paginator/
validator/retry.
**Detect:** rules/<lang>.md idiom lists; audit pass over `utils`/`helpers`.
**Transform:** swap call sites to the platform version; delete the local copy.
**Tier:** T1 — behavior differences are the whole risk (edge cases, error
types, locale/timezone handling). Characterization tests on the hand-rolled
version FIRST, then confirm the platform version passes the same tests.
**Gotchas:** the hand-rolled version's quirk may be load-bearing (callers
depend on its wrong-but-stable sort order). If the quirk has dependents,
preserving it *is* the behavior — document and keep, or migrate callers first.

## C6 — Remove dead symbols

**Smell:** functions/classes/exports with zero real references.
**Detect:** map `x0` → then the FULL evidence chain (safety-model §3) — map
evidence alone is never sufficient.
**Transform:** delete the symbol, its tests-of-nothing (tests that only test
the dead code), its exports, and its docs entry, in one commit.
**Tier:** T1 internal with complete chain; T2 public → deprecation cycle.
**Gotchas:** everything in safety-model §1 (reflection, DI, templates, routes,
external callers). This is the entry where the dynamic-reference checklist
earns its keep.

## C7 — Flatten trivial hierarchies and merge anemic classes

**Smell:** a class with one method and no state (a function wearing a
costume); two classes that are always instantiated and used together; a
base class whose only child overrides nothing.
**Detect:** map: `c` symbols with 1 method; inheritance chains of depth 1
with no polymorphic call sites.
**Transform:** class-with-one-method → function; always-together pair →
merge; no-op base → fold into child.
**Tier:** T1 internal; T2 if any name is on the surface (keep the public name).
**Gotchas:** frameworks that discover classes by convention (commands,
listeners, jobs) need the class shape even when it looks anemic — check the
framework's registration mechanism first.

## C8 — Table-ify switch ladders

**Smell:** long if/elif or switch mapping a value to a value (or to a
one-liner behavior), duplicated in more than one place.
**Detect:** repeated `case`/`elif` blocks over the same domain in the map's
high-LOC functions.
**Transform:** one dict/map/lookup table + one line of lookup; shared tables
live next to their domain type, not in `utils`.
**Tier:** T0–T1 (pure mechanical when arms are value-only).
**Gotchas:** arms with side effects or fall-through are logic, not data —
don't force them into a table that then needs lambdas everywhere; that's
swapping visible complexity for hidden complexity at equal LOC.

## C9 — Deduplicate copy-pasted blocks into an EXISTING home

**Smell:** the same 5–20 line block in ≥2 places (validation preambles,
response envelopes, retry loops).
**Detect:** audit pass; `dupes` name-stem hits; reviewer instinct ("I've read
this before").
**Transform:** the block moves to the *existing* symbol that owns the concept
(ladder rungs 2–5) — a parameter, an extended method, a method on the type the
data belongs to. Only when no owner exists does it earn a new function (rung
justification required). NOT a new `utils` entry by default. Method-level
merges execute through `scripts/extract_method.py` (check → extract → remove →
wire; PHP/Java/C#/Kotlin/Go/Rust exact tokenizers, Python via ast, JS/TS via
tree-sitter), never hand-sliced. Template dedupe (Blade/Twig/Vue) is
partial/component extraction instead — manual, gated by the template compile.
**Tier:** T1.
**Gotchas:** two copies that are one character different are two *behaviors* —
find out which one is the bug before unifying on either. Copies in DIFFERENT
domains → the cross-domain home-selection rule (below) decides neutral-home /
adjudicate / keep — the "existing home" must respect domain boundaries.
**Payoff (estimate honestly):** "lines removed" overcounts — the shared home
costs real LOC: the merged body once (usually ≥ one block, since it absorbs the
variants), its docblock, and one `use`/call line per site.
Net ≈ `N × block_LOC − (merged body + docblock + N call-lines)`, and a
*documented* shared home routinely nets ~0 or even positive (a deployment
measured −70 estimated → **+1 actual**). So the real, rankable win is NOT net
LOC — it's **duplicate definitions collapsed** (N → 1 canonical) and **bug-
surface removed**: a fix to the shared concept now touches one place, not N.
Record the collapse count; feed `plan.py done` so the realization loop learns
this repo's C9 factor.

## C10 — Delete comment noise and zombie code

**Smell:** commented-out code blocks, `// TODO 2019`, doc comments narrating
the line below them (`i++ // increment i`), dead README sections for removed
features.
**Detect:** T0 sweep; grep for comment markers + git blame age.
**Transform:** delete. Git remembers everything; commented-out code is a
worse `git log`.
**Tier:** T0.
**Gotchas:** license headers, linter pragmas, and genuine WHY-comments stay —
the target is noise, not documentation. When a TODO is real, it becomes a
tracked issue, then the comment goes.

---

## Cross-domain merges: the home-selection rule

**Same bytes ≠ same concept.** Before any C1/C9 merge, look at where the twins
LIVE, not just what they say. Twins inside one domain merge into the owning
symbol (standard C9). Twins in **different domains** — a `UserProfile` method
and a byte-identical `StockType` method — are one of exactly three cases, and
the classification decides everything:

1. **Neutral concept** — the code belongs to *neither* domain (money
   formatting, ratio math, retry, date rounding). Hoist it to a
   **domain-neutral home** — an existing Support/Concerns trait or shared
   module (extension ladder applies: existing neutral module before a new
   file) — and have BOTH domains depend on it. **Dependency arrows point
   domain → shared, never domain → domain.** Making `StockType` call
   `UserProfile::formatMoney()` is not a merge, it's a coupling: unrelated
   lifecycles chained so the next profile change is a stock-type risk.

2. **One true owner** — the concept genuinely belongs to one domain and the
   other copied it. Cross-domain "just call the owner" is still wrong; the real
   question is design-level: either the borrower shouldn't have this behavior
   at all, or the concept is actually neutral (→ case 1). Route as
   **T2/adjudication with the analysis attached** — never auto-merge.

3. **Coincidental twins** — identical *today*, but they change for different
   reasons (profile validation vs stock validation that happen to match).
   **Do NOT merge — duplication is cheaper than the wrong abstraction.**
   Record a ledger keep ("coincidental twins — will diverge") so no future
   audit re-flags the pair.

**The change-reason test** decides between them: *"would a change requested for
domain A's copy ever need to differ from domain B's?"* — yes or unsure →
case 3, keep. Only a confident "no, it's one concept" earns cases 1–2.

**The neutral home still pays the full quality bill:** named for the CONCEPT
(`MoneyFormat`, `RatioMath`), never for a donor (`UserProfileHelper` consumed
by stock code is the smell wearing a new name); no grab-bag `utils` growth
(never-list); C9's honest pricing applies (defs collapsed and bug-surface
removed vs. what the home costs); and the reuse gate governs its creation like
any new code.

## Using the catalog

- The **audit** workflow tags every finding `C<n>` + tier and ranks by
  (payoff × confidence) / effort.
- The **surgeon** executes exactly one entry per commit, following the
  transformation protocol (safety-model §6).
- The **verifier** checks the executed transform against this entry's gotchas
  specifically — they are the known failure modes.
- The **gate** uses C1–C3 and C9 in reverse: they describe the duplicates you
  are about to create if you skip the reuse check.
