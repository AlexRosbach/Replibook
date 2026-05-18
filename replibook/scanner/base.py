from abc import ABC, abstractmethod
import subprocess


class BaseScanner(ABC):
    @abstractmethod
    def scan(self) -> list:
        pass

    def _run(self, cmd: list[str]) -> str:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""
