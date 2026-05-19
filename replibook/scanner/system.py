import locale
import socket

from replibook.models.scan_result import SystemConfigInfo
from replibook.scanner.base import BaseScanner
from replibook.utils import detect_os, has_command


class SystemScanner(BaseScanner):
    def scan(self) -> list[SystemConfigInfo]:
        info = SystemConfigInfo(
            hostname=socket.gethostname(),
            timezone=self._timezone(),
            locale=self._locale(),
        )
        return [info]

    def _timezone(self) -> str:
        if detect_os() == "macos" and has_command("systemsetup"):
            output = self._run(["systemsetup", "-gettimezone"])
            if ":" in output:
                return output.split(":", 1)[1].strip()

        if detect_os() == "windows" and has_command("tzutil"):
            return self._run(["tzutil", "/g"]).strip()

        if has_command("timedatectl"):
            output = self._run(["timedatectl", "show", "-p", "Timezone", "--value"])
            if output:
                return output.strip()
        return ""

    def _locale(self) -> str:
        current = locale.getlocale()[0]
        if current:
            return current

        output = self._run(["locale"])
        for line in output.splitlines():
            if line.startswith("LANG="):
                return line.split("=", 1)[1].strip().strip('"')

        if detect_os() == "windows" and has_command("powershell"):
            output = self._run([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-Command", "(Get-Culture).Name",
            ])
            if output:
                return output.strip()
        return ""
