import socket
from datetime import datetime
from pathlib import Path
import shutil

from jinja2 import Environment, FileSystemLoader

from replibook.utils import detect_os


class PlaybookGenerator:
    def __init__(self, scan_results: dict, output_dir: str, export_compose: bool = False):
        self.scan_results = scan_results
        self.output_dir = Path(output_dir)
        self.export_compose = export_compose
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
        config = self.scan_results.get("config")
        deployments = self.scan_results.get("deployments", [])
        deployments = self._prepare_deployments(deployments)
        vault_vars = self._collect_vault_vars()

        template = self.env.get_template("site.yml.j2")
        playbook = template.render(
            hostname=hostname,
            timestamp=timestamp,
            host_os=host_os,
            use_become=(host_os == "linux"),
            apt_packages=[p for p in packages if p.manager == "apt"],
            brew_packages=[p for p in packages if p.manager == "homebrew"],
            cask_packages=[p for p in packages if p.manager == "homebrew_cask"],
            other_packages=[p for p in packages if p.manager not in {"apt", "homebrew", "homebrew_cask"}],
            systemd_services=[s for s in services if s.manager == "systemd"],
            systemd_user_services=[s for s in services if s.manager == "systemd_user"],
            brew_services=[s for s in services if s.manager == "homebrew"],
            launchd_services=[s for s in services if s.manager == "launchd"],
            containers=self.scan_results.get("docker", []),
            deployments=deployments,
            config=config,
        )

        playbook_file = self.output_dir / f"{hostname}_playbook.yml"
        playbook_file.write_text(playbook)

        inventory_file = self.output_dir / "inventory.ini"
        inventory_file.write_text(f"[replibook]\n{hostname} ansible_connection=local\n")

        if vault_vars:
            vault_file = self.output_dir / "vault_vars.example.yml"
            lines = ["---"] + [f"{k}: {v}" for k, v in sorted(vault_vars.items())]
            vault_file.write_text("\n".join(lines) + "\n")

        return str(playbook_file), str(inventory_file)

    def _collect_vault_vars(self) -> dict[str, str]:
        vars_out: dict[str, str] = {}
        for container in self.scan_results.get("docker", []):
            for key, value in getattr(container, "vault_vars", {}).items():
                vars_out[key] = value
        return vars_out

    def _prepare_deployments(self, deployments: list) -> list[dict]:
        if not self.export_compose:
            return [
                {
                    "name": d.name,
                    "directory": d.directory,
                    "project_src": d.directory,
                }
                for d in deployments
            ]

        base = self.output_dir / "compose_exports"
        base.mkdir(parents=True, exist_ok=True)
        prepared = []
        for index, dep in enumerate(deployments, start=1):
            target = base / f"{index:03d}_{self._slug(dep.name)}"
            target.mkdir(parents=True, exist_ok=True)
            copied = False

            compose_file = Path(getattr(dep, "compose_file", "") or "")
            if compose_file.is_file():
                shutil.copy2(compose_file, target / compose_file.name)
                copied = True
            for env_path in getattr(dep, "env_files", []) or []:
                src = Path(env_path)
                if src.is_file():
                    shutil.copy2(src, target / src.name)
                    copied = True

            prepared.append(
                {
                    "name": dep.name,
                    "directory": dep.directory,
                    "project_src": str(target if copied else dep.directory),
                }
            )
        return prepared

    @staticmethod
    def _slug(value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() else "_" for ch in value).strip("_").lower()
        return cleaned or "compose_project"
