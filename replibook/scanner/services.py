from replibook.scanner.base import BaseScanner
from replibook.models.scan_result import ServiceInfo
from replibook.utils import detect_os, has_command

_LINUX_SKIP_PREFIXES = (
    "systemd-", "dbus", "getty", "user@", "session-",
    "init.scope", "-.mount", "-.slice",
)


class ServiceScanner(BaseScanner):
    def __init__(self, include_user_services: bool = False, include_launchd: bool = False):
        self.include_user_services = include_user_services
        self.include_launchd = include_launchd

    def scan(self) -> list[ServiceInfo]:
        os_name = detect_os()
        if os_name == "macos":
            return self._scan_macos()
        return self._scan_linux()

    # ── Linux (systemd) ───────────────────────────────────────────────────

    def _scan_linux(self) -> list[ServiceInfo]:
        if not has_command("systemctl"):
            return []

        enabled = self._systemctl_set(["--state=enabled"], "list-unit-files")
        active = self._systemctl_set(["--state=active"], "list-units")
        user_enabled = set()
        user_active = set()
        if self.include_user_services:
            user_enabled = self._systemctl_set(["--user", "--state=enabled"], "list-unit-files")
            user_active = self._systemctl_set(["--user", "--state=active"], "list-units")

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
        for name in sorted(user_enabled | user_active):
            if any(name.startswith(p) for p in _LINUX_SKIP_PREFIXES):
                continue
            services.append(ServiceInfo(
                name=name,
                enabled=name in user_enabled,
                state="started" if name in user_active else "stopped",
                manager="systemd_user",
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
        services = []
        if has_command("brew"):
            output = self._run(["brew", "services", "list"])

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

        if self.include_launchd and has_command("launchctl"):
            output = self._run(["launchctl", "list"])
            for line in output.splitlines()[1:]:
                parts = line.split()
                if len(parts) < 3:
                    continue
                label = parts[-1].strip()
                if label.startswith("com.apple."):
                    continue
                services.append(ServiceInfo(
                    name=label,
                    enabled=True,
                    state="started",
                    manager="launchd",
                ))
        return sorted(services, key=lambda s: s.name)
