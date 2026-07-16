---
name: srk-gate
description: Reuse gate — decide what to EXTEND before writing any code
argument-hint: <task description>
agent: agent
---

Follow `.github/shrinkage/workflows/gate.md` for the task: ${input}
Refresh the codemap, harvest 2-5 candidate symbols, verdict each
(extend / not-applicable-because-fact), walk the extension ladder, check the
plan against catalog smells C1/C2/C3/C9, confirm compatibility-surface changes
are additive-only, and emit the gate record before any implementation.
