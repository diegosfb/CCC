"""Tests for the Python environment inspector."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, List

import importlib.metadata
import pytest

from python_env_inspector import EnvironmentInfo, PythonEnvironmentInspector


class DummyDistribution:
    """Simple distribution stub for testing package discovery."""

    def __init__(self, name: str, version: str) -> None:
        """Initialize the dummy distribution.

        Args:
            name: The distribution name.
            version: The distribution version.
        """
        self.metadata = {"Name": name}
        self.version = version


def test_discover_includes_current_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The inspector should always include the current environment."""
    monkeypatch.setenv("VIRTUAL_ENV", str(Path(sys.prefix).resolve()))
    inspector = PythonEnvironmentInspector()

    environments = inspector.discover_environments()

    assert environments
    current_env = environments[0]
    assert current_env.path == Path(sys.prefix).resolve()
    assert current_env.env_type == "venv"


def test_discover_additional_envs_from_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Additional environments can be provided through an env variable."""
    custom_env = tmp_path / "custom_env"
    python_executable = custom_env / "bin" / "python"
    python_executable.parent.mkdir(parents=True)
    python_executable.write_text("#!/usr/bin/env python\n")
    python_executable.chmod(0o755)

    monkeypatch.setenv("PYTHON_ENV_PATHS", str(custom_env))
    inspector = PythonEnvironmentInspector()

    environments = inspector.discover_environments()

    assert any(env.path == custom_env for env in environments)
    custom_info = next(env for env in environments if env.path == custom_env)
    assert custom_info.python_executable == python_executable
    assert custom_info.env_type == "custom"


def test_reproduction_configuration_includes_packages(monkeypatch: pytest.MonkeyPatch) -> None:
    """The reproduction configuration should include sorted package strings."""
    dummy_distributions = [
        DummyDistribution("zeta", "1.0.0"),
        DummyDistribution("alpha", "2.0.0"),
    ]

    def fake_distributions() -> Iterable[DummyDistribution]:
        return dummy_distributions

    monkeypatch.setattr(importlib.metadata, "distributions", fake_distributions)
    inspector = PythonEnvironmentInspector()
    current_env = inspector.discover_environments()[0]

    config = inspector.get_reproduction_configuration(current_env)

    assert config["python_version"]
    assert config["packages"] == ["alpha==2.0.0", "zeta==1.0.0"]


def test_non_current_env_has_no_packages(tmp_path: Path) -> None:
    """Non-current environments should not resolve packages by default."""
    other_env = EnvironmentInfo(
        name="other",
        path=tmp_path,
        python_executable=tmp_path / "bin" / "python",
        env_type="custom",
    )
    inspector = PythonEnvironmentInspector()

    config = inspector.get_reproduction_configuration(other_env)

    assert config["packages"] == []
