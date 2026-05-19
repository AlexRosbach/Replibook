import json

from replibook.models.scan_result import NetworkInterfaceInfo
from replibook.scanner.base import BaseScanner
from replibook.utils import detect_os, has_command


class NetworkScanner(BaseScanner):
    def scan(self) -> list[NetworkInterfaceInfo]:
        if detect_os() == "macos":
            return self._scan_macos()
        return self._scan_linux()

    def _scan_linux(self) -> list[NetworkInterfaceInfo]:
        interfaces: dict[str, NetworkInterfaceInfo] = {}

        if has_command("ip"):
            for item in self._ip_addr_json():
                name = item.get("ifname", "")
                if not name or name == "lo":
                    continue
                addresses = [
                    f"{addr.get('local')}/{addr.get('prefixlen')}"
                    for addr in item.get("addr_info", [])
                    if addr.get("family") == "inet" and addr.get("local") and addr.get("prefixlen") is not None
                ]
                interfaces[name] = NetworkInterfaceInfo(
                    name=name,
                    manager="ip",
                    addresses=addresses,
                    method="manual" if addresses else "disabled",
                )

            gateway, default_interface = self._linux_default_route()
            if default_interface and default_interface in interfaces:
                interfaces[default_interface].gateway4 = gateway

        if has_command("nmcli"):
            for connection in self._nmcli_connections():
                device = connection.get("GENERAL.DEVICES") or connection.get("device") or ""
                if not device or device == "--":
                    continue
                info = interfaces.setdefault(
                    device,
                    NetworkInterfaceInfo(name=device, manager="networkmanager"),
                )
                info.manager = "networkmanager"
                info.connection_name = connection.get("connection.id", "")
                info.method = connection.get("ipv4.method", info.method or "manual")
                if connection.get("ipv4.addresses"):
                    info.addresses = self._split_nmcli_values(connection["ipv4.addresses"])
                if connection.get("ipv4.gateway"):
                    info.gateway4 = connection["ipv4.gateway"]
                if connection.get("ipv4.dns"):
                    info.nameservers = self._split_nmcli_values(connection["ipv4.dns"])

        nameservers = self._linux_nameservers()
        for info in interfaces.values():
            if not info.nameservers:
                info.nameservers = nameservers

        return sorted(interfaces.values(), key=lambda item: item.name)

    def _scan_macos(self) -> list[NetworkInterfaceInfo]:
        if not has_command("networksetup"):
            return []

        services = []
        output = self._run(["networksetup", "-listallnetworkservices"])
        for line in output.splitlines():
            name = line.strip().removeprefix("*")
            if not name or name.startswith("An asterisk"):
                continue

            info = NetworkInterfaceInfo(name=name, manager="networksetup")
            ip_output = self._run(["networksetup", "-getinfo", name])
            for item in ip_output.splitlines():
                if item.startswith("IP address:"):
                    address = item.split(":", 1)[1].strip()
                    if address:
                        info.addresses.append(address)
                elif item.startswith("Subnet mask:"):
                    mask = item.split(":", 1)[1].strip()
                    if mask and info.addresses and "/" not in info.addresses[-1]:
                        info.addresses[-1] = f"{info.addresses[-1]} ({mask})"
                elif item.startswith("Router:"):
                    info.gateway4 = item.split(":", 1)[1].strip()

            dns_output = self._run(["networksetup", "-getdnsservers", name])
            if "There aren't any DNS Servers" not in dns_output:
                info.nameservers = [line.strip() for line in dns_output.splitlines() if line.strip()]
            services.append(info)

        return sorted(services, key=lambda item: item.name)

    def _ip_addr_json(self) -> list[dict]:
        output = self._run(["ip", "-j", "addr", "show"])
        if not output:
            return []
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def _linux_default_route(self) -> tuple[str, str]:
        output = self._run(["ip", "route", "show", "default"])
        for line in output.splitlines():
            parts = line.split()
            if "via" in parts and "dev" in parts:
                return parts[parts.index("via") + 1], parts[parts.index("dev") + 1]
        return "", ""

    def _linux_nameservers(self) -> list[str]:
        resolvectl = self._run(["resolvectl", "dns"])
        nameservers = []
        for line in resolvectl.splitlines():
            if ":" in line:
                nameservers.extend(line.split(":", 1)[1].split())
        if nameservers:
            return sorted(set(nameservers))

        try:
            with open("/etc/resolv.conf", encoding="utf-8") as handle:
                return [
                    line.split()[1]
                    for line in handle
                    if line.startswith("nameserver ") and len(line.split()) >= 2
                ]
        except OSError:
            return []

    def _nmcli_connections(self) -> list[dict[str, str]]:
        active = self._run(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
        connections = []
        for line in active.splitlines():
            if ":" not in line:
                continue
            name, device = line.split(":", 1)
            details = self._nmcli_connection_details(name)
            details["device"] = device
            connections.append(details)
        return connections

    def _nmcli_connection_details(self, name: str) -> dict[str, str]:
        fields = "connection.id,GENERAL.DEVICES,ipv4.method,ipv4.addresses,ipv4.gateway,ipv4.dns"
        output = self._run(["nmcli", "-t", "-f", fields, "connection", "show", name])
        details = {}
        for line in output.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                details[key] = value
        return details

    def _split_nmcli_values(self, value: str) -> list[str]:
        return [item.strip() for item in value.replace(",", ";").split(";") if item.strip()]
