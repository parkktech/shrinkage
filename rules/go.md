# Go Minimalism Rules

## Extend, don't add — Go idioms

- Grow a function with an options struct (or functional options) rather than
  sibling variants — `Start(port, WithTLS())` beats `StartTLS(port)`.
- Accept interfaces, return structs — and define the interface at the
  CONSUMER, only when a second implementation exists (Go proverb + the
  anti-speculation rule agree here).
- Prefer the stdlib hard: `slices`, `maps`, `errors.Join`, `strings.Builder`
  cover most `utils` candidates since 1.21.
- A method on an existing type beats a free function taking that type as its
  first arg; a free function beats a new single-method type.
- Table-driven tests: extend the table, don't clone the test func.
- Errors: wrap with `%w` on the existing error path; no parallel error
  hierarchies for one caller.

## Anti-patterns to refuse

- Interfaces with one implementation defined next to the implementation
  ("interface pollution") — Go doubles the anti-speculation rule here.
- Getter/setter pairs on structs used only within the package.
- `pkg/util`, `pkg/common`, `pkg/helpers` growth — the function belongs in
  the package whose types it touches.
- A wrapper goroutine/channel layer around an API that's already synchronous
  and fine.

## Dynamic-reference checklist (required before ANY deletion — safety-model §3)

- **Implicit interface satisfaction** — the big one: a method with zero
  callers may exist to satisfy an interface (`Handle`, `ServeHTTP`, `Error`,
  `String`, `MarshalJSON`). Search for interfaces whose method set includes
  the signature before deleting any method.
- Struct tags: `json:`/`yaml:`/`db:` fields reached only via
  (un)marshalling; the field looks dead, the wire format isn't.
- Reflection (`reflect`, `encoding/*`), template packages (`text/template`
  `{{.Method}}` calls by name), and `database/sql` scanning by position.
- Build tags (`//go:build`) — code invisible to your current build is not
  dead; check all tag combinations and GOOS/GOARCH variants.
- `//go:generate`, `//go:linkname`, cgo exports, `plugin.Lookup("Name")`.
- Exported identifiers in ANY package: Go has no package-private-to-repo —
  anything capitalized is compatibility surface for external importers (T2)
  unless the module is `internal/`.
- init() side effects and blank imports (`_ "pkg"`) — a package with no
  referenced symbols may be imported for registration side effects.

## When planning (GSD plan phase)

Query the codemap for the domain's existing types and their method sets; name
what each task extends (`server.go::Server.Start`). New-package tasks carry a
ladder justification and must not create a `util` package. Respect `internal/`
boundaries as the T1/T2 line.

## When verifying (GSD verify phase)

Run `diffstat.py`; check new interfaces have ≥2 implementations, no new
one-method types where a function would do, deleted methods checked against
implicit interface satisfaction, and net LOC at or below plan expectation.
