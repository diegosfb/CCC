from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


class PythonEnvLister:
    """Discover Python environments in known locations and write them to a file."""

    def __init__(self, search_paths: Optional[Iterable[Path]] = None, include_system: bool = True) -> None:
        """Initialize the lister with optional search paths and system inclusion."""
        self.search_paths = (
            [Path(path).expanduser() for path in search_paths]
            if search_paths is not None
            else self.default_search_paths()
        )
        self.include_system = include_system

    def default_search_paths(self) -> List[Path]:
        """Return a list of typical locations for Python environments on macOS."""
        return [
            Path.home() / ".virtualenvs",
            Path.home() / ".pyenv" / "versions",
            Path.home() / "Library" / "Application Support" / "virtualenv",
        ]

    def discover(self) -> List[Tuple[str, str]]:
        """Discover available Python environments and return name/description pairs."""
        environments = {}
        if self.include_system:
            environments["system"] = f"Python executable at {sys.executable}"

        for base_path in self.search_paths:
            if not base_path.exists():
                continue
            for child in base_path.iterdir():
                if not child.is_dir():
                    continue
                python_path = self._find_python_executable(child)
                if python_path is not None:
                    environments[child.name] = f"Python executable at {python_path}"

        return sorted(environments.items(), key=lambda item: item[0].lower())

    def write_to_file(self, output_path: Path) -> None:
        """Write the discovered Python environments to a text file."""
        environments = self.discover()
        lines = [f"{name}: {description}" for name, description in environments]
        content = "\n".join(lines)
        if lines:
            content += "\n"
        output_path.write_text(content, encoding="utf-8")

    def _find_python_executable(self, env_path: Path) -> Optional[Path]:
        """Find a Python executable within a candidate environment directory."""
        candidates = [env_path / "bin" / "python", env_path / "bin" / "python3"]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None


def create_python_env_list_file(
    output_path: Optional[Path] = None,
    search_paths: Optional[Iterable[Path]] = None,
    include_system: bool = True,
) -> Path:
    """Create python-env-list.txt with discovered environments and return its path."""
    lister = PythonEnvLister(search_paths=search_paths, include_system=include_system)
    target_path = Path(output_path) if output_path is not None else Path("python-env-list.txt")
    lister.write_to_file(target_path)
    return target_path


if __name__ == "__main__":
    create_python_env_list_file()
