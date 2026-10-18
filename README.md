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
