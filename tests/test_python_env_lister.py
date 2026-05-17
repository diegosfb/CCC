"""Tests for python_env_lister utilities."""

from __future__ import annotations

from types import SimpleNamespace

import python_env_lister


class FakeRunner:
    """A fake subprocess runner for predictable testing."""

    def __init__(self, version_output: str, version_error: str, packages_output: str) -> None:
        """Initialize the fake runner with predetermined outputs."""
        self.version_output = version_output
        self.version_error = version_error
        self.packages_output = packages_output
        self.calls = []

    def __call__(self, args, capture_output, text, check):
        """Return a completed process based on the provided arguments."""
        self.calls.append(args)
        if "--version" in args:
            return SimpleNamespace(stdout=self.version_output, stderr=self.version_error)
        if "pip" in args:
            return SimpleNamespace(stdout=self.packages_output, stderr="")
        raise ValueError("Unexpected command")


def test_build_reproduction_list_includes_packages_and_version() -> None:
    """Ensure reproduction list includes Python version and packages."""
    inspector = python_env_lister.EnvironmentInspector()
    reproduction_list = inspector.build_reproduction_list("Python 3.11.0", ["requests==2.0.0", "numpy==1.26.0"])
    assert reproduction_list[0] == "Python version: Python 3.11.0"
    assert "- requests==2.0.0" in reproduction_list
    assert "- numpy==1.26.0" in reproduction_list


def test_generate_creation_script_creates_expected_file(tmp_path) -> None:
    """Ensure the creation script is written with the right name and content."""
    inspector = python_env_lister.EnvironmentInspector()
    script_path = inspector.generate_creation_script(
        "demo-env",
        ["requests==2.0.0", "numpy==1.26.0"],
        tmp_path,
    )
    assert script_path.name == "demo-env.creation-script.py"
    content = script_path.read_text(encoding="utf-8")
    assert "Creation script for environment \"demo-env\"" in content
    assert "requests==2.0.0" in content
    assert "numpy==1.26.0" in content


def test_get_python_version_prefers_stdout_and_falls_back_to_stderr() -> None:
    """Ensure Python version extraction works for stdout and stderr."""
    runner_stdout = FakeRunner("Python 3.10.1\n", "", "package==1.0\n")
    inspector_stdout = python_env_lister.EnvironmentInspector(runner_stdout)
    assert inspector_stdout.get_python_version("python") == "Python 3.10.1"

    runner_stderr = FakeRunner("", "Python 3.9.9\n", "package==1.0\n")
    inspector_stderr = python_env_lister.EnvironmentInspector(runner_stderr)
    assert inspector_stderr.get_python_version("python") == "Python 3.9.9"


def test_get_installed_packages_parses_freeze_output() -> None:
    """Ensure pip freeze output is parsed into a clean list."""
    runner = FakeRunner("Python 3.10.1\n", "", "requests==2.0.0\n\nnumpy==1.26.0\n")
    inspector = python_env_lister.EnvironmentInspector(runner)
    packages = inspector.get_installed_packages("python")
    assert packages == ["requests==2.0.0", "numpy==1.26.0"]
