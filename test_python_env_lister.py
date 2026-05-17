import os
from dataclasses import dataclass

import pytest

from python_env_lister import PythonEnvironment, PythonEnvironmentLister, list_available_environments


@dataclass
class FakeCompletedProcess:
    """Simple stand-in for subprocess.CompletedProcess."""

    stdout: str = ""
    stderr: str = ""


def fake_runner_factory(version_output, freeze_output):
    """Create a fake runner that returns preconfigured outputs."""

    def runner(args, capture_output=True, text=True, check=False):
        if "--version" in args:
            return FakeCompletedProcess(stdout=version_output, stderr="")
        if "pip" in args and "freeze" in args:
            return FakeCompletedProcess(stdout=freeze_output, stderr="")
        return FakeCompletedProcess(stdout="", stderr="")

    return runner


def create_fake_env(tmp_path, name):
    """Create a minimal virtual environment structure."""
    env_path = tmp_path / name
    bin_path = env_path / "bin"
    bin_path.mkdir(parents=True)
    (env_path / "pyvenv.cfg").write_text("home = /usr/bin")
    python_executable = bin_path / "python"
    python_executable.write_text("")
    return env_path


def test_find_environments_detects_virtualenv(tmp_path):
    """Ensure environments are discovered by pyvenv.cfg presence."""
    env_path = create_fake_env(tmp_path, "env_one")
    lister = PythonEnvironmentLister(search_paths=[str(tmp_path)])
    environments = lister.find_environments()
    assert len(environments) == 1
    assert environments[0].path == str(env_path)
    assert environments[0].name == "env_one"


def test_environment_reproduction_instructions(tmp_path):
    """Ensure reproduction details include version and packages."""
    env_path = create_fake_env(tmp_path, "env_two")
    env = PythonEnvironment(name="env_two", path=str(env_path), python_executable=str(env_path / "bin" / "python"))
    runner = fake_runner_factory("Python 3.11.2\n", "requests==2.31.0\npytest==7.4.0\n")
    instructions = env.generate_reproduction_instructions(runner)
    assert instructions["python_version"] == "3.11.2"
    assert instructions["packages"] == ["pytest==7.4.0", "requests==2.31.0"]
    assert instructions["create_command"] == "python -m venv env_two"
    assert instructions["activate_command"] == "source env_two/bin/activate"


def test_list_available_environments_integration(tmp_path):
    """Integration test that returns environment details for reporting."""
    create_fake_env(tmp_path, "env_three")
    runner = fake_runner_factory("Python 3.10.1\n", "flask==2.2.3\n")
    results = list_available_environments(search_paths=[str(tmp_path)], runner=runner)
    assert len(results) == 1
    environment = results[0]
    assert environment["name"] == "env_three"
    assert environment["reproduction"]["python_version"] == "3.10.1"
    assert environment["reproduction"]["packages"] == ["flask==2.2.3"]
    assert os.path.basename(environment["python_executable"]) == "python"
