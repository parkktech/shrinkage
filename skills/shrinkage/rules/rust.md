# Rust Minimalism Rules

## Extend, don't add — Rust idioms

- Add a defaulted/`Option` parameter or a builder field before a sibling
  method; `impl Default` + struct update syntax (`..Default::default()`)
  beats constructor variants.
- Extend an existing `impl` block before creating a new type; extend an enum
  with a variant before a parallel enum.
- Prefer std/core machinery over hand-rolls: iterator adapters over index
  loops, `?` over match-on-error ladders, `derive` over manual impls.
- Generics with trait bounds beat duplicated concrete versions — but only
  when the second concrete case exists (monomorphization means speculative
  generics cost compile time AND binary size).
- Feature-gate (Cargo features) rather than fork modules for optional
  functionality — and delete expired feature gates like C4 flags.

## Anti-patterns to refuse

- A trait with a single implementer and no test/mocking need — YAGNI applies
  doubly since trait indirection costs dyn dispatch or generic bloat.
- Newtype wrappers that add no invariant, only ceremony.
- `mod utils` growth; free functions belong near the types they serve.
- Cloning to satisfy the borrow checker where a lifetime or reference
  restructure removes both the clone and the confusion.

## Dynamic-reference checklist (required before ANY deletion — safety-model §3)

- **Macros** — the big one: `macro_rules!` and proc-macros reference symbols
  invisibly (`stringify!`, `paste!`, derive expansions). Grep macro
  definitions AND `#[derive(...)]` attributes touching the type.
- Trait implementations: a "dead" method may satisfy a trait bound used
  generically (`T: Display`); search trait definitions for the signature.
- `#[cfg(...)]` conditional compilation — check all feature/target
  combinations (`cargo check --all-features`, and with none).
- Serde and friends: `#[serde(rename)]`, skip/default attrs — struct fields
  reached only through (de)serialization; wire compat is Zeroth Law surface.
- `#[no_mangle]`/`extern "C"` — FFI consumers outside the repo entirely.
- Public items in a published crate: anything `pub` reachable from the crate
  root is semver surface (T2); `pub(crate)` is your internal-only marker.
- Tests/benches/examples/build.rs reference code independently of src.
- Linker-level registration (`inventory`, `ctor`) collects items with no
  visible callers by design.

## When planning (GSD plan phase)

Query the codemap for existing types, impls, and trait method sets; name the
exact impl each task extends (`wallet.rs::Wallet.transfer`). New-crate or
new-module tasks carry ladder justifications; new traits require the second
implementer or a stated dyn/mocking need.

## When verifying (GSD verify phase)

Run `diffstat.py`; check no single-implementer traits appeared, deleted items
checked against macro/derive/cfg reachability, `cargo check --all-features`
green, and net LOC at or below plan expectation.
