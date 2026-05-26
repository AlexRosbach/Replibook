import os
from replibook.scanner.base import BaseScanner
from replibook.models.scan_result import ComposeDeployment
from replibook.utils import detect_os

_LINUX_ROOTS = ["/opt", "/srv", "/home", "/root", "/docker", "/var/lib"]
_MACOS_ROOTS = ["/Users", "/opt", "/usr/local"]
_WINDOWS_ROOTS = ["C:\\Docker", "C:\\Projects", os.path.expanduser("~")]
_COMPOSE_NAMES = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
_SKIP_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__",
    ".cache", "target", "build", "dist", ".tox", ".pytest_cache",
    ".mypy_cache", "Library", ".Trash",
}


class DeploymentScanner(BaseScanner):
    def scan(self) -> list[ComposeDeployment]:
        os_name = detect_os()
        if os_name == "macos":
            roots = _MACOS_ROOTS
        elif os_name == "windows":
            roots = _WINDOWS_ROOTS
        else:
            roots = _LINUX_ROOTS
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
                        deployments.append(ComposeDeployment(
                            directory=dirpath,
                            name=os.path.basename(dirpath),
                        ))

        return sorted(deployments, key=lambda d: d.directory)
