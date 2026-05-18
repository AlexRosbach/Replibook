import questionary
from rich.console import Console
from rich.panel import Panel

from replibook.scanner import (
    PackageScanner,
    ServiceScanner,
    DockerScanner,
    DeploymentScanner,
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
        }
    return {
        "packages": ("Installed Packages (apt/dpkg)", PackageScanner),
        "services": ("Systemd Services", ServiceScanner),
        "docker": ("Docker Containers & Images", DockerScanner),
        "deployments": ("Docker Compose Deployments", DeploymentScanner),
    }


def run(output: str, run_all: bool = False) -> None:
    host_os = detect_os()
    MODULES = _module_labels(host_os)

    console.print(Panel(
        f"[bold cyan]Replibook v{__version__}[/bold cyan]\n"
        f"Ansible Playbook Generator [dim]· detected: {host_os}[/dim]",
        expand=False,
    ))

    if run_all:
        selected_keys = list(MODULES.keys())
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
        scan_results[key] = ScannerClass().scan()

    counts = {
        "packages": len(scan_results.get("packages", [])),
        "services": len(scan_results.get("services", [])),
        "docker": len(scan_results.get("docker", [])),
        "deployments": len(scan_results.get("deployments", [])),
    }

    console.print()
    for key, count in counts.items():
        if key in scan_results:
            label = MODULES[key][0]
            console.print(f"  [dim]{label}:[/dim] [white]{count}[/white] found")

    console.print("\n[bold]Generating playbook...[/bold]")
    generator = PlaybookGenerator(scan_results, output)
    playbook_path, inventory_path = generator.generate()

    console.print()
    console.print(f"[green]✓[/green] Playbook written to: [bold]{playbook_path}[/bold]")
    console.print(f"[green]✓[/green] Inventory written to: [bold]{inventory_path}[/bold]")
