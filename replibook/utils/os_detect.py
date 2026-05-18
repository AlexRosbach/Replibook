import platform
import shutil


def detect_os() -> str:
    """Return 'linux', 'macos', or 'unknown'."""
    system = platform.system()
    if system == "Linux":
        return "linux"
    if system == "Darwin":
        return "macos"
    return "unknown"


def has_command(name: str) -> bool:
    return shutil.which(name) is not None
