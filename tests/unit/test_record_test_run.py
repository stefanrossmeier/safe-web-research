from __future__ import annotations

import sys

from scripts.record_test_run import _public_command


def test_public_command_replaces_local_python_and_removes_junit_path() -> None:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--junitxml=/private/tmp/example.xml",
    ]

    assert _public_command(command) == [
        "uv",
        "run",
        "python",
        "-m",
        "pytest",
        "-q",
    ]


def test_public_command_preserves_portable_non_python_command() -> None:
    command = ["git", "status", "--short"]

    assert _public_command(command) == command
