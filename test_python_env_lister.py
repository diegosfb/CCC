from pathlib import Path

import pytest

from python_env_lister import PythonEnvLister, create_python_env_list_file


def _create_fake_env(base_path: Path, name: str) -> Path:
    """Create a fake Python environment directory with a python executable."""
    env_path = base_path / name
    python_bin = env_path / "bin"
    python_bin.mkdir(parents=True, exist_ok=True)
    (python_bin / "python").write_text("#!/usr/bin/env python\n", encoding="utf-8")
    return env_path


def test_discover_envs_in_custom_paths(tmp_path: Path) -> None:
    """Discover environments from a custom search path and validate results."""
    _create_fake_env(tmp_path, "envA")
    _create_fake_env(tmp_path, "envB")

    lister = PythonEnvLister(search_paths=[tmp_path], include_system=False)
    environments = lister.discover()

    names = [name for name, _ in environments]
    assert names == ["envA", "envB"]
    assert all("Python executable at" in description for _, description in environments)


def test_write_to_file_creates_expected_output(tmp_path: Path) -> None:
    """Verify that the output file is correctly generated with expected content."""
    _create_fake_env(tmp_path, "envA")
    output_file = tmp_path / "python-env-list.txt"

    lister = PythonEnvLister(search_paths=[tmp_path], include_system=False)
    lister.write_to_file(output_file)

    content = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert content == [
        f"envA: Python executable at {tmp_path / 'envA' / 'bin' / 'python'}",
    ]


def test_create_python_env_list_file_default_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the helper creates python-env-list.txt in the current directory."""
    _create_fake_env(tmp_path, "envA")
    monkeypatch.chdir(tmp_path)

    created_path = create_python_env_list_file(search_paths=[tmp_path], include_system=False)

    assert created_path.name == "python-env-list.txt"
    assert created_path.exists()
    lines = created_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines == [
        f"envA: Python executable at {tmp_path / 'envA' / 'bin' / 'python'}",
    ]
