# Python Minimalism Rules

## Extend, don't add — Python idioms

- Prefer a keyword argument with a default over a new function variant.
  `export(fmt="csv")` beats `export_csv()` + `export_json()` — callers stay valid.
- Module-level functions over manager/service classes with no state. A class
  whose `__init__` is empty is a namespace, and modules already are namespaces.
- Extend an existing dataclass with a defaulted field instead of a parallel
  type. Two near-identical dataclasses always drift apart.
- Reach for the stdlib before writing a helper: `itertools`, `functools`,
  `pathlib`, `collections` cover most "utils" candidates.
- Use comprehensions/generator expressions where they replace a loop-and-append
  block one-for-one; keep the loop when logic has branches.
- Prefer editing the existing test parametrization (`pytest.mark.parametrize`)
  over cloning a test function per case.

## Anti-patterns to refuse

- `ABC`/`Protocol` with a single implementer — add it with the second one.
- `utils.py` / `helpers.py` growth when the function has an obvious home on an
  existing class or module.
- Wrapper functions whose body is one delegated call.
- Class hierarchies for behavior a dict-of-functions or a parameter expresses.

## Dynamic-reference checklist (required before ANY deletion — safety-model §3)

Python hides references from static scans in these places. Verify each, or
record why it can't apply, before calling a symbol dead:

- `getattr`/`setattr`/`hasattr` with the symbol's name as a string or built
  string — grep the name in quotes and f-string fragments
- `importlib.import_module` / `__import__` with dotted-path strings
- `__getattr__`/`__getattribute__` on modules or classes (PEP 562 module
  attrs) — one of these existing anywhere in the package caps confidence
- Framework registration by string: Django `settings.py` dotted paths, urls
  `as_view` strings, Celery task names, entry_points in
  pyproject.toml/setup.cfg, plugin registries
- Decorator-based registries (`@app.route`, `@receiver`, `@click.command`) —
  the function has no *callers* by design; being registered IS the reference
- Templates: Jinja/Django template files call methods and filters by name
- Pickled/serialized objects: a class needed only for `pickle.load` of old
  data has zero code refs and is absolutely load-bearing
- `# noqa` / `del`-guard patterns and re-exports in `__init__.py` (`__all__`)
- Test fixtures/conftest discovery by name convention

## When planning (GSD plan phase)

Query the codemap for the domain nouns of the task and name the exact existing
symbols each plan task will extend (`file.py::Class.method`). A plan task that
creates a new file must carry a one-line justification for why rungs 1–6 of the
extension ladder were insufficient.

## When verifying (GSD verify phase)

Run `diffstat.py` and check: new symbols match what the plan justified, no new
single-implementer ABCs/Protocols, no new `utils` entries with an obvious home,
and net LOC is at or below the plan's expectation.
