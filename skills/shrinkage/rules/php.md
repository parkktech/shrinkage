# PHP Minimalism Rules

## Extend, don't add — PHP idioms

- Add a defaulted parameter (or nullable typed parameter) to an existing
  method before adding a sibling method: `addLine(Item $item, int $qty = 1)`
  grows; `addLineWithQty()` duplicates.
- Extend the existing service class with a method before creating a new
  service — a new service means new wiring in the container/config too.
- Use a trait only when the second concrete user exists; until then the code
  belongs on the one class that uses it.
- Prefer enums (8.1+) or class constants over parallel classes that differ
  only in a value.
- Match the framework's existing extension seam (middleware, event listener,
  scope, policy) before inventing a layer — query the codemap for what the
  project already uses.
- In Laravel/Symfony projects, extend the existing FormRequest/DTO/resource
  with a field before creating a variant class.

## Anti-patterns to refuse

- An interface with a single implementer "for testability" — PHP test doubles
  can mock concrete classes; add the interface with the second implementation.
- New `Helper`/`Util`/`Manager` classes when the logic has a home on an
  existing model or service.
- A repository wrapper whose every method is one delegated ORM call.
- Abstract base classes introduced together with their first and only child.

## Dynamic-reference checklist (required before ANY deletion — safety-model §3)

PHP hides references from static scans in these places. Verify each, or
record why it can't apply, before calling a symbol dead:

- Variable functions/classes/methods: `$fn()`, `new $class`, `$obj->$method`,
  `call_user_func` / `call_user_func_array` with strings or arrays
- Magic methods absorbing calls: `__call`, `__callStatic`, `__get`, `__set` —
  any of these on a class (or its parents) hides method references
- Container/service bindings by string: Laravel service providers, Symfony
  services.yaml, facades resolving via container keys
- Route/console registration: routes files referencing
  `Controller::class . '@method'` or string actions; scheduled commands;
  queue job classes resolved by name at dispatch
- Blade/Twig templates calling helpers, components by kebab-name, and
  accessor properties (`$user->full_name` → `getFullNameAttribute`)
- Eloquent conventions: accessors/mutators/scopes (`scopeActive`) called by
  derived names; model events; observers registered by class string
- Serialized data: queued jobs and cached payloads reference classes by FQCN
  string — a class with zero code refs may be sitting in a queue right now
- composer.json autoload files/scripts; config arrays of class names
- Reflection-based frameworks (attributes/annotations): the attribute IS the
  registration

## When planning (GSD plan phase)

Query the codemap for existing services, models, and controllers in the task's
domain; name the exact symbols to extend (`InvoiceBuilder::addLine`). New-class
or new-file plan tasks carry a one-line ladder justification, including why the
framework's existing seam wasn't enough.

## When verifying (GSD verify phase)

Run `diffstat.py` and check: new symbols match plan justifications, no new
single-implementer interfaces, no new Helper/Util/Manager classes with an
obvious home, net LOC at or below the plan's expectation.
