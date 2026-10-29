# SwiftAssay ExpenseGuard playground

This is the first CSAssay-inspired application workflow increment for Swift.
It adapts the useful parts of the C# Playground: named requirements, an immutable
functional core, an effect shell, executed baseline/expanded test selections,
isolated mutations, offline next-investigation proposals, and source freshness.
The native Swift domain and harness execute real code; Python 3 is only the
local experiment/evidence adapter.
No packages are downloaded, model providers contacted, or payments performed.

## Run locally

From this repository root:

```sh
python3 -m unittest discover -s playground -p 'test_*.py' -v
python3 playground/run.py --output artifacts/playground/first-run
python3 playground/review.py artifacts/playground/first-run/run.json
```

Choose a **fresh output directory** for every experiment. Existing evidence is
never overwritten. The adapter needs Python 3.10+; Python domain execution uses
Python 3.14. The other domains use their actual installed native compilers.
The runner records compiler versions and hashes. Rust uses the already installed
`stable` toolchain and never asks rustup to fetch the absent pinned compiler.
Kotlin verifies the compiler files against the existing repository lock before
compiling and records Java. Swift compiles in Swift language mode 6.

Exit codes describe this **bounded experiment**: 0 Pass (every registered
observation matched and exact native pin matched), 1 Fail (unexpected result),
2 Inconclusive (including a runtime pin gap or changed source), 3 ToolFailure.
An Inconclusive runtime qualification may still contain a completed experiment;
inspect both `completed` and `toolchain.exactPinQualified`.
This is separate from the existing checker's receipt and grants no release approval.

## Requirements and real observations

Read [the declared requirements](expenseguard/requirements.json) first.
ExpenseGuard decides integer-cent expenses in USD: invalid policy/input,
approval at or below the limit, and review above it. Closed native outcome cases
carry amounts or rejection reasons. There is no floating-point currency conversion.
The shell owns command-line arguments, compiler/process calls, files and reporting.

The original six named cases deliberately miss zero and exact-limit boundaries.
The expanded twelve cases retain those six and add the missing edges, whitespace,
negative policy and a large amount. Each native harness emits one explicit result
per expected case and a consistent exit code; missing, duplicate, foreign or
malformed output cannot pass.

The runner compiles **copies**, retaining every source and executable under the
fresh evidence directory. Five registered transformations execute:

| Case | Original selection | Expanded selection | Interpretation |
| --- | --- | --- | --- |
| Accept zero | Survives | Killed by zero amount | Propose registered zero-boundary investigation |
| Review exact limit | Survives | Killed by exact limit | Propose registered limit-boundary investigation |
| Remove currency guard | Killed | Killed | Existing test protects the requirement |
| Integer-equivalent candidate | Survives | Survives | SurvivorReview; equivalence remains unresolved |
| Invalid source | Compilation fails | Not run | InvalidMutation, never a killed mutation |

A sixth **control** deliberately breaks the original baseline. Its real failing
acceptance run requires context repair and cannot trigger mutation advice.
The original baseline and every expected rejection keep their raw logs.

`advice.py` is deterministic and offline. It can propose only the registered
`zero-amount` and `exact-limit` investigations. A failed baseline, invalid
mutation, missing result, stale snapshot, unknown probe, or exhausted proposal
budget cannot become Pass or execute a command. `--budget 0` demonstrates
BudgetExhausted for otherwise eligible proposals. The budget limits a proposal
for each independent mutation observation; it does not execute probes.

## Evidence and freshness

`run.json` binds playground inputs, requirements, relevant toolchain declarations,
compiler identity, commands, native case results, raw-output/log hashes, actual
build products and each mutation observation. `run.sha256` covers receipt bytes.
These are local integrity bindings, not signed attestations. The final source
snapshot must match the starting snapshot. `review.py` checks current source,
receipt bytes and every retained execution log without executing source. A changed
source, tampered receipt or missing/changed log makes its state NotAvailable.
The original historical verdict remains in its receipt.

## Existing checker remains separate

Run the existing checker explicitly:

```sh
swift run swift-assay check playground/expenseguard/domain --json
swift run swift-assay check Examples/Violations/Sources/Domain --json
```

The clean domain should produce no selected lexical findings. The existing violating specimen must still exit 1. Lexical absence does not prove purity, parsing, source completeness or runtime correctness.
The experiment does not promote admitted rules, waive findings, change historical
receipts or alter the existing checker exit/JSON contract.

## Remaining phases

This bounded increment is not general application intake, an automatic code
migration, a general mutation engine, a coverage collector, a model benchmark,
or platform/deployment qualification. Future increments can add deliberately
reviewed application contracts, scope-complete receipts, packaged consumers and
wider investigations. Preserve survivors and missing evidence throughout.
