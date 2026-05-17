import json
import os
import subprocess
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional


@dataclass
class PythonEnvironment:
    """Represents a Python environment and provides inspection utilities."""

    name: str
    path: str
    python_executable: str

    def get_python_version(self, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> str:
        """Return the Python version for this environment."""
        completed = runner(
            [self.python_executable, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        output = (completed.stdout or "").strip() or (completed.stderr or "").strip()
        return output.replace("Python ", "", 1) if output.startswith("Python ") else output

    def get_installed_packages(
        self, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run
    ) -> List[str]:
        """Return a sorted list of installed packages (pip freeze format)."""
        completed = runner(
            [self.python_executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=False,
        )
        packages = [line.strip() for line in (completed.stdout or "").splitlines() if line.strip()]
        return sorted(packages)

    def generate_reproduction_instructions(
        self, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run
    ) -> Dict[str, Iterable[str]]:
        """Generate a list of configuration and installation steps to reproduce the environment."""
        python_version = self.get_python_version(runner)
        packages = self.get_installed_packages(runner)
        instructions = {
            "python_version": python_version,
            "packages": packages,
            "create_command": f"python -m venv {self.name}",
            "activate_command": f"source {self.name}/bin/activate",
            "install_command": "pip install -r requirements.txt",
        }
        return instructions


class PythonEnvironmentLister:
    """Finds Python environments and retrieves reproduction details."""

    def __init__(
        self,
        search_paths: Optional[Iterable[str]] = None,
        file_system: Optional[object] = None,
    ) -> None:
        """Initialize the lister with search paths and a filesystem module."""
        self.search_paths = list(search_paths) if search_paths else [os.path.expanduser("~")]
        self.file_system = file_system or os

    def find_environments(self) -> List[PythonEnvironment]:
        """Discover Python environments under the configured search paths."""
        environments: List[PythonEnvironment] = []
        for root_path in self.search_paths:
            for dirpath, _, filenames in self.file_system.walk(root_path):
                if "pyvenv.cfg" not in filenames:
                    continue
                python_executable = self._python_executable_for_env(dirpath)
                if not python_executable:
                    continue
                name = self.file_system.path.basename(dirpath)
                environments.append(PythonEnvironment(name=name, path=dirpath, python_executable=python_executable))
        return environments

    def _python_executable_for_env(self, env_path: str) -> Optional[str]:
        """Return the python executable for a virtual environment, if it exists."""
        candidate = self.file_system.path.join(env_path, "bin", "python")
        if self.file_system.path.isfile(candidate):
            return candidate
        return None


def list_available_environments(
    search_paths: Optional[Iterable[str]] = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> List[Dict[str, object]]:
    """Return a list of environment details ready for reporting."""
    lister = PythonEnvironmentLister(search_paths=search_paths)
    results: List[Dict[str, object]] = []
    for environment in lister.find_environments():
        reproduction = environment.generate_reproduction_instructions(runner)
        results.append(
            {
                "name": environment.name,
                "path": environment.path,
                "python_executable": environment.python_executable,
                "reproduction": reproduction,
            }
        )
    return results


def main() -> None:
    """Entry point that prints environment details as JSON."""
    environments = list_available_environments()
    print(json.dumps(environments, indent=2))


if __name__ == "__main__":
    main()
