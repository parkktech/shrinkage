# JavaScript / TypeScript Minimalism Rules

## Extend, don't add — JS/TS idioms

- Grow an options object (`{ format = "csv" } = opts`) instead of adding a
  sibling function or a boolean-flag parameter pile.
- Extend the existing module's exports before creating a new file — a new file
  is a new import site for every consumer.
- Prefer a union type or a defaulted generic over a parallel interface.
  `Result<T>` with a wider `T` beats `ResultV2`.
- In React, extend the existing component with a prop (with a default) before
  forking a `XxxVariant` component; extract a child component only when JSX is
  duplicated in two places already.
- Prefer deriving state over storing it: a computed value or memo beats a new
  state field plus the effects that sync it.
- Reuse the project's existing fetch/client/error layer; never add a second
  HTTP wrapper because the first one wasn't found — query the codemap first.

## Anti-patterns to refuse

- An interface or abstract class with one implementer.
- `utils/`, `helpers/`, `lib/misc.ts` growth when the logic belongs beside its
  only caller or on an existing module.
- Wrapper components/functions that only pass props/arguments through.
- Copying a component/function to change one branch — parameterize instead.

## Dynamic-reference checklist (required before ANY deletion — safety-model §3)

JS/TS hides references from static scans in these places. Verify each, or
record why it can't apply, before calling a symbol dead:

- Bracket access with strings or built strings: `obj[name]`, `window[fn]`,
  `this[method]` — grep the name in quotes and template-literal fragments
- Dynamic `import()` / `require()` with computed paths
- DI tokens and decorator metadata (Angular/Nest providers, InversifyJS) —
  bound by token/string, not by import
- Framework convention loading: Next.js/Nuxt file-based routes, auto-imported
  components, serverless function files — the FILE is the reference
- Event systems: `emitter.on("name")` handlers, Redux action types, message
  queue consumers — the string is the contract
- JSX indirection: components passed as props/config, lazy() registries,
  storybook stories
- package.json surface: `main`/`exports`/`bin` entries, npm scripts calling
  files directly; webpack/vite aliases and entry points
- Public package exports: anything in the published entry graph is
  compatibility surface (T2) regardless of local ref counts
- Tests mocking by path: `jest.mock("./wrapper")` makes that wrapper a seam

## When planning (GSD plan phase)

Query the codemap for existing components, hooks, and services touching the
task's domain; name them in plan tasks (`cart.ts::applyDiscount`). New-file plan
tasks carry a one-line ladder justification. Check for an existing barrel/module
the export can join instead of a new file.

## When verifying (GSD verify phase)

Run `diffstat.py` and check: new symbols were justified in the plan, no new
pass-through wrappers, no duplicated component bodies, net LOC at or below the
plan's expectation.
