# Source publication and frozen baseline history

The current source is consolidated on `main`. The original lifecycle baseline
commit `3f0176a116b036ae46721d1c0f1f4ab7170d9667` is retained on
`qualification/frozen-baseline-20261029`. A normal full clone fetches that branch.
For a shallow or single-branch clone, restore the required Git object before
running the frozen-baseline lifecycle:

```sh
git fetch origin qualification/frozen-baseline-20261029
```

Do not replace `baseCommit`, weaken the original tests, or relabel old receipts
as executions on the publication commit. The separate baseline ref preserves
original-byte comparison while main has a consolidated implementation change.
Source publication does not admit new rules or grant application release authority.
