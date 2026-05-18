from replibook.scanner.base import BaseScanner
from replibook.models.scan_result import PackageInfo
from replibook.utils import detect_os, has_command


class PackageScanner(BaseScanner):
    def scan(self) -> list[PackageInfo]:
        os_name = detect_os()
        if os_name == "macos":
            return self._scan_macos()
        return self._scan_linux()

    # ── Linux (apt / dpkg) ────────────────────────────────────────────────

    def _scan_linux(self) -> list[PackageInfo]:
        if has_command("pacman"):
            return self._scan_pacman()
        if has_command("dnf"):
            return self._scan_rpm_like("dnf")
        if has_command("yum"):
            return self._scan_rpm_like("yum")
        if has_command("zypper"):
            return self._scan_rpm_like("zypper")
        if has_command("rpm"):
            return self._scan_rpm_like("rpm")

        packages = []

        if has_command("apt-mark"):
            manual = self._run(["apt-mark", "showmanual"])
            if manual:
                names = [line.strip() for line in manual.splitlines() if line.strip()]
                versions = self._dpkg_versions(names)
                for name in names:
                    packages.append(PackageInfo(
                        name=name,
                        version=versions.get(name, ""),
                        manager="apt",
                    ))
                return sorted(packages, key=lambda p: p.name)

        if has_command("dpkg-query"):
            output = self._run(["dpkg-query", "-W", "-f=${Package}\t${Version}\n"])
            for line in output.splitlines():
                parts = line.split("\t", 1)
                if len(parts) == 2 and parts[0].strip():
                    packages.append(PackageInfo(
                        name=parts[0].strip(),
                        version=parts[1].strip(),
                        manager="apt",
                    ))

        return sorted(packages, key=lambda p: p.name)

    def _scan_rpm_like(self, manager: str) -> list[PackageInfo]:
        if not has_command("rpm"):
            return []
        packages = []
        output = self._run(["rpm", "-qa", "--qf", "%{NAME}\t%{VERSION}-%{RELEASE}\n"])
        for line in output.splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2 and parts[0].strip():
                packages.append(PackageInfo(
                    name=parts[0].strip(),
                    version=parts[1].strip(),
                    manager=manager,
                ))
        return sorted(packages, key=lambda p: p.name)

    def _scan_pacman(self) -> list[PackageInfo]:
        output = self._run(["pacman", "-Qe"])
        packages = []
        for line in output.splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2:
                packages.append(PackageInfo(name=parts[0].strip(), version=parts[1].strip(), manager="pacman"))
        return sorted(packages, key=lambda p: p.name)

    def _dpkg_versions(self, names: list[str]) -> dict[str, str]:
        if not names or not has_command("dpkg-query"):
            return {}
        output = self._run(["dpkg-query", "-W", "-f=${Package}\t${Version}\n"] + names)
        versions = {}
        for line in output.splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                versions[parts[0].strip()] = parts[1].strip()
        return versions

    # ── macOS (Homebrew) ──────────────────────────────────────────────────

    def _scan_macos(self) -> list[PackageInfo]:
        if not has_command("brew"):
            return []

        packages = []

        formulas = self._run(["brew", "list", "--installed-on-request", "--formula"])
        for name in formulas.splitlines():
            name = name.strip()
            if name:
                packages.append(PackageInfo(name=name, version="", manager="homebrew"))

        casks = self._run(["brew", "list", "--cask"])
        for name in casks.splitlines():
            name = name.strip()
            if name:
                packages.append(PackageInfo(name=name, version="", manager="homebrew_cask"))

        return sorted(packages, key=lambda p: (p.manager, p.name))
