# Drupal Framework Rules

Read WITH `rules/php.md`. Drupal extends by registration — hooks, services,
plugins, events — so most symbols have zero direct callers BY DESIGN. That
cuts both ways: powerful seams for adding less, and a minefield for deletion.

## The platform sweep (before ANY new code)

`codemap.py vendor <term>` plus core's service registry: entity queries,
Queue API, Cache API (`cache.*` bins), Batch API, State/Config APIs,
`\Drupal::service(...)` catalog, existing field types/formatters/widgets,
Views plugins. Check contrib before writing a module — the module probably
exists; extending it beats forking it.

## Extension seams (the ladder, framework-flavored)

- Rung 1: config (YAML) and third-party settings on existing entities.
- Rung 2–3: **alter hooks** (`hook_form_alter`, `hook_entity_type_alter`,
  `hook_views_query_alter`) — modify existing behavior without new structure.
- Rung 4–5: a method on your existing service; an event subscriber on an
  existing event; extending an existing plugin class.
- New plugin instance (block, field formatter, queue worker) via annotation/
  attribute — structured rung 6; it slots into an existing plugin manager.
- Service decoration (`decorates:` in services.yml) over copy-paste service
  replacement.
- New module (rung 8): real domain only; one .info.yml, focused; not
  `mysite_custom` grab-bags.

## Anti-patterns to refuse

- A custom module that duplicates a core/contrib capability found in the
  sweep.
- Procedural .module helpers doing what an injected service should.
- Hook implementations that reimplement what an alter on the existing
  build/query would do.
- `\Drupal::service()` static calls inside classes that could inject.

## Dynamic-reference checklist ADDITIONS (on top of php.md)

- **Hooks are name-magic:** `MODULE_hook_name()` functions have zero callers
  and are absolutely alive. Same for `THEME_preprocess_*`, `template_*`.
- `hook_update_N()` / post-update hooks are PERMANENT once shipped — never
  delete (update sequencing breaks); Zeroth Law at its strictest.
- YAML is the reference graph: *.services.yml (incl. decorators), routing.yml
  (controllers by string), *.links.*.yml, permissions.yml, libraries.yml.
- Plugin discovery: annotations/attributes (`@Block`, `@FieldFormatter`) —
  the annotation IS the registration; derivers generate plugins dynamically.
- Config entities reference plugin IDs and classes by string (views config,
  field storage, entity displays); config schema files.
- Twig templates call fields/functions by name; theme suggestions by pattern.
- Entity API magic: base field definitions, handlers declared in entity
  annotations (storage, access, forms), typed-data constraints by string id.
- Batch/queue callbacks by callable-string; cron implementations via hook.

## When planning / verifying

Plan tasks name the seam ("form_alter on node_form", "decorate
`http_client`", "queue worker plugin") and the module that owns it. Verify:
no core/contrib duplicate written, YAML references resolve (`drush cr` +
config validation), no deleted hook that config/update sequencing still
needs, services injected not statically fetched.

## Templates (Twig)

- .twig files are indexed: blocks and macros appear in the codemap as
  extend/override candidates, and template identifier references count.
- Read `rules/twig.md` for the template ladder (extends+block over copy,
  macro over repetition, logic upstream in preprocess).
- Theme suggestions resolve templates by NAME PATTERN — a "dead" template may
  be selected at runtime; check hook_theme/suggestions before deleting.

## Gate recipes (file-type → cheapest sufficient gate)

- **Services / hooks / plugin annotations:** `drush cache:rebuild` — rebuilds
  the container and re-discovers plugins; a broken service definition or a
  removed class referenced in services.yml fails HERE, not in production.
- **Config / schema:** `drush config:status` after changes — drift shows
  immediately.
- **Twig templates:** recompiled on next render after `drush cache:rebuild`;
  for behavior, a kernel/functional test on the route beats hand-loading pages.
- **Module code:** `vendor/bin/phpunit -c core <module tests>` — one suite,
  own process (kernel tests catch container wiring unit tests can't).
