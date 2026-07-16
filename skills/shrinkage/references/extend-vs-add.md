# Extend vs Add — Worked Examples

Read this when a reuse-gate decision feels ambiguous. Each example shows the
task, the tempting addition, and the ladder-lower move that wins.

## 1. "Add CSV export to reports" (rung 2 beats rung 6)

Tempting: `class CsvExporter` beside the existing `ReportExporter`.
Codemap shows: `m render(self, data, format="pdf")  x14`.
Winning move: add `"csv"` to the format dispatch inside `render`. One branch,
zero new symbols, every existing caller can now pass `format="csv"`.
Justification pattern: a new class duplicates the data-loading and pagination
that `ReportExporter` already owns.

## 2. "Remember me on login" (rung 2–3 beats rung 8)

Tempting: a `persistent_sessions` module with its own store.
Winning move: `SessionManager.create(user, ttl=DEFAULT_TTL)` grows a `ttl`
parameter; the login handler passes the long TTL when the box is checked.
The session store, expiry sweep, and invalidation logic already exist — a new
module would re-own all three.

## 3. "Also notify the account owner" (subtraction pass)

Tempting: `notifyOwner()` next to the existing `notifyAssignee()`.
Winning move: both become one `notify(recipients)` — resolve recipients at the
call site. Net LOC negative: two near-duplicate methods collapse into one.
Rule of thumb: when the new requirement makes two siblings differ only by a
value, the requirement is telling you to merge them, not to add a third.

## 4. When ADDING is actually right

The ladder is a bias, not a ban. A new file/class is correct when:

- the codemap shows no symbol owning the domain (nothing to extend), or
- extending would couple two things that change for different reasons (the
  justification must name the two reasons), or
- the existing symbol is already past its cohesion limit and the plan includes
  splitting it (net LOC still trends down).

A stated one-line justification that survives those three checks is a good
addition. "It felt cleaner" does not survive them.
