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

## Templates (Blade)

- .blade.php files are indexed (they're PHP to the map): component/method
  references in Blade count toward refs — but @-directive and kebab-case
  component references still need the grep pass before deletion.
- Repeated markup becomes a component with @props defaults or a slot — not a
  copied include. `clones` catches copy-pasted partials.
- Logic in templates belongs in the component class, a view composer, or an
  accessor — @php blocks are a smell.
- Extend layouts via @section/@push overrides, never by copying the layout.
