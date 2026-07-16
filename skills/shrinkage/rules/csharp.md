# C# Minimalism Rules

## Extend, don't add — C# idioms

- Optional parameters with defaults are first-class — use them before
  overload ladders or sibling methods (`Create(sku, qty = 1)`).
- Extend the existing service with a method before registering a new one in
  DI — every `services.AddScoped<X>()` is wiring plus lifetime reasoning.
- Prefer the platform: LINQ over index loops where clearer, records over
  hand-written DTOs, pattern matching over type-check ladders,
  `string.Create`/interpolation over builders for simple cases.
- Extension methods extend types you don't own — but they live next to their
  domain, not in a grab-bag `Extensions` class.
- One `[Theory]`/`[InlineData]` table beats N cloned `[Fact]`s.

## Anti-patterns to refuse

- `IFooService` + single `FooService` pair by reflex — Moq mocks concrete
  virtual members; add the interface with the second implementation or a
  real proxy/decorator need.
- Abstract base classes born with one child.
- `Helpers`/`Utils`/`Common` class growth when a domain type owns the logic.
- Async-over-sync wrappers (`Task.Run` around synchronous work) that add a
  layer without adding concurrency.

## Dynamic-reference checklist (required before ANY deletion — safety-model §3)

- **DI container & conventions** — the big one: ASP.NET Core resolves by
  type/assembly scan; controllers, middleware, hosted services, and Razor
  pages are discovered, not called. Zero references ≠ not running.
- Reflection & attributes: `[ApiController]` routing, model binding,
  validation attributes, `Activator.CreateInstance`, `Type.GetType("Name")`,
  source generators keying on attributes.
- Serialization surface: System.Text.Json/Newtonsoft property names,
  `[JsonPropertyName]`, EF Core entities and migrations — wire and schema
  compat is Zeroth Law surface.
- Config-by-string: appsettings.json type names, DI registrations from
  config, AutoMapper profiles discovered by scan, MediatR handlers resolved
  by request type.
- Razor/Blazor views calling properties by name; tag helpers; view
  components found by convention (`Default.cshtml`).
- Public members of published NuGet packages: semver surface (T2).
- P/Invoke and `[UnmanagedCallersOnly]` — callers outside the managed world.
- Tests: `Mock<X>`, `[Collection]` fixtures, WebApplicationFactory startup
  classes referenced by generic parameter only.

## When planning (GSD plan phase)

Query the codemap for existing services, controllers, and entities; name the
exact symbols each task extends (`InvoiceService.CreateAsync`). New-class or
new-interface tasks carry ladder justifications including why DI registration
of another service beats one more method.

## When verifying (GSD verify phase)

Run `diffstat.py`; check no reflex `I*`+impl pairs appeared, deleted symbols
checked against DI/convention/serialization reachability, suite green, net
LOC at or below plan expectation.
