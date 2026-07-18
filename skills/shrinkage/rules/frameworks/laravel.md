# Laravel Framework Rules

Read WITH `rules/php.md`. The framework is enormous — most "new" code in a
Laravel app already exists in Illuminate. Sweep before writing.

## The platform sweep (before ANY new code)

`codemap.py vendor <term>` — then prefer, in order: an Illuminate class you
can call, a framework seam you can hang the behavior on, then your own code.
The usual suspects people rewrite: `Str`/`Arr`/`Collection` helpers, the
validation rule that already exists, `Http` client (not Guzzle-by-hand),
`Number`/`Carbon` formatting, queued jobs/notifications, rate limiting,
`Cache::remember`, pagination, signed URLs, task scheduling.

## Extension seams (the ladder, framework-flavored)

- Rung 2–3 equivalents: config value → existing class's optional
  parameter/fluent method → **macro** on Str/Collection/Response/Builder
  (adds a method WITHOUT a new class).
- Rung 4–5: method on the existing Service/Action/Model; scope on the model;
  accessor/cast instead of transforming at every call site.
- Structured seams before new layers: FormRequest for validation, middleware
  for cross-cutting, events/listeners for side effects, policies for authz,
  casts for value objects.
- New service class (rung 6–7) only when a seam doesn't fit — and register it
  where the existing provider already lives, not a new provider per class.

## Anti-patterns to refuse

- Repository-wrapping Eloquent where every method delegates (C2 at scale).
- A helpers.php that shadows `Str`/`Arr` capabilities.
- New singleton managers for what the container + a provider already do.
- Interfaces for app services with one implementation "for swapping later."

## Dynamic-reference checklist ADDITIONS (on top of php.md)

- Routes reference controllers/actions by class-string and name; `route()`
  and `action()` calls by string.
- Container bindings/aliases by string or interface; contextual bindings.
- config/*.php arrays holding class names (mail, queue, auth providers,
  middleware groups); .env keys feeding them.
- Blade: components by kebab-name, directives, `@inject`; view composers.
- Model magic: `$casts`, relation methods called as properties, observers
  registered in providers, `boot{Trait}` conventions, morph maps by string.
- Scheduled commands in console kernel / routes/console.php; event discovery.
- Queued payloads: serialized job class names sitting in queues (Zeroth Law:
  don't rename/remove job classes with jobs in flight).
- Translations, gates/abilities by string name, broadcast channel names.

## When planning / verifying

Plan tasks name the seam ("macro on Collection", "listener on OrderShipped")
rather than "new class". Verify: no Illuminate duplicate got written (sweep
the diff's new symbols against `vendor` search), seams used over layers, and
queued/route/config string references still resolve after any change.

## Gate recipes (file-type → cheapest sufficient gate)

A gate exists to *observe* the change cheaply, not to exercise the whole app.
For each file type in scope, pick the cheapest gate that would actually fail if
the transform broke something — don't improvise a heavy end-to-end run when a
compile-level check suffices. Field-proven recipes:

- **Blade templates** (`*.blade.php`): `php artisan view:cache` compiles every
  template in one pass (catches syntax errors, undefined components/directives,
  bad `@include`/`@extends` targets), then `php artisan view:clear` so a stale
  compiled cache doesn't leak into later runs. Far cheaper than rendering pages.
- **Routes** (`routes/*.php`): `php artisan route:list > /dev/null` resolves the
  whole route table, so a controller/action a route names by class-string fails
  loudly if you removed or renamed it — exactly the reference the static map
  can't see (see the dynamic-reference checklist above).
- **Rendering a specific view for behavior:** do NOT gate through the
  controller/HTTP path when the page is heavy — a report page that recomputes
  minutes of data will time the gate out. Use a fixture render harness:
  `view()->addLocation(<fixture dir>)` and render the region view(s) directly
  with canned data, asserting on the output. Milliseconds instead of minutes,
  and it isolates the template from unrelated slow upstream work.
- **The test runner is not always `phpunit`:** many repos alias
  `vendor/bin/phpunit` to Pest or run only via `php artisan test`. Detect it —
  check `composer.json` scripts and whether `tests/Pest.php` exists — and invoke
  the suite the repo actually uses instead of assuming a raw phpunit binary.
- **Config / `.env` key changes:** `php artisan config:cache` then
  `config:clear` surfaces a malformed config array; grep `config('<key>')` and
  `env('<KEY>')` string reads first (dynamic-reference checklist).

Surgeon/verifier: pick the gate from this table for each file type in scope
rather than improvising one. When a repo teaches a cheaper sufficient gate, add
it here — this list is the framework's institutional memory, not session memory.

## Templates (Blade)

- .blade.php files are indexed (they're PHP to the map): component/method
  references in Blade count toward refs — but @-directive and kebab-case
  component references still need the grep pass before deletion.
- Repeated markup becomes a component with @props defaults or a slot — not a
  copied include. `clones` catches copy-pasted partials.
- Logic in templates belongs in the component class, a view composer, or an
  accessor — @php blocks are a smell.
- Extend layouts via @section/@push overrides, never by copying the layout.
