"""Utilities for inspecting Python environments and creating reproduction scripts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Sequence


class EnvironmentInspector:
    """Collects details about Python environments and generates reproduction assets."""

    def __init__(self, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> None:
        """Initialize the inspector with a subprocess runner."""
        self._runner = runner

    def get_python_version(self, python_executable: str) -> str:
        """Return the Python version for the provided executable."""
        result = self._runner(
            [python_executable, "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        # The version can appear in stdout or stderr depending on the platform.
        output = result.stdout.strip() or result.stderr.strip()
        return output

    def get_installed_packages(self, python_executable: str) -> List[str]:
        """Return a list of installed packages for the provided executable."""
        result = self._runner(
            [python_executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Filter out empty lines to avoid blank entries.
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def build_reproduction_list(self, python_version: str, packages: Sequence[str]) -> List[str]:
        """Build a list describing the configuration and installations needed."""
        reproduction_list = [f"Python version: {python_version}", "Installations:"]
        if packages:
            reproduction_list.extend(f"- {package}" for package in packages)
        else:
            reproduction_list.append("- No third-party packages detected.")
        return reproduction_list

    def generate_creation_script(
        self,
        env_name: str,
        packages: Sequence[str],
        output_dir: str | Path,
    ) -> Path:
        """Generate a creation script for the given environment name."""
        output_path = Path(output_dir) / f"{env_name}.creation-script.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        script_content = create_creation_script_content(env_name, packages)
        output_path.write_text(script_content, encoding="utf-8")
        return output_path


def create_creation_script_content(env_name: str, packages: Sequence[str]) -> str:
    """Create the content for a Python environment creation script."""
    packages_list = list(packages)
    return (
        f'"""Creation script for environment \"{env_name}\"."""\n\n'
        "import os\n"
        "import subprocess\n"
        "import sys\n"
        "from pathlib import Path\n\n"
        "def _get_pip_executable(env_path: Path) -> Path:\n"
        "    \"\"\"Return the pip executable path for the environment.\"\"\"\n"
        "    if os.name == \"nt\":\n"
        "        return env_path / \"Scripts\" / \"pip\"\n"
        "    return env_path / \"bin\" / \"pip\"\n\n"
        "def main() -> None:\n"
        "    \"\"\"Create the virtual environment and install required packages.\"\"\"\n"
        f"    env_path = Path(\"{env_name}\")\n"
        "    if not env_path.exists():\n"
        "        subprocess.run([sys.executable, \"-m\", \"venv\", str(env_path)], check=True)\n"
        "    pip_executable = _get_pip_executable(env_path)\n"
        f"    packages = {packages_list!r}\n"
        "    if packages:\n"
        "        subprocess.run([str(pip_executable), \"install\", *packages], check=True)\n\n"
        "if __name__ == \"__main__\":\n"
        "    main()\n"
    )


def generate_environment_assets(
    env_name: str,
    python_executable: str,
    output_dir: str | Path,
    inspector: EnvironmentInspector | None = None,
) -> dict:
    """Generate reproduction details and a creation script for an environment."""
    inspector = inspector or EnvironmentInspector()
    python_version = inspector.get_python_version(python_executable)
    packages = inspector.get_installed_packages(python_executable)
    reproduction_list = inspector.build_reproduction_list(python_version, packages)
    script_path = inspector.generate_creation_script(env_name, packages, output_dir)
    return {"reproduction_list": reproduction_list, "script_path": script_path}


def main() -> None:
    """Command-line entry point for generating environment reproduction assets."""
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python python_env_lister.py <env-name> [python-executable] [output-dir]")
    env_name = sys.argv[1]
    python_executable = sys.argv[2] if len(sys.argv) > 2 else sys.executable
    output_dir = sys.argv[3] if len(sys.argv) > 3 else os.getcwd()
    assets = generate_environment_assets(env_name, python_executable, output_dir)
    for line in assets["reproduction_list"]:
        print(line)
    print(f"Creation script written to: {assets['script_path']}")


if __name__ == "__main__":
    main()
