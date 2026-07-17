# Android Framework Rules

Read WITH `rules/kotlin.md` (or `rules/java.md` for legacy modules). Detection:
`build.gradle(.kts)` / `AndroidManifest.xml` present.

## The platform sweep (before ANY new code)

Jetpack/androidx almost certainly ships it: Paging, WorkManager, Navigation,
Room, DataStore (not hand-rolled prefs), Lifecycle/ViewModel, CameraX, Coil/
Glide, Retrofit/OkHttp interceptors, Hilt. Search your own modules first
(`codemap.py query`), then check androidx before writing a manager,
scheduler, cache, or image loader by hand.

## Extension seams (the ladder, Android-flavored)

- Rung 1–2: resource/config values, theme attributes, a defaulted parameter
  on the existing composable/use case.
- **Compose:** extend the existing composable with a parameter or `Modifier`
  before forking a Variant composable; hoist state instead of duplicating
  stateful widgets; slot APIs (`content: @Composable () -> Unit`) over
  copy-paste layouts.
- **Views (legacy):** styles/themes over per-view attributes; `<include>`/
  merge over duplicated layout blocks; a custom view only at the second use.
- Architecture: a function on the existing ViewModel/UseCase/Repository
  before a new one; an OkHttp interceptor over per-call header code; a Room
  migration over a parallel table.
- DI: bind into the existing Hilt module for the domain; a new module is a
  rung-7 decision.

## Anti-patterns to refuse

- `*Manager`/`*Helper` singletons duplicating a Jetpack library.
- A BaseActivity/BaseFragment hierarchy born for one shared behavior — use
  composition (delegates, lifecycle observers).
- Copying a composable/layout to change one color/padding (that's a
  parameter/style/modifier).
- New Application-scope state for what `SavedStateHandle`/DataStore owns.

## Dynamic-reference checklist ADDITIONS (on top of kotlin.md)

kotlin.md's checklist covers the core (manifest, layout XML, generated code,
keep rules, serialization, flavors). Android-specific extras: app widgets and
tile/service metadata XML, `res/xml` (shortcuts, file-provider paths,
preferences screens), WorkManager unique work names, notification channel
ids, intent actions/extras used by external apps (compatibility surface!),
and Play Feature Delivery dynamic modules loaded by name.

## When planning / verifying

Plan tasks name the seam ("parameter on CheckoutSummary composable",
"interceptor on the existing OkHttp client", "function on OrderUseCase").
Verify: no Jetpack duplicate written, every deleted class checked against
manifest + XML + generated wiring + keep rules, `assemble` green across
flavors, and lint's UnusedResources run before believing a resource is dead.
