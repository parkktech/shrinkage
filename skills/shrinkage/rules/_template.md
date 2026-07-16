# <Language> Minimalism Rules

<!-- Copy this template to rules/<lang>.md when adding a language. Keep it
under ~50 lines: these files are loaded by fresh-context agents (including
GSD planners/executors/verifiers) on every task that touches the language. -->

## Extend, don't add — <language> idioms

<!-- 4–8 rules for HOW to stay low on the extension ladder in this language.
Each rule: the preference, then the one-line why. -->

## Anti-patterns to refuse

<!-- Language-specific speculative structure: the local flavors of
"interface with one implementer" and "wrapper around a wrapper". -->

## Dynamic-reference checklist (required before ANY deletion — safety-model §3)

<!-- THE most important section for deletion safety. List every place this
language/ecosystem references symbols in ways static scans miss: reflection,
string-built lookups, DI containers, convention-based framework loading,
templates, serialized data, registration by decorator/attribute, build-tool
entry points, tests mocking by path. 8-12 items; each greppable/verifiable. -->

## When planning (GSD plan phase)

<!-- What the planner should check in the codemap before writing tasks:
which existing symbols to name in the plan, what counts as justification
for a new file in this language. -->

## When verifying (GSD verify phase)

<!-- What the verifier should scan for: new-symbol count vs plan, planted
duplicates, ladder-rung justifications present for new files/modules. -->
