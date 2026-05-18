import socket
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from replibook.utils import detect_os


class PlaybookGenerator:
    def __init__(self, scan_results: dict, output_dir: str):
        self.scan_results = scan_results
        self.output_dir = Path(output_dir)
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

        packages = self.scan_results.get("packages", [])
        services = self.scan_results.get("services", [])

        template = self.env.get_template("site.yml.j2")
        playbook = template.render(
            hostname=hostname,
            timestamp=timestamp,
            host_os=host_os,
            use_become=(host_os == "linux"),
            apt_packages=[p for p in packages if p.manager == "apt"],
            brew_packages=[p for p in packages if p.manager == "homebrew"],
            cask_packages=[p for p in packages if p.manager == "homebrew_cask"],
            systemd_services=[s for s in services if s.manager == "systemd"],
            brew_services=[s for s in services if s.manager == "homebrew"],
            containers=self.scan_results.get("docker", []),
            deployments=self.scan_results.get("deployments", []),
        )

        playbook_file = self.output_dir / f"{hostname}_playbook.yml"
        playbook_file.write_text(playbook)

        inventory_file = self.output_dir / "inventory.ini"
        inventory_file.write_text(f"[replibook]\n{hostname} ansible_connection=local\n")

        return str(playbook_file), str(inventory_file)
