"""Exercise the real aggregate step with dependency results, including cancellations."""

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml


WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/ci.yaml"


@pytest.fixture
def evaluate(tmp_path):
    # Execute the workflow's shell command so the test covers its exit status
    # and GitHub output, not a second implementation of the decision logic.
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    gate = workflow["jobs"]["all-checks-pass"]
    step = next(step for step in gate["steps"] if step.get("id") == "evaluate")

    def run(results):
        output = tmp_path / "github-output"
        process = subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step["run"]],
            env={
                **os.environ,
                "NEEDS": json.dumps({name: {"result": result} for name, result in results.items()}),
                "GITHUB_OUTPUT": str(output),
            },
            capture_output=True,
            text=True,
            timeout=10,
        )
        emitted = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines())
        assert json.loads(emitted["needs-json"]) == results
        return process

    return run


@pytest.mark.parametrize("result", ["success", "skipped"])
def test_completed_or_intentionally_skipped_lanes_pass(evaluate, result):
    process = evaluate({"detect": "success", "tests": result, "e2e-desktop": "skipped"})
    assert process.returncode == 0, process.stdout + process.stderr


@pytest.mark.parametrize(
    "result",
    ["failure", "cancelled", "timed_out", "action_required", "neutral", "unknown", "", None],
)
def test_any_unacceptable_dependency_blocks_the_gate(evaluate, result):
    process = evaluate({"detect": "success", "tests": result, "docs-site": "skipped"})
    assert process.returncode != 0, process.stdout + process.stderr
    assert "::error::" in process.stdout
    assert "tests" in process.stdout
