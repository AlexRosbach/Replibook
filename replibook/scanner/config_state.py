import glob
import grp
import os
import pwd

from replibook.models.scan_result import CronJobInfo, HostConfigState, SSHSettingInfo
from replibook.scanner.base import BaseScanner
from replibook.utils import detect_os, has_command

_SYSCTL_PREFIXES = ("net.", "vm.", "fs.", "kernel.")


class ConfigStateScanner(BaseScanner):
    def scan(self) -> HostConfigState:
        return HostConfigState(
            users=self._scan_users(),
            groups=self._scan_groups(),
            cron_jobs=self._scan_cron(),
            ssh_settings=self._scan_ssh_settings(),
            firewall_rules=self._scan_firewall(),
            mounts=self._scan_mounts(),
            sysctl=self._scan_sysctl(),
        )

    def _scan_users(self) -> list[str]:
        users = []
        for user in pwd.getpwall():
            if user.pw_uid >= 1000 or user.pw_uid in (0,):
                users.append(user.pw_name)
        return sorted(set(users))

    def _scan_groups(self) -> list[str]:
        groups = []
        for group in grp.getgrall():
            if group.gr_gid >= 1000 or group.gr_gid in (0,):
                groups.append(group.gr_name)
        return sorted(set(groups))

    def _scan_cron(self) -> list[CronJobInfo]:
        sources = ["/etc/crontab"] + sorted(glob.glob("/etc/cron.d/*"))
        jobs: list[CronJobInfo] = []
        for source in sources:
            if not os.path.isfile(source):
                continue
            try:
                with open(source, "r", encoding="utf-8", errors="ignore") as f:
                    for raw in f:
                        line = raw.strip()
                        if not line or line.startswith("#"):
                            continue
                        jobs.append(CronJobInfo(source=source, line=line))
            except OSError:
                continue
        return jobs

    def _scan_ssh_settings(self) -> list[SSHSettingInfo]:
        path = "/etc/ssh/sshd_config"
        settings = []
        if not os.path.isfile(path):
            return settings
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        settings.append(SSHSettingInfo(key=parts[0], value=parts[1]))
        except OSError:
            return []
        return settings

    def _scan_firewall(self) -> list[str]:
        os_name = detect_os()
        if os_name == "linux":
            if has_command("ufw"):
                return [line for line in self._run(["ufw", "status"]).splitlines() if line.strip()]
            if has_command("firewall-cmd"):
                return [line for line in self._run(["firewall-cmd", "--list-all"]).splitlines() if line.strip()]
            if has_command("iptables"):
                return [line for line in self._run(["iptables", "-S"]).splitlines() if line.strip()]
            return []
        if has_command("pfctl"):
            return [line for line in self._run(["pfctl", "-sr"]).splitlines() if line.strip()]
        return []

    def _scan_mounts(self) -> list[str]:
        os_name = detect_os()
        if os_name == "linux" and os.path.isfile("/proc/mounts"):
            mounts = []
            try:
                with open("/proc/mounts", "r", encoding="utf-8", errors="ignore") as f:
                    for raw in f:
                        parts = raw.split()
                        if len(parts) >= 4:
                            mounts.append(f"{parts[0]} {parts[1]} {parts[2]} {parts[3]}")
            except OSError:
                return []
            return mounts
        return [line for line in self._run(["mount"]).splitlines() if line.strip()]

    def _scan_sysctl(self) -> dict[str, str]:
        if not has_command("sysctl"):
            return {}
        output = self._run(["sysctl", "-a"])
        result: dict[str, str] = {}
        for line in output.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
            elif ":" in line:
                key, value = line.split(":", 1)
            else:
                continue
            key = key.strip()
            value = value.strip()
            if key.startswith(_SYSCTL_PREFIXES):
                result[key] = value
        return result
