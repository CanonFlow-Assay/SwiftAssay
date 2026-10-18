---
name: functional-swift
description: Build Swift changes around immutable structs and exhaustive enums, with explicit effects isolated in adapters and ordinary failures returned as values.
---

# Functional Swift

Model domain data with `let` properties in structs and model alternatives with exhaustive enums. For expected validation failures, return a case such as `.rejected(reason:)` or a domain `Result`; do not trap with `try!`, `fatalError`, or precondition failures. Make reductions and transformations explicit and keep domain functions deterministic.

Decode data once at a boundary, validate it, then construct trusted values. Filesystem, network, clock, logging, and UI access belong to injected adapters or the shell. Test every enum case and keep the domain testable without Foundation-driven effects.
