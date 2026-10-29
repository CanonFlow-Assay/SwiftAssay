#!/usr/bin/env python3
"""Execute a bounded native experiment; never rewrite the checked-in domain."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from advice import decide


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def snapshot() -> dict:
    files = sorted(p for p in HERE.rglob("*") if p.is_file()
                   and "__pycache__" not in p.parts and ".kotlinassay" not in p.parts)
    files += [ROOT / name for name in ("pyproject.toml", "Cargo.lock", "rust-toolchain.toml", "Package.swift", ".swift-version", "toolchain.lock.json") if (ROOT / name).is_file()]
    return {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sorted(files)}


def execute(argv: list[str], cwd: Path, log: Path, env: dict | None = None) -> dict:
    try:
        done = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=90)
        stdout, stderr = done.stdout, done.stderr
        status = "Completed"
        code = done.returncode
    except FileNotFoundError as error:
        stdout, stderr, code, status = b"", str(error).encode(), None, "Unavailable"
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code, status = error.stdout or b"", error.stderr or b"", None, "Timeout"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_bytes(stdout + b"\n--- stderr ---\n" + stderr)
    return {"argv": argv, "status": status, "exitCode": code,
            "stdoutSha256": digest(stdout), "stderrSha256": digest(stderr),
            "logSha256": digest(log.read_bytes()), "log": str(log),
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace")}


def observe(result: dict, expected: list[str]) -> dict:
    rows = [line.split("\t") for line in result["stdout"].splitlines()]
    valid = (result["status"] == "Completed" and len(rows) == len(expected)
             and all(len(row) == 3 and row[0] == "CASE" and row[1] == name
                     and row[2] in ("PASS", "FAIL") for row, name in zip(rows, expected)))
    if not valid:
        return {"verdict": "Inconclusive", "reason": "Missing, duplicate or malformed named test output.",
                "execution": result}
    failed = [row[1] for row in rows if row[2] == "FAIL"]
    if result["exitCode"] != (1 if failed else 0):
        return {"verdict": "ToolFailure", "reason": "Exit status disagrees with named test results.",
                "execution": result}
    return {"verdict": "Fail" if failed else "Pass", "tests": len(rows), "failed": failed,
            "execution": result}


def toolchain(language: str, output: Path) -> tuple[dict, list[str], list[str]]:
    if language == "Python":
        compiler = [shutil.which("python3.14") or sys.executable]
        version_args, pin = ["--version"], "3.14.7"
    elif language == "Rust":
        # Use an already installed toolchain; never let rustup download the unavailable pin.
        location = subprocess.run(["rustup", "which", "--toolchain", "stable", "rustc"],
                                  capture_output=True, text=True, timeout=10)
        compiler = [location.stdout.strip()] if location.returncode == 0 else ["rustc"]
        version_args, pin = ["--version"], "1.98.1"
    elif language == "Swift":
        compiler = [shutil.which("swiftc") or "swiftc"]
        version_args, pin = ["--version"], "6.4"
    else:
        lock = json.loads((ROOT / "toolchain.lock.json").read_text())
        home = Path(lock["compilerHome"])
        # The existing lock owns compiler bytes; a version string alone is insufficient.
        for name, expected in lock["compilerFilesSha256"].items():
            if digest((home / name).read_bytes()) != expected:
                raise ValueError("Pinned Kotlin compiler bytes changed: " + name)
        compiler = [str(home / "bin/kotlinc")]
        version_args, pin = ["-version"], lock["kotlinVersion"]
    version = execute(compiler + version_args, ROOT, output / "toolchain.log")
    text = version["stdout"] + version["stderr"]
    exact = bool(re.search(r"(?<![0-9.])" + re.escape(pin) + r"(?![0-9.])", text))
    if language == "Kotlin":
        java = execute(["java", "-version"], ROOT, output / "java.log")
        exact = exact and "21.0.12.1" in java["stderr"]
    else:
        java = None
    record = {"runtimePin": pin, "observed": text.strip(), "exactPinQualified": exact,
              "execution": version, "java": java}
    record["compilerExecutableSha256"] = digest(Path(compiler[0]).resolve().read_bytes())
    return record, compiler, []


def build(language: str, compiler: list[str], domain: str, harness: str,
          work: Path, log: Path) -> tuple[dict, list[str]]:
    work.mkdir(parents=True)
    names = {"Python": ("expense.py", "main.py"), "Rust": ("expense.rs", "main.rs"),
             "Swift": ("Expense.swift", "main.swift"), "Kotlin": ("Expense.kt", "Main.kt")}
    domain_name, harness_name = names[language]
    (work / domain_name).write_text(domain, encoding="utf-8")
    (work / harness_name).write_text(harness, encoding="utf-8")
    if language == "Python":
        result = execute(compiler + ["-I", "-c", "import ast,pathlib; [ast.parse(pathlib.Path(p).read_text()) for p in ['expense.py','main.py']]"], work, log)
        command = compiler + ["-B", str(work / harness_name)]
        executable = work / domain_name
    elif language == "Rust":
        executable = work / "tests"
        result = execute(compiler + ["--edition=2024", "-Dwarnings", harness_name, "-o", str(executable)], work, log)
        command = [str(executable)]
    elif language == "Swift":
        executable = work / "tests"
        result = execute(compiler + ["-swift-version", "6", "-warnings-as-errors", domain_name,
                                    harness_name, "-o", str(executable)], work, log)
        command = [str(executable)]
    else:
        executable = work / "tests.jar"
        result = execute(compiler + [domain_name, harness_name, "-jvm-target", "21", "-Werror",
                                    "-include-runtime", "-d", str(executable)], work, log)
        command = ["java", "-jar", str(executable)]
    if executable.is_file():
        result["executableSha256"] = digest(executable.read_bytes())
    return result, command


def run(args: argparse.Namespace, output: Path) -> dict:
    config = json.loads((HERE / "config.json").read_text())
    language = config["language"]
    requirements = json.loads((HERE / "expenseguard/requirements.json").read_text())
    initial = snapshot()
    domain = (HERE / config["domain"]).read_text()
    harness = (HERE / config["harness"]).read_text()
    report = {"schema": "assay-playground/0.1", "application": "ExpenseGuard", "language": language,
              "authority": "Bounded native experiment; advice cannot grant a checker verdict or release approval.",
              "source": initial, "sourceSnapshotSha256": digest(json.dumps(initial, sort_keys=True).encode()),
              "requirementsSha256": digest((HERE / "expenseguard/requirements.json").read_bytes()),
              "mutations": [], "verdict": "Inconclusive", "completed": False,
              "staticVerification": "NotCollected; use the documented existing checker command separately."}
    write_json(output / "run.json", report)
    tooling, compiler, _ = toolchain(language, output)
    report["toolchain"] = tooling
    build_result, command = build(language, compiler, domain, harness, output / "work/original", output / "original-build.log")
    report["originalBuild"] = build_result
    if build_result["exitCode"] != 0:
        report["reason"] = "Original sample failed compilation or tool execution."
        report["verdict"] = "ToolFailure" if build_result["status"] == "Completed" else "Inconclusive"
        return report
    report["baseline"] = {}
    for selection in ("baseline", "expanded"):
        record = execute(command + [selection], output / "work/original", output / ("original-" + selection + ".log"))
        report["baseline"][selection] = observe(record, requirements["selections"][selection])
    if any(item["verdict"] != "Pass" for item in report["baseline"].values()):
        report["reason"] = "Failed original baseline; no mutation advice is eligible."
        observed_verdicts = [item["verdict"] for item in report["baseline"].values()]
        report["verdict"] = "ToolFailure" if "ToolFailure" in observed_verdicts else "Inconclusive" if "Inconclusive" in observed_verdicts else "Fail"
        return report
    for mutation in config["mutations"]:
        record = {"id": mutation["id"], "requirement": mutation["requirement"]}
        before, after = mutation["before"], mutation["after"]
        if domain.count(before) != 1:
            raise ValueError("Mutation needs one exact source anchor: " + mutation["id"])
        changed = domain.replace(before, after, 1)
        work = output / "work" / mutation["id"]
        built, mutated_command = build(language, compiler, changed, harness, work, output / (mutation["id"] + "-build.log"))
        record["sourceSha256"], record["build"] = digest(changed.encode()), built
        observation = {"baseline": "Pass", "probeId": mutation.get("probeId")}
        if built["exitCode"] != 0:
            record["outcome"] = "InvalidMutation" if built["status"] == "Completed" else "Incomplete"
            observation["compilation"] = "Fail" if built["status"] == "Completed" else "Incomplete"
        else:
            observation["compilation"] = "Pass"
            for selection in ("baseline", "expanded"):
                observed = observe(execute(mutated_command + [selection], work,
                                   output / (mutation["id"] + "-" + selection + ".log")),
                                   requirements["selections"][selection])
                record[selection] = observed
                observation["original" if selection == "baseline" else "expanded"] = {
                    "Pass": "Survived", "Fail": "Killed"}.get(observed["verdict"], "Incomplete")
            record["outcome"] = observation["expanded"]
        record["observation"] = observation
        record["advice"] = decide(observation, args.budget)
        record["expectedObservation"] = mutation["expected"]
        record["metExpectation"] = all(observation.get(k) == v for k, v in mutation["expected"].items())
        report["mutations"].append(record)
        write_json(output / "run.json", report)
    # An actual failed original is a context-repair control, never a mutation kill.
    control_domain = domain.replace("amount <= 0", "amount <= 5000", 1)
    control_build, control_command = build(language, compiler, control_domain, harness,
        output / "work/failed-baseline", output / "failed-baseline-build.log")
    control_observed = observe(execute(control_command + ["baseline"], output / "work/failed-baseline",
        output / "failed-baseline.log"), requirements["selections"]["baseline"]) if control_build["exitCode"] == 0 else {"verdict": "Inconclusive"}
    report["failedBaselineControl"] = {"build": control_build, "observation": control_observed,
        "advice": decide({"baseline": control_observed["verdict"]}, args.budget),
        "metExpectation": control_observed["verdict"] == "Fail"}
    report["sourceUnchanged"] = initial == snapshot()
    report["completed"] = report["sourceUnchanged"] and all(x["metExpectation"] for x in report["mutations"]) and report["failedBaselineControl"]["metExpectation"]
    if not report["sourceUnchanged"]:
        report["verdict"], report["reason"] = "Inconclusive", "Source changed while collecting evidence."
        for mutation in report["mutations"]:
            mutation["advice"] = decide(mutation["observation"], args.budget, fresh=False)
    elif any(m.get(selection, {}).get("verdict") == "ToolFailure" for m in report["mutations"] for selection in ("baseline", "expanded")):
        report["verdict"], report["reason"] = "ToolFailure", "Native output and exit status disagree."
    elif any(m["outcome"] == "Incomplete" or m["observation"].get("compilation") == "Incomplete" for m in report["mutations"]) or control_observed["verdict"] == "Inconclusive":
        report["verdict"], report["reason"] = "Inconclusive", "A native execution is missing, interrupted or incomplete."
    elif not report["completed"]:
        report["verdict"], report["reason"] = "Fail", "An observed experiment differs from its registered expectation."
    elif not tooling["exactPinQualified"]:
        report["verdict"], report["reason"] = "Inconclusive", "Experiment completed on the recorded runtime; exact pinned runtime is unavailable."
    else:
        report["verdict"] = "Pass"
    report["nonclaims"] = ["Not a replacement for existing checker verification.",
        "Survivors are not automatic equivalence findings.", "No general mutation engine, coverage measurement, security or business correctness proof.",
        "No provider calls, package publication, or real payments."]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Fresh evidence directory (must not exist).")
    parser.add_argument("--budget", type=int, default=3, help="Offline advice proposal budget; no automatic execution.")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Evidence output already exists; choose a fresh directory.")
    if HERE == output or HERE in output.parents:
        parser.error("Evidence must be outside playground source (use artifacts/playground/<run> or /tmp).")
    if args.budget < 0:
        parser.error("Budget must be nonnegative.")
    output.mkdir(parents=True)
    try:
        report = run(args, output)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report = json.loads((output / "run.json").read_text()) if (output / "run.json").exists() else {}
        report.update(verdict="ToolFailure", completed=False, reason=str(error))
    write_json(output / "run.json", report)
    (output / "run.sha256").write_text(digest((output / "run.json").read_bytes()) + "\n")
    print(json.dumps({"verdict": report["verdict"], "completed": report["completed"], "receipt": str(output / "run.json")}))
    return {"Pass": 0, "Fail": 1, "Inconclusive": 2, "ToolFailure": 3}[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
