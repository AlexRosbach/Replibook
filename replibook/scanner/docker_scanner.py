from replibook.scanner.base import BaseScanner
from replibook.models.scan_result import ContainerInfo


class DockerScanner(BaseScanner):
    def __init__(self, redact_secrets: bool = True, vault_env_prefix: str | None = None):
        self.redact_secrets = redact_secrets
        self.vault_env_prefix = vault_env_prefix

    def scan(self) -> list[ContainerInfo]:
        try:
            import docker
            client = docker.from_env()
        except Exception:
            return []

        containers = []
        for c in client.containers.list(all=True):
            attrs = c.attrs
            containers.append(ContainerInfo(
                name=c.name,
                image=attrs.get("Config", {}).get("Image", ""),
                ports=self._parse_ports(attrs),
                volumes=self._parse_volumes(attrs),
                env_vars=self._parse_env(attrs, c.name),
                vault_vars=self._collect_vault_vars(attrs, c.name),
                restart_policy=attrs.get("HostConfig", {}).get("RestartPolicy", {}).get("Name", "unless-stopped"),
            ))

        return sorted(containers, key=lambda c: c.name)

    def _parse_ports(self, attrs: dict) -> list[str]:
        port_bindings = attrs.get("HostConfig", {}).get("PortBindings") or {}
        ports = []
        for container_port, bindings in port_bindings.items():
            if bindings:
                for binding in bindings:
                    host_port = binding.get("HostPort", "")
                    if host_port:
                        ports.append(f"{host_port}:{container_port.split('/')[0]}")
        return ports

    def _parse_volumes(self, attrs: dict) -> list[str]:
        mounts = attrs.get("Mounts") or []
        volumes = []
        for m in mounts:
            source = m.get("Source", "")
            destination = m.get("Destination", "")
            mode = m.get("Mode", "rw")
            if source and destination:
                volumes.append(f"{source}:{destination}:{mode}" if mode != "rw" else f"{source}:{destination}")
        return volumes

    def _parse_env(self, attrs: dict, container_name: str) -> dict[str, str]:
        raw = attrs.get("Config", {}).get("Env") or []
        env = {}
        for entry in raw:
            if "=" in entry:
                key, value = entry.split("=", 1)
                if self.vault_env_prefix and self._looks_secret(key):
                    env[key] = "{{ " + self._vault_var_name(container_name, key) + " }}"
                    continue
                if self.redact_secrets and self._looks_secret(key):
                    env[key] = "__REDACTED__"
                    continue
                env[key] = value
        return env

    def _collect_vault_vars(self, attrs: dict, container_name: str) -> dict[str, str]:
        if not self.vault_env_prefix:
            return {}
        vars_out = {}
        raw = attrs.get("Config", {}).get("Env") or []
        for entry in raw:
            if "=" not in entry:
                continue
            key, _ = entry.split("=", 1)
            if self._looks_secret(key):
                vars_out[self._vault_var_name(container_name, key)] = "__SET_ME__"
        return vars_out

    def _vault_var_name(self, container_name: str, env_key: str) -> str:
        cname = "".join(ch if ch.isalnum() else "_" for ch in container_name).strip("_").lower()
        ekey = "".join(ch if ch.isalnum() else "_" for ch in env_key).strip("_").lower()
        return f"{self.vault_env_prefix}_{cname}_{ekey}"

    @staticmethod
    def _looks_secret(key: str) -> bool:
        upper = key.upper()
        markers = ("SECRET", "TOKEN", "PASSWORD", "PASS", "API_KEY", "PRIVATE_KEY", "ACCESS_KEY")
        return any(m in upper for m in markers)
