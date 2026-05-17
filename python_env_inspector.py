"""Utilities for inspecting Python environments on macOS."""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

import importlib.metadata


@dataclass(frozen=True)
class EnvironmentInfo:
    """Represents a discovered Python environment."""

    name: str
    path: Path
    python_executable: Path
    env_type: str


class PythonEnvironmentInspector:
    """Discover and describe Python environments for reproducibility."""

    def __init__(
        self,
        env_var_paths: str = "PYTHON_ENV_PATHS",
        version_getter: Optional[Callable[[EnvironmentInfo], Optional[str]]] = None,
        packages_getter: Optional[Callable[[EnvironmentInfo], List[str]]] = None,
    ) -> None:
        """Initialize the inspector with optional dependency injection.

        Args:
            env_var_paths: The environment variable that lists additional env paths.
            version_getter: Optional callable to resolve python versions.
            packages_getter: Optional callable to resolve installed packages.
        """
        self._env_var_paths = env_var_paths
        self._version_getter = version_getter or self._default_version_getter
        self._packages_getter = packages_getter or self._default_packages_getter

    def discover_environments(self) -> List[EnvironmentInfo]:
        """Discover available Python environments.

        Returns:
            A list of EnvironmentInfo objects describing each environment.
        """
        environments: List[EnvironmentInfo] = []

        # Always include the current environment.
        current_env = self._build_current_environment()
        environments.append(current_env)

        # Include additional environments defined via env var.
        env_paths = os.environ.get(self._env_var_paths, "")
        for raw_path in filter(None, env_paths.split(os.pathsep)):
            env_path = Path(raw_path).expanduser().resolve()
            python_executable = env_path / "bin" / "python"
            if python_executable.exists():
                environments.append(
                    EnvironmentInfo(
                        name=env_path.name or "custom",
                        path=env_path,
                        python_executable=python_executable,
                        env_type="custom",
                    )
                )

        return environments

    def get_reproduction_configuration(self, env: EnvironmentInfo) -> Dict[str, object]:
        """Generate a configuration describing how to reproduce an environment.

        Args:
            env: The environment to describe.

        Returns:
            A dictionary with python version and package requirements.
        """
        return {
            "name": env.name,
            "path": str(env.path),
            "env_type": env.env_type,
            "python_version": self._version_getter(env),
            "packages": self._packages_getter(env),
        }

    def _build_current_environment(self) -> EnvironmentInfo:
        """Build the EnvironmentInfo for the current interpreter."""
        current_path = Path(sys.prefix).resolve()
        python_executable = Path(sys.executable).resolve()
        env_type = self._detect_current_env_type()
        name = current_path.name or "current"
        return EnvironmentInfo(
            name=name,
            path=current_path,
            python_executable=python_executable,
            env_type=env_type,
        )

    def _detect_current_env_type(self) -> str:
        """Detect whether the current environment is conda, venv, or system."""
        current_prefix = Path(sys.prefix).resolve()
        if os.environ.get("CONDA_PREFIX") == str(current_prefix):
            return "conda"
        if os.environ.get("VIRTUAL_ENV") == str(current_prefix):
            return "venv"
        return "system"

    def _default_version_getter(self, env: EnvironmentInfo) -> Optional[str]:
        """Resolve the python version for the current environment.

        Args:
            env: The environment being queried.

        Returns:
            The python version string if resolvable, otherwise None.
        """
        if env.python_executable == Path(sys.executable).resolve():
            return platform.python_version()
        return None

    def _default_packages_getter(self, env: EnvironmentInfo) -> List[str]:
        """Resolve packages for the current environment.

        Args:
            env: The environment being queried.

        Returns:
            A sorted list of packages for the current environment, or empty list.
        """
        if env.python_executable != Path(sys.executable).resolve():
            return []

        packages: List[str] = []
        for dist in importlib.metadata.distributions():
            name = dist.metadata.get("Name", "")
            if name:
                packages.append(f"{name}=={dist.version}")

        return sorted(packages)
