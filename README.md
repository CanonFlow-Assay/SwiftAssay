# SwiftAssay

SwiftAssay is a deterministic checker for a small functional Swift profile. Its scanner is a pure library; only the executable shell enumerates and reads files. The order example uses immutable structs, exhaustive enum outcomes, and a pure reduction.

The project targets [Swift `6.4`](https://www.swift.org/blog/swift-6.4-released/), the current stable release at its creation, in Swift language mode 6. It has no package dependencies or telemetry.

```sh
swift test
swift run swift-assay check Examples/Clean/Sources/Domain --json
swift run swift-assay check Examples/Violations/Sources/Domain
```

Read [the v0.1 contract](docs/CONTRACT.md) for the exact evidence boundary. The authoring guide is [functional-swift](skills/functional-swift/SKILL.md).

Licensed under Apache-2.0.

## ExpenseGuard playground

The [native ExpenseGuard playground](playground/README.md) adds requirements,
real baseline/expanded acceptance execution, isolated mutation controls, bounded
offline investigation advice and source/log freshness checks. Run:

```sh
python3 playground/run.py --output artifacts/playground/first-run
```

This experiment is separate from checker authority. Exact runtime pin gaps remain
Inconclusive even when the experiment completes; survivors remain visible.

## Scope completeness

Empty, linked, unreadable and unsupported source scopes cannot Pass. Incomplete JSON retains `missingEvidence`; known findings remain Fail. See the [current scope addendum](docs/CONTRACT.md#scope-completeness-increment-29-october-2026). Original USB evaluation metadata remains historical; its current-resolution section records this increment.

## Requirements lifecycle and local archive consumer

The [R6 lifecycle](playground/lifecycle/README.md) freezes the prior12-case
baseline, retains real Unicode-boundary acceptance failures, executes the repaired
22-case candidate and an independent locally packed verifier consumer. Run
`python3 playground/lifecycle/run.py --output ../brainstorm/astra/evidence/native-lifecycle-a-fresh-run`
under the documented exact SDK environment. Its assessment remains separate
from checker authority and human release approval.
