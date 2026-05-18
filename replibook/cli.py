import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel

from replibook.scanner import (
    PackageScanner,
    ServiceScanner,
    DockerScanner,
    DeploymentScanner,
    ConfigStateScanner,
)
from replibook.generator.playbook import PlaybookGenerator
from replibook.utils import detect_os
from replibook.version import __version__

console = Console()


def _module_labels(host_os: str) -> dict:
    if host_os == "macos":
        return {
            "packages": ("Installed Packages (Homebrew)", PackageScanner),
            "services": ("Homebrew Services", ServiceScanner),
            "docker": ("Docker Containers & Images", DockerScanner),
            "deployments": ("Docker Compose Deployments", DeploymentScanner),
            "config": ("Host Configuration & State", ConfigStateScanner),
        }
    return {
        "packages": ("Installed Packages (apt/dpkg)", PackageScanner),
        "services": ("Systemd Services", ServiceScanner),
        "docker": ("Docker Containers & Images", DockerScanner),
        "deployments": ("Docker Compose Deployments", DeploymentScanner),
        "config": ("Host Configuration & State", ConfigStateScanner),
    }


def run(
    output: str,
    run_all: bool = False,
    include_packages: bool | None = None,
    include_services: bool | None = None,
    include_docker: bool | None = None,
    include_deployments: bool | None = None,
    include_config: bool | None = None,
    redact_secrets: bool = True,
    vault_env_prefix: str | None = None,
    export_compose: bool = False,
    include_user_services: bool = False,
    include_launchd: bool = False,
    snapshot_path: str | None = None,
) -> None:
    host_os = detect_os()
    MODULES = _module_labels(host_os)

    console.print(Panel(
        f"[bold cyan]Replibook v{__version__}[/bold cyan]\n"
        f"Ansible Playbook Generator [dim]· detected: {host_os}[/dim]",
        expand=False,
    ))

    explicit_module_flags = {
        "packages": include_packages,
        "services": include_services,
        "docker": include_docker,
        "deployments": include_deployments,
        "config": include_config,
    }
    has_explicit_selection = any(v is not None for v in explicit_module_flags.values())

    if run_all:
        selected_keys = list(MODULES.keys())
    elif has_explicit_selection:
        selected_keys = [k for k, v in explicit_module_flags.items() if v is True]
        if not selected_keys:
            console.print("[yellow]No modules selected. Exiting.[/yellow]")
            raise SystemExit(0)
    else:
        choices = [
            questionary.Choice(title=label, value=key, checked=True)
            for key, (label, _) in MODULES.items()
        ]
        selected_keys = questionary.checkbox(
            "Select scanner modules to run:",
            choices=choices,
        ).ask()

        if not selected_keys:
            console.print("[yellow]No modules selected. Exiting.[/yellow]")
            raise SystemExit(0)

        output = questionary.text(
            "Output directory for playbooks:",
            default=output,
        ).ask()

        if output is None:
            raise SystemExit(0)

    console.print("\n[bold]Scanning...[/bold]")

    scan_results: dict = {}
    for key in selected_keys:
        label, ScannerClass = MODULES[key]
        console.print(f"  [cyan]→[/cyan] {label}")
        if key == "services":
            scan_results[key] = ScannerClass(
                include_user_services=include_user_services,
                include_launchd=include_launchd,
            ).scan()
        elif key == "docker":
            scan_results[key] = ScannerClass(
                redact_secrets=redact_secrets,
                vault_env_prefix=vault_env_prefix,
            ).scan()
        else:
            scan_results[key] = ScannerClass().scan()

    counts = {
        "packages": len(scan_results.get("packages", [])),
        "services": len(scan_results.get("services", [])),
        "docker": len(scan_results.get("docker", [])),
        "deployments": len(scan_results.get("deployments", [])),
        "config": _config_count(scan_results.get("config")),
    }

    console.print()
    for key, count in counts.items():
        if key in scan_results:
            label = MODULES[key][0]
            console.print(f"  [dim]{label}:[/dim] [white]{count}[/white] found")

    console.print("\n[bold]Generating playbook...[/bold]")
    generator = PlaybookGenerator(scan_results, output, export_compose=export_compose)
    playbook_path, inventory_path = generator.generate()

    console.print()
    console.print(f"[green]✓[/green] Playbook written to: [bold]{playbook_path}[/bold]")
    console.print(f"[green]✓[/green] Inventory written to: [bold]{inventory_path}[/bold]")

    if snapshot_path:
        snapshot_file = Path(snapshot_path)
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "host_os": host_os,
            "scan_results": _serialize(scan_results),
        }
        snapshot_file.write_text(json.dumps(payload, indent=2) + "\n")
        console.print(f"[green]✓[/green] Snapshot written to: [bold]{snapshot_file}[/bold]")


def diff_snapshots(old_snapshot: str, new_snapshot: str) -> None:
    old = json.loads(Path(old_snapshot).read_text(encoding="utf-8"))
    new = json.loads(Path(new_snapshot).read_text(encoding="utf-8"))
    old_results = old.get("scan_results", {})
    new_results = new.get("scan_results", {})

    console.print(Panel("[bold cyan]Replibook Snapshot Diff[/bold cyan]", expand=False))

    keys = sorted(set(old_results.keys()) | set(new_results.keys()))
    for key in keys:
        old_items = _canonicalize(old_results.get(key))
        new_items = _canonicalize(new_results.get(key))
        added = sorted(new_items - old_items)
        removed = sorted(old_items - new_items)
        console.print(f"\n[bold]{key}[/bold]: +{len(added)} / -{len(removed)}")
        for line in added[:20]:
            console.print(f"  [green]+ {line}[/green]")
        for line in removed[:20]:
            console.print(f"  [red]- {line}[/red]")


def _canonicalize(value) -> set[str]:
    if isinstance(value, list):
        return {json.dumps(item, sort_keys=True) for item in value}
    if isinstance(value, dict):
        if all(v is None or isinstance(v, (str, int, float, bool)) for v in value.values()):
            return {f"{k}={value[k]}" for k in sorted(value.keys())}
        result = set()
        for k, v in value.items():
            result |= {f"{k}:{item}" for item in _canonicalize(v)}
        return result
    if value is None:
        return set()
    return {str(value)}


def _serialize(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    return value


def _config_count(config) -> int:
    if not config:
        return 0
    return (
        len(getattr(config, "users", []))
        + len(getattr(config, "groups", []))
        + len(getattr(config, "cron_jobs", []))
        + len(getattr(config, "ssh_settings", []))
        + len(getattr(config, "firewall_rules", []))
        + len(getattr(config, "mounts", []))
        + len(getattr(config, "sysctl", {}))
    )
