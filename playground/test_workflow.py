"""Negative controls for evidence interpretation, freshness and offline advice."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from advice import decide
from run import digest, observe
from review import review, snapshot


class AdviceTests(unittest.TestCase):
    def test_boundary_survivor_selects_only_registered_probe(self):
        observed = {"baseline": "Pass", "compilation": "Pass", "original": "Survived", "expanded": "Killed", "probeId": "zero-amount"}
        self.assertEqual(decide(observed)["kind"], "ProbeRequested")
        self.assertEqual(decide(observed, budget=0)["kind"], "BudgetExhausted")
        self.assertEqual(decide(observed, fresh=False)["kind"], "ContextRequired")
        self.assertEqual(decide(dict(observed, probeId="run-shell"))["kind"], "ContextRequired")

    def test_survivor_invalid_mutation_and_failed_baseline_cannot_grant_pass(self):
        self.assertEqual(decide({"baseline": "Fail"})["kind"], "ContextRequired")
        self.assertEqual(decide({"baseline": "Pass", "compilation": "Fail"})["kind"], "ContextRequired")
        self.assertEqual(decide({"baseline": "Pass", "compilation": "Pass", "expanded": "Survived"})["kind"], "SurvivorReview")
        self.assertEqual(decide({"baseline": "Pass", "compilation": "Pass", "original": "Killed", "expanded": "Killed"})["kind"], "NoInvestigation")


class EvidenceTests(unittest.TestCase):
    def execution(self, text, code=0, status="Completed"):
        return {"stdout": text, "exitCode": code, "status": status}

    def test_missing_duplicate_foreign_timeout_or_crash_output_never_passes(self):
        for result in [self.execution(""), self.execution("CASE\ta\tPASS\nCASE\ta\tPASS"),
                       self.execution("CASE\tforeign\tPASS"), self.execution("CASE\ta\tPASS", status="Timeout"),
                       self.execution("CASE\ta\tPASS", code=-11)]:
            self.assertNotEqual(observe(result, ["a"])["verdict"], "Pass")

    def test_named_failures_and_exit_codes_must_agree(self):
        self.assertEqual(observe(self.execution("CASE\ta\tFAIL", 1), ["a"])["verdict"], "Fail")
        self.assertEqual(observe(self.execution("CASE\ta\tFAIL", 0), ["a"])["verdict"], "ToolFailure")
        self.assertEqual(observe(self.execution("CASE\ta\tPASS", 0), ["a"])["verdict"], "Pass")

    def test_source_and_log_drift_make_a_recorded_pass_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "execution.log"
            log.write_text("original output")
            receipt = root / "run.json"
            report = {"schema": "assay-playground/0.1", "source": snapshot(), "verdict": "Pass", "completed": True,
                      "execution": {"log": str(log), "logSha256": digest(log.read_bytes())}}
            def save():
                receipt.write_text(json.dumps(report))
                receipt.with_suffix(".sha256").write_text(digest(receipt.read_bytes()))
            save()
            self.assertEqual(review(receipt)["state"], "ReadyForReview")
            log.write_text("changed output")
            self.assertEqual(review(receipt)["state"], "NotAvailable")
            log.write_text("original output")
            report["source"]["expenseguard/domain/missing"] = "bad"
            save()
            self.assertEqual(review(receipt)["state"], "NotAvailable")
            receipt.write_text("changed receipt")
            self.assertEqual(review(receipt)["state"], "NotAvailable")


if __name__ == "__main__":
    unittest.main()
