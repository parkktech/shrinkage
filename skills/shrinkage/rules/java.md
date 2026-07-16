# Java Minimalism Rules

## Extend, don't add — Java idioms

- Overload with a defaulted delegate (`create(sku)` → `create(sku, 1)`) or a
  builder field before a parallel method; records + `with`-style copies beat
  near-duplicate DTOs.
- Extend the existing service with a method before adding a new
  `@Service`/`@Component` — every new bean is wiring, config, and test
  scaffolding on top of the LOC.
- Prefer the platform: streams over index loops where clearer, `Optional`
  over null-convention pairs, `java.time` over hand-rolled date math,
  `Map.computeIfAbsent` over check-then-put blocks.
- One `@ParameterizedTest` table beats N cloned test methods.
- Exceptions: extend the existing hierarchy; no parallel exception trees for
  one call site.

## Anti-patterns to refuse

- Interface + single `Impl` class ("`FooService` / `FooServiceImpl`") without
  a second implementation or a genuine proxy need — the classic Java
  speculation; mock frameworks handle concrete classes fine.
- `AbstractBaseHelperManager` layers: abstract classes introduced with their
  first and only child.
- `Utils`/`Helper` class growth when the logic belongs on a domain type.
- Getters/setters on internal classes where a record or direct field serves.

## Dynamic-reference checklist (required before ANY deletion — safety-model §3)

- **Reflection & DI** — the big one: Spring/CDI/Guice resolve beans by
  annotation, name, or classpath scan; a class with zero `new` calls may be
  instantiated by the container. Check component-scan paths, XML/Java config,
  `@Qualifier` strings.
- Annotations processed at build/runtime: JPA entities, Jackson
  (de)serialization, `@EventListener`, `@Scheduled`, AOP pointcuts matching
  by name pattern.
- `Class.forName`, `Method.invoke`, `ServiceLoader` (`META-INF/services`),
  JNDI names, JMX beans.
- Config-file references: Spring properties/YAML naming classes, logback
  appenders, persistence.xml, web.xml servlets/filters.
- Serialized compatibility: `Serializable` classes sitting in caches/queues/
  sessions reference classes by name at deserialization (Zeroth Law surface).
- JSP/Thymeleaf/FreeMarker templates calling getters by property name
  (`${order.total}` → `getTotal()`).
- Public API of published artifacts: anything public in a library JAR is
  semver surface (T2).
- Test frameworks: `@MockBean`, Mockito `mock(X.class)` — mocked types are
  seams; deleting the real one breaks tests silently compile-wise.

## When planning (GSD plan phase)

Query the codemap for existing services, entities, and controllers; name the
exact symbols each task extends (`OrderService.createOrder`). New-class tasks
carry ladder justifications including why the existing bean's cohesion
couldn't absorb the method.

## When verifying (GSD verify phase)

Run `diffstat.py`; check no new single-impl interfaces or abstract-with-one-
child layers, deleted classes checked against DI/reflection/serialization
reachability, suite green, net LOC at or below plan expectation.
