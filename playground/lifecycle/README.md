# Swift ExpenseGuard lifecycle — R6

This local slice takes a named change from a frozen native baseline through real
red acceptance, repaired implementation, preserved old tests, assessment and an
independently consumed local verifier archive. It uses Swift for domain code,
compiled artifacts and acceptance execution. Python3.12+ is development orchestration; Python application execution remains pinned3.14.7.

## Run

Use the same exact SDK environment described in the parent playground guide.
Python3.14.7 and Rust1.98.1 are available in the family's isolated task caches;
Rust honors an explicit RUSTUP_TOOLCHAIN. Swift6.4 and locked Kotlin2.4.20 / Java21
remain required. No SDK or package installation from the network occurs here.

```sh
python3 -m unittest discover -s playground/lifecycle -p 'test_*.py' -v
python3 playground/lifecycle/run.py --output ../brainstorm/astra/evidence/native-lifecycle-a-fresh-run
python3 playground/lifecycle/run.py --review artifacts/lifecycle/a-fresh-run/run.json
```

Evidence must be outside the producer tree and its ancestors, in a fresh path
with no symlink context. Choose fresh output each time. Exit0 means the bounded lifecycle completed;1
means an observed failure;2 means incomplete/stale evidence or a pin gap;3 means
tool/infrastructure failure. The versioned run.json has schema
assay-native-lifecycle/0.1 and explicit completed, verdict, source, toolchain,
baseline, red, candidate, consumer, assessment and controls. run.sha256 binds
receipt bytes. Review rejects changed source, missing/altered baseline receipts,
binaries, installed verifier modules, package archives or raw logs.

## Named requirement and baseline

change-request.json registers only R6: nonblank memos contain at most200Unicode
scalar values, evaluated after the existing policy/amount/currency/blank checks
(R1-R4) and before approval/review (R5). Existing operation and closed outcome
cases remain. Inputs in this fixture are well-formed Unicode strings, with no
byte-decoder claim. The implementation counts native scalar values rather than
UTF16 code units or user-perceived graphemes.

baseline/ preserves the exact original domain, harness and five requirements.
baseline-manifest.json binds those files to their declared original Git commit;
intake compares the actual Git bytes and refuses altered frozen inputs. The old
contract and all twelve named tests/minimum remain frozen. The new requirements
and acceptance JSON retain every old case and add ten memo/precedence cases.
This is an explicitly implemented R6 change, not arbitrary prose-to-code generation.

For each run the old domain is compiled **once** into a separate native artifact:
Python sourceless .pyc, Rust rlib, Swift testable module/shared library or Kotlin
JAR. The original twelve tests pass against it. The expanded22-case harness then
links/imports **that same unchanged artifact**;201ASCII,201astral and202combining
scalar cases fail as ordinary acceptance failures. Compiler success is required
before a red result is interpreted. The repaired authored domain is compiled into
a different artifact; all22 expanded cases and the unchanged original12 pass.
The original library hash is checked again. Raw red failures remain retained.

A separate deliberately wrong old-test expectation actually fails against the
frozen old artifact. Missing baseline, failed baseline, stale source, changed
artifact, changed contract and reduced old selection cannot receive ReadyForReview.
Nine focused protocol/retained-artifact tests also cover duplicate names, unknown
probes, invalid budgets, altered frozen Git inputs and missing/tampered logs.
Advice names only the registered memo-scalar-boundary investigation; it cannot
execute a command, waive a requirement or grant checker authority.

## Packed verifier consumer

The existing SwiftPM manifest, Sources, Tests and license are packed into a source archive. A new consumer extracts it, builds its own Release verifier with a separate scratch directory and executes that installed binary against copied candidate domain source.

Archive, actual installed modules/binaries, producer source/compiler, commands,
raw output and consumer receipts are bound. Consumer execution imports no producer
source or project references. The copied application's source hash matches the
candidate. The checker receipt remains a narrow lexical observation; the separate native acceptance runs are not promoted to semantic checker authority.

These local archives are not releases or published packages. No new checker rule
was admitted. No coverage, model benchmark, universal purity, complete business
correctness or automatic mutation-equivalence claim is made. Original phase1
mutation experiments and their unresolved survivors remain separate. Human review
and any source/package publication require their own scope.

Review reconstructs actual named native rows from raw logs, verifies every required
compile/artifact/input/contract and installed archive binding, checks the current
pinned compiler, recomputes all six controls and assessment, and rejects projection
mismatches or incomplete schema. Cached ReadyForReview labels and rewritten receipt
checksums cannot override failed raw evidence. The separate review_controls command
uses actual retained red execution as a forged candidate and confirms rejection,
while preserving the original run and every original artifact.

For a source squash or shallow clone, follow the [frozen baseline history instructions](../../docs/SOURCE-PUBLICATION.md).
