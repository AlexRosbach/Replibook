import os
from pathlib import Path

import yaml
from replibook.scanner.base import BaseScanner
from replibook.models.scan_result import ComposeDeployment
from replibook.utils import detect_os

_LINUX_ROOTS = ["/opt", "/srv", "/home", "/root", "/docker", "/var/lib"]
_MACOS_ROOTS = ["/Users", "/opt", "/usr/local"]
_COMPOSE_NAMES = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
_SKIP_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__",
    ".cache", "target", "build", "dist", ".tox", ".pytest_cache",
    ".mypy_cache", "Library", ".Trash",
}


class DeploymentScanner(BaseScanner):
    def scan(self) -> list[ComposeDeployment]:
        roots = _MACOS_ROOTS if detect_os() == "macos" else _LINUX_ROOTS
        found_dirs: set[str] = set()
        deployments = []

        for root in roots:
            if not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
                for filename in filenames:
                    if filename in _COMPOSE_NAMES and dirpath not in found_dirs:
                        found_dirs.add(dirpath)
                        compose_path = os.path.join(dirpath, filename)
                        deployments.append(ComposeDeployment(
                            directory=dirpath,
                            name=os.path.basename(dirpath),
                            compose_file=compose_path,
                            env_files=self._find_env_files(compose_path),
                        ))

        return sorted(deployments, key=lambda d: d.directory)

    def _find_env_files(self, compose_file: str) -> list[str]:
        compose_path = Path(compose_file)
        env_files = []
        default_env = compose_path.parent / ".env"
        if default_env.is_file():
            env_files.append(str(default_env))

        try:
            content = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return sorted(set(env_files))

        services = content.get("services", {}) if isinstance(content, dict) else {}
        for svc in services.values():
            if not isinstance(svc, dict):
                continue
            env_file = svc.get("env_file")
            if not env_file:
                continue
            entries = env_file if isinstance(env_file, list) else [env_file]
            for entry in entries:
                file_path = compose_path.parent / str(entry)
                if file_path.is_file():
                    env_files.append(str(file_path))

        return sorted(set(env_files))
