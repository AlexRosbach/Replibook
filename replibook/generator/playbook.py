import socket
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from replibook.review import build_review_report
from replibook.utils import detect_os


@dataclass
class TargetConfig:
    name: str
    connection: str = "local"
    host: str | None = None
    user: str | None = None
    port: int | None = None
    identity_file: str | None = None

    def inventory_line(self) -> str:
        if self.connection == "local":
            return f"{self.name} ansible_connection=local"

        parts = [self.name]
        if self.host:
            parts.append(f"ansible_host={self.host}")
        if self.user:
            parts.append(f"ansible_user={self.user}")
        if self.port:
            parts.append(f"ansible_port={self.port}")
        if self.identity_file:
            parts.append(f"ansible_ssh_private_key_file={self.identity_file}")
        return " ".join(parts)


class PlaybookGenerator:
    def __init__(
        self,
        scan_results: dict,
        output_dir: str,
        target: TargetConfig | None = None,
        use_become: bool | None = None,
    ):
        self.scan_results = scan_results
        self.output_dir = Path(output_dir)
        self.target = target
        self.use_become = use_become
        self.review_report_path: str | None = None
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def generate(self) -> tuple[str, str]:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        hostname = socket.gethostname()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        host_os = detect_os()
        target = self.target or TargetConfig(name=hostname)
        use_become = self.use_become if self.use_become is not None else (host_os == "linux")

        packages = self.scan_results.get("packages", [])
        services = self.scan_results.get("services", [])

        template = self.env.get_template("site.yml.j2")
        playbook = template.render(
            hostname=hostname,
            timestamp=timestamp,
            host_os=host_os,
            use_become=use_become,
            review_report=build_review_report(self.scan_results),
            review_report_path=self.review_report_path,
            system_configs=self.scan_results.get("system", []),
            scheduled_tasks=self.scan_results.get("scheduled_tasks", []),
            apt_packages=[p for p in packages if p.manager == "apt"],
            brew_packages=[p for p in packages if p.manager == "homebrew"],
            cask_packages=[p for p in packages if p.manager == "homebrew_cask"],
            windows_packages=[p for p in packages if p.manager.startswith("windows")],
            systemd_services=[s for s in services if s.manager == "systemd"],
            brew_services=[s for s in services if s.manager == "homebrew"],
            windows_services=[s for s in services if s.manager == "windows"],
            containers=self.scan_results.get("docker", []),
            deployments=self.scan_results.get("deployments", []),
            network_interfaces=self.scan_results.get("network", []),
        )

        playbook_file = self.output_dir / f"{hostname}_playbook.yml"
        playbook_file.write_text(playbook)

        inventory_file = self.output_dir / "inventory.ini"
        inventory_file.write_text(f"[replibook]\n{target.inventory_line()}\n")

        return str(playbook_file), str(inventory_file)
