from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def _load_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "record_release_evidence.py"
    spec = importlib.util.spec_from_file_location("record_release_evidence", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_evidence_validators_accept_one_clean_commit() -> None:
    module = _load_module()
    commit = "abc123def456"

    module._validate_test_report(
        {
            "git_commit": commit,
            "git_dirty": False,
            "suites": [{"name": "deterministic", "exit_code": 0}],
        },
        commit=commit,
    )
    module._validate_security_report(
        {
            "git_commit": commit,
            "git_dirty": False,
            "results": [
                {
                    "architecture": "safe-web-research",
                    "attack_successes": 0,
                    "forbidden_network_executed": 0,
                    "secret_exfiltration_accepted": 0,
                    "shell_actions_accepted": 0,
                    "invalid_provenance_accepted": 0,
                    "action_smuggling_accepted": 0,
                    "benign_tasks_completed": 10,
                    "benign_cases": 10,
                }
            ],
        },
        commit=commit,
    )
    module._validate_quality_report(
        {
            "git_commit": commit,
            "git_dirty": False,
            "model": "z-ai/glm-5.3-flash",
            "passed_cases": 5,
            "total_cases": 5,
        },
        commit=commit,
        model="z-ai/glm-5.3-flash",
    )


def test_release_evidence_rejects_mixed_commits() -> None:
    module = _load_module()

    with pytest.raises(SystemExit, match="expected"):
        module._validate_test_report(
            {
                "git_commit": "old-commit",
                "git_dirty": False,
                "suites": [{"exit_code": 0}],
            },
            commit="release-commit",
        )


def test_release_evidence_rejects_security_regression() -> None:
    module = _load_module()

    with pytest.raises(SystemExit, match="forbidden action"):
        module._validate_security_report(
            {
                "git_commit": "abc123",
                "git_dirty": False,
                "results": [
                    {
                        "architecture": "safe-web-research",
                        "attack_successes": 1,
                        "forbidden_network_executed": 0,
                        "secret_exfiltration_accepted": 0,
                        "shell_actions_accepted": 0,
                        "invalid_provenance_accepted": 0,
                        "action_smuggling_accepted": 0,
                        "benign_tasks_completed": 10,
                        "benign_cases": 10,
                    }
                ],
            },
            commit="abc123",
        )


def test_replace_public_reports_removes_older_generated_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    staging = tmp_path / "staging"
    public = tmp_path / "reports"

    report_map = {}
    for name in ("test_runs", "security_benchmark", "research_quality"):
        source = staging / name
        destination = public / name
        source.mkdir(parents=True)
        destination.mkdir(parents=True)
        (source / "20260920T200000Z.json").write_text("{}")
        (source / "20260920T200000Z.md").write_text("new")
        (source / "latest.json").write_text("{}")
        (source / "latest.md").write_text("new")
        (destination / "README.md").write_text("keep")
        (destination / "old.json").write_text("old")
        (destination / "old.md").write_text("old")
        report_map[name] = destination

    monkeypatch.setattr(module, "_TEMP_ROOT", staging)
    monkeypatch.setattr(module, "_REPORTS", report_map)

    module._replace_public_reports()

    for destination in report_map.values():
        assert (destination / "README.md").read_text() == "keep"
        assert not (destination / "old.json").exists()
        assert not (destination / "old.md").exists()
        assert (destination / "latest.json").exists()
        assert (destination / "latest.md").read_text() == "new"
