# SwiftAssay v0.1 contract

SwiftAssay recursively scans `.swift` files beneath the selected directory. `check` exits `0` for no findings, `1` for findings, `2` for unreadable targets, and `64` for invalid input. `--json` writes a sorted-key JSON receipt.

The first rules observe forced failure/trap fragments, selected Foundation and named effect fragments, and a few implicitly-unwrapped optional spellings. They are lexical checks only. They do not parse Swift, type-check code, understand comments or aliases, or prove runtime behavior. A pass never proves complete functional style, purity, correctness, or security.
