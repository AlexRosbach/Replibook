import json

from replibook.scanner.base import BaseScanner
from replibook.models.scan_result import ServiceInfo
from replibook.utils import detect_os, has_command

_LINUX_SKIP_PREFIXES = (
    "systemd-", "dbus", "getty", "user@", "session-",
    "init.scope", "-.mount", "-.slice",
)


class ServiceScanner(BaseScanner):
    def scan(self) -> list[ServiceInfo]:
        os_name = detect_os()
        if os_name == "macos":
            return self._scan_macos()
        if os_name == "windows":
            return self._scan_windows()
        return self._scan_linux()

    # ── Linux (systemd) ───────────────────────────────────────────────────

    def _scan_linux(self) -> list[ServiceInfo]:
        if not has_command("systemctl"):
            return []

        enabled = self._systemctl_set(["--state=enabled"], "list-unit-files")
        active = self._systemctl_set(["--state=active"], "list-units")

        services = []
        for name in sorted(enabled | active):
            if any(name.startswith(p) for p in _LINUX_SKIP_PREFIXES):
                continue
            services.append(ServiceInfo(
                name=name,
                enabled=name in enabled,
                state="started" if name in active else "stopped",
                manager="systemd",
            ))
        return services

    def _systemctl_set(self, extra_args: list[str], subcommand: str) -> set[str]:
        output = self._run([
            "systemctl", subcommand, "--type=service",
            "--no-pager", "--no-legend", "--plain", *extra_args,
        ])
        names = set()
        for line in output.splitlines():
            parts = line.split()
            if parts:
                names.add(parts[0].removesuffix(".service"))
        return names

    # ── macOS (Homebrew services) ─────────────────────────────────────────

    def _scan_macos(self) -> list[ServiceInfo]:
        if not has_command("brew"):
            return []

        output = self._run(["brew", "services", "list"])
        services = []

        for line in output.splitlines()[1:]:  # skip header
            parts = line.split()
            if len(parts) < 2:
                continue
            name = parts[0]
            status = parts[1].lower()
            if status == "none":
                continue
            services.append(ServiceInfo(
                name=name,
                enabled=status == "started",
                state="started" if status == "started" else "stopped",
                manager="homebrew",
            ))
        return sorted(services, key=lambda s: s.name)

    # ── Windows services ──────────────────────────────────────────────────

    def _scan_windows(self) -> list[ServiceInfo]:
        if not has_command("powershell"):
            return []

        script = r"""
Get-CimInstance Win32_Service |
  Where-Object { $_.State -eq 'Running' -or $_.StartMode -in @('Auto', 'Automatic') } |
  Select-Object Name, State, StartMode |
  Sort-Object Name |
  ConvertTo-Json -Depth 3
"""
        output = self._run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])
        services = []
        for item in self._json_list(output):
            name = str(item.get("Name", "")).strip()
            if not name:
                continue
            state = str(item.get("State", "")).lower()
            start_mode = str(item.get("StartMode", "")).lower()
            services.append(ServiceInfo(
                name=name,
                enabled=start_mode in {"auto", "automatic"},
                state="started" if state == "running" else "stopped",
                manager="windows",
            ))
        return services

    def _json_list(self, output: str) -> list[dict]:
        if not output:
            return []
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return []
        if isinstance(data, dict):
            return [data]
        return data if isinstance(data, list) else []
