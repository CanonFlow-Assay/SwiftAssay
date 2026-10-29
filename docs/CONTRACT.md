# SwiftAssay v0.1 contract

SwiftAssay recursively scans `.swift` files beneath the selected directory. `check` exits `0` for no findings, `1` for findings, `2` for unreadable targets, and `64` for invalid input. `--json` writes a sorted-key JSON receipt.

The first rules observe forced failure/trap fragments, selected Foundation and named effect fragments, and a few implicitly-unwrapped optional spellings. They are lexical checks only. They do not parse Swift, type-check code, understand comments or aliases, or prove runtime behavior. A pass never proves complete functional style, purity, correctness, or security.

## Scope-completeness increment (29 October 2026)

A missing or empty supported-source scope returns Inconclusive (exit 2). The shell refuses symbolic-link roots/ancestors and entries, nonregular source files, traversal/enumeration failures, malformed UTF-8 and unsupported size/depth/count limits. Limits are 10,000 source files, 64 directory levels, 4 MiB per file and 64 MiB total. A known lexical finding remains Fail (exit 1) even when another input is incomplete. JSON retains findings and adds `missingEvidence` when needed. Existing nonempty complete Pass/Fail receipts retain their schema and rule meanings.

The pure receipt renderer also refuses to grant Pass for zero observed files. The shell assumes a trusted local, quiescent filesystem; it is not a hostile-host sandbox or semantic compiler. Existing lexical false positives, aliases/macros/comments and runtime limitations remain.
