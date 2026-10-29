#!/usr/bin/env python3
"""Check local receipt integrity and current source freshness without executing code."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run import digest, snapshot


def review(receipt: Path) -> dict:
    raw = receipt.read_bytes()
    expected = receipt.with_suffix(".sha256").read_text().strip()
    if digest(raw) != expected:
        return {"state": "NotAvailable", "verdict": "Inconclusive", "reason": "Receipt digest changed."}
    report = json.loads(raw)
    if report.get("schema") != "assay-playground/0.1":
        return {"state": "NotAvailable", "verdict": "Inconclusive", "reason": "Unsupported receipt schema."}
    if report.get("source") != snapshot():
        return {"state": "NotAvailable", "verdict": "Inconclusive", "reason": "Current source differs from the recorded experiment."}
    records = []
    def collect(value):
        if isinstance(value, dict):
            if "logSha256" in value and "log" in value:
                records.append(value)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
    collect(report)
    root = receipt.parent.resolve()
    for item in records:
        log = Path(item["log"]).resolve()
        if root not in log.parents or not log.is_file() or digest(log.read_bytes()) != item["logSha256"]:
            return {"state": "NotAvailable", "verdict": "Inconclusive", "reason": "Execution log is missing, changed or outside this evidence directory."}
    verdict = report.get("verdict", "Inconclusive")
    ready = report.get("completed") is True and verdict == "Pass"
    return {"state": "ReadyForReview" if ready else "NeedsReview", "verdict": verdict,
            "reason": "Current source and retained logs match the local receipt.",
            "authority": "Local integrity check, not a signature, checker grant or release approval."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    try:
        result = review(args.receipt.resolve())
    except (OSError, ValueError, KeyError) as error:
        result = {"state": "NotAvailable", "verdict": "Inconclusive", "reason": str(error)}
    print(json.dumps(result, sort_keys=True))
    return {"Pass": 0, "Fail": 1, "Inconclusive": 2, "ToolFailure": 3}.get(result["verdict"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
