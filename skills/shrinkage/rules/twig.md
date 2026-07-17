# Twig Template Rules (Drupal, Symfony)

Read WITH the framework rules (`frameworks/drupal.md` where applicable).

## Extend, don't add — template idioms

- `{% extends %}` + override ONE `{% block %}` beats copying a whole template
  to change a section — the block map shows exactly which override points the
  base already offers.
- Repeated markup (2+ places) becomes a `{% macro %}` or an `{% embed %}` with
  blocks — the codemap's dupes/clones sweeps now see template copy-paste.
- Logic belongs upstream: a preprocess/view-model/controller variable, not
  chained filters re-derived in five templates.
- Prefer the existing filter/function (core + framework extensions) over a
  custom Twig extension; a custom extension needs the second use case.

## Anti-patterns to refuse

- Full-template copies into a theme to change one block (the template-land C9).
- Near-identical macros in sibling templates — consolidate to one, import it.
- `{% if %}` ladders switching on a type — that's a template suggestion /
  separate block's job.

## Deletion checklist additions

- Templates are resolved by NAME CONVENTION (Drupal theme suggestions,
  `hook_theme`, Symfony bundle overrides) — a template with zero includes may
  be selected at runtime by pattern. Verify the naming registry before
  deleting any template.
- Blocks may be overridden by child themes you don't see in this repo.

## When planning / verifying

Plan tasks name the block/macro being extended, not "edit the template".
Verify: no whole-template copy landed where a block override sufficed; new
macros justified by a second call site.
