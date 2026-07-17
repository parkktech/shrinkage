# Kotlin Minimalism Rules

## Extend, don't add — Kotlin idioms

- **Default parameters are rung 2 as a language feature** — `fun export(fmt:
  Format = Format.CSV)` beats overloads AND sibling functions; named args keep
  call sites readable as params grow.
- Extension functions extend types you don't own — but they live next to
  their domain, never in a `Utils.kt` grab-bag; and prefer a member function
  when you DO own the type.
- `data class` + `copy()` over builder boilerplate and near-duplicate DTOs;
  `sealed class`/`sealed interface` + `when` over parallel class hierarchies
  (exhaustiveness makes extension safe).
- Reach for stdlib first: scope functions, collection operators
  (`groupBy`, `associateBy`, `fold`), `runCatching`, delegation (`by`) — most
  "helpers" already exist.
- One parameterized test over cloned test functions.

## Anti-patterns to refuse

- Interface + single `Impl` (Java habit; mockk mocks finals/concretes fine).
- `object SomethingUtils` / `Helpers.kt` growth when the logic has a type.
- `!!` chains and `lateinit` where a constructor default or `?:` collapses
  branches.
- Abstract base classes born with one child; `open` "for later".

## Dynamic-reference checklist (required before ANY deletion — safety-model §3)

- **AndroidManifest.xml** registers activities/services/receivers/providers
  by class name — zero code refs, absolutely alive. (Indexed ref-only by the
  map, but verify intent-filters and aliases too.)
- Layout/navigation/menu XML: custom views by FQCN, `android:onClick` method
  names, `app:destination`, data-binding expressions calling methods.
- Generated code keeps sources alive: ViewBinding/DataBinding, Room DAOs,
  Hilt/Dagger components, kapt/ksp processors — a "dead" annotated class may
  be the input to generated wiring.
- **ProGuard/R8 keep rules** (`*.pro`): a class kept by rule is referenced by
  something outside static analysis (reflection, JNI, SDKs).
- Serialization by name: kotlinx.serialization, Gson/Moshi field names,
  Firebase/Parcelize; renames break wire/data compat (Zeroth Law).
- Reflection + coroutines machinery: `Class.forName`, WorkManager worker
  class names, JobScheduler, deep links, `@JvmName`/`@JvmStatic` for Java
  callers, JNI `external fun`.
- Gradle: `applicationId`/manifest placeholders, buildConfigField consumers,
  flavor-specific source sets (code "unused" in one flavor is live in another).
- Multiplatform: `expect`/`actual` pairs — deleting one side breaks targets
  you're not building right now.

## When planning (GSD plan phase)

Name the existing type/extension point each task extends
(`OrderRepository.fetch`, extension on `Flow<T>`); new-file tasks carry
ladder justifications; check the platform sweep (Jetpack/androidx — see
frameworks/android.md) before writing anything Google already ships.

## When verifying (GSD verify phase)

Run `diffstat.py`; check no new single-impl interfaces or Utils objects,
deleted symbols verified against manifest/XML/generated-code/keep-rule
reachability, all build flavors compile, net LOC at or below plan.
