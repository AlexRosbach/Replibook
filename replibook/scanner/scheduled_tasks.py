from pathlib import Path

from replibook.models.scan_result import ScheduledTaskInfo
from replibook.scanner.base import BaseScanner
from replibook.utils import detect_os, has_command


CRON_PARTS = {"@reboot", "@hourly", "@daily", "@weekly", "@monthly", "@yearly", "@annually"}


class ScheduledTaskScanner(BaseScanner):
    def scan(self) -> list[ScheduledTaskInfo]:
        if detect_os() == "macos":
            return self._scan_macos()
        return self._scan_linux()

    def _scan_linux(self) -> list[ScheduledTaskInfo]:
        tasks = []
        tasks.extend(self._scan_user_crontab())
        tasks.extend(self._scan_cron_file(Path("/etc/crontab"), system_crontab=True))
        for directory in ("/etc/cron.d", "/etc/cron.hourly", "/etc/cron.daily", "/etc/cron.weekly", "/etc/cron.monthly"):
            tasks.extend(self._scan_cron_directory(Path(directory)))
        return sorted(tasks, key=lambda item: (item.source, item.name, item.command))

    def _scan_macos(self) -> list[ScheduledTaskInfo]:
        tasks = []
        tasks.extend(self._scan_user_crontab())
        for directory in (
            Path.home() / "Library" / "LaunchAgents",
            Path("/Library/LaunchAgents"),
            Path("/Library/LaunchDaemons"),
        ):
            if not directory.is_dir():
                continue
            for item in sorted(directory.glob("*.plist")):
                tasks.append(ScheduledTaskInfo(
                    name=item.stem,
                    source=str(item),
                    manager="launchd",
                    command=f"Review launchd plist: {item}",
                ))
        return tasks

    def _scan_user_crontab(self) -> list[ScheduledTaskInfo]:
        if not has_command("crontab"):
            return []
        output = self._run(["crontab", "-l"])
        return self._parse_crontab(output, source="user crontab", system_crontab=False)

    def _scan_cron_directory(self, directory: Path) -> list[ScheduledTaskInfo]:
        if not directory.is_dir():
            return []

        tasks = []
        for item in sorted(directory.iterdir()):
            if not item.is_file():
                continue
            if directory.name.startswith("cron.") and directory.name != "cron.d":
                tasks.append(ScheduledTaskInfo(
                    name=item.name,
                    source=str(item),
                    schedule=directory.name.replace("cron.", "@"),
                    command=str(item),
                    manager="cron-file",
                ))
            else:
                tasks.extend(self._scan_cron_file(item, system_crontab=True))
        return tasks

    def _scan_cron_file(self, path: Path, system_crontab: bool) -> list[ScheduledTaskInfo]:
        if not path.is_file():
            return []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []
        return self._parse_crontab(content, source=str(path), system_crontab=system_crontab)

    def _parse_crontab(self, content: str, source: str, system_crontab: bool) -> list[ScheduledTaskInfo]:
        tasks = []
        for index, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" in stripped.split(maxsplit=1)[0]:
                continue
            parsed = self._parse_cron_line(stripped, system_crontab=system_crontab)
            if not parsed:
                continue
            schedule, user, command = parsed
            tasks.append(ScheduledTaskInfo(
                name=f"{Path(source).name}:{index}",
                source=source,
                schedule=schedule,
                command=command,
                user=user,
                manager="cron",
            ))
        return tasks

    def _parse_cron_line(self, line: str, system_crontab: bool) -> tuple[str, str, str] | None:
        parts = line.split()
        if not parts:
            return None

        if parts[0] in CRON_PARTS:
            min_len = 3 if system_crontab else 2
            if len(parts) < min_len:
                return None
            if system_crontab:
                return parts[0], parts[1], " ".join(parts[2:])
            return parts[0], "", " ".join(parts[1:])

        min_len = 7 if system_crontab else 6
        if len(parts) < min_len:
            return None

        schedule = " ".join(parts[:5])
        if system_crontab:
            return schedule, parts[5], " ".join(parts[6:])
        return schedule, "", " ".join(parts[5:])
