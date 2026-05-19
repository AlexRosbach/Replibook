import getpass

import questionary
from rich.console import Console
from rich.panel import Panel

from replibook.scanner import (
    PackageScanner,
    ServiceScanner,
    DockerScanner,
    DeploymentScanner,
)
from replibook.generator.playbook import PlaybookGenerator, TargetConfig
from replibook.utils import detect_os
from replibook.version import __version__

console = Console()


def _module_labels(host_os: str) -> dict:
    if host_os == "macos":
        return {
            "packages": (
                "Installed Packages (Homebrew)",
                "Reads Homebrew formulas and casks installed on this Mac.",
                PackageScanner,
            ),
            "services": (
                "Homebrew Services",
                "Reads services managed through brew services.",
                ServiceScanner,
            ),
            "docker": (
                "Docker Containers & Images",
                "Reads local Docker containers, images, ports, volumes and environment values.",
                DockerScanner,
            ),
            "deployments": (
                "Docker Compose Deployments",
                "Searches common folders for Compose files and adds deployment tasks.",
                DeploymentScanner,
            ),
        }
    return {
        "packages": (
            "Installed Packages (apt/dpkg)",
            "Reads manually installed apt/dpkg packages and creates apt tasks.",
            PackageScanner,
        ),
        "services": (
            "Systemd Services",
            "Reads enabled and active systemd services and creates service tasks.",
            ServiceScanner,
        ),
        "docker": (
            "Docker Containers & Images",
            "Reads local Docker containers, images, ports, volumes and environment values.",
            DockerScanner,
        ),
        "deployments": (
            "Docker Compose Deployments",
            "Searches common folders for Compose files and adds deployment tasks.",
            DeploymentScanner,
        ),
    }


def _ask_bool(message: str, default: bool) -> bool:
    answer = questionary.confirm(message, default=default).ask()
    if answer is None:
        raise SystemExit(0)
    return answer


def _ask_text(message: str, default: str = "") -> str:
    answer = questionary.text(message, default=default).ask()
    if answer is None:
        raise SystemExit(0)
    return answer.strip()


def _select_modules(modules: dict) -> list[str]:
    console.print("\n[bold]Scan modules[/bold]")
    console.print("[dim]Each module is explained before you decide whether to include it.[/dim]\n")

    selected: list[str] = []
    for key, (label, description, _) in modules.items():
        console.print(Panel(description, title=label, expand=False))
        if _ask_bool(f"[ ] Include {label}?", default=True):
            selected.append(key)

    if not selected:
        console.print("[yellow]No modules selected. Exiting.[/yellow]")
        raise SystemExit(0)
    return selected


def _target_from_options(
    host_os: str,
    target_connection: str,
    target_name: str | None,
    target_host: str | None,
    target_user: str | None,
    target_port: int | None,
    target_identity_file: str | None,
    target_become: bool | None,
) -> tuple[TargetConfig, bool | None]:
    if target_connection not in {"local", "ssh"}:
        raise ValueError("--target-connection must be either local or ssh")

    if target_connection == "local":
        return TargetConfig(name=target_name or "localhost"), target_become

    if not target_host:
        raise ValueError("--target-host is required when --target-connection is ssh")

    target = TargetConfig(
        name=target_name or "target",
        connection="ssh",
        host=target_host,
        user=target_user,
        port=target_port,
        identity_file=target_identity_file,
    )
    if target_become is None:
        target_become = host_os == "linux"
    return target, target_become


def _configure_target(host_os: str) -> tuple[TargetConfig | None, bool | None]:
    console.print("\n[bold]Target inventory[/bold]")
    console.print(
        "[dim]Replibook scans this machine, but the generated playbook can target this machine or another host over SSH.[/dim]"
    )

    use_ssh = _ask_bool("Generate inventory for another host over SSH?", default=False)
    if not use_ssh:
        return None, None

    host = _ask_text("Target IP or hostname:")
    if not host:
        console.print("[red]Target host cannot be empty.[/red]")
        raise SystemExit(1)

    name = _ask_text("Inventory name:", default="target")
    user = _ask_text("SSH user:", default=getpass.getuser())
    port_text = _ask_text("SSH port:", default="22")
    identity_file = _ask_text("SSH private key path (optional):")
    use_become = _ask_bool("Use sudo/become in the generated playbook?", default=(host_os == "linux"))

    try:
        port = int(port_text)
    except ValueError:
        console.print("[red]SSH port must be a number.[/red]")
        raise SystemExit(1)

    return (
        TargetConfig(
            name=name or "target",
            connection="ssh",
            host=host,
            user=user or None,
            port=port,
            identity_file=identity_file or None,
        ),
        use_become,
    )


def run(
    output: str,
    run_all: bool = False,
    target_connection: str = "local",
    target_name: str | None = None,
    target_host: str | None = None,
    target_user: str | None = None,
    target_port: int | None = None,
    target_identity_file: str | None = None,
    target_become: bool | None = None,
) -> None:
    host_os = detect_os()
    MODULES = _module_labels(host_os)

    console.print(Panel(
        f"[bold cyan]Replibook v{__version__}[/bold cyan]\n"
        f"Ansible Playbook Generator [dim]· detected: {host_os}[/dim]",
        expand=False,
    ))

    if run_all:
        selected_keys = list(MODULES.keys())
        target, use_become = _target_from_options(
            host_os,
            target_connection,
            target_name,
            target_host,
            target_user,
            target_port,
            target_identity_file,
            target_become,
        )
    else:
        selected_keys = _select_modules(MODULES)

        output_answer = questionary.text(
            "Output directory for playbooks:",
            default=output,
        ).ask()

        if output_answer is None:
            raise SystemExit(0)
        output = output_answer
        target, use_become = _configure_target(host_os)

    console.print("\n[bold]Scanning...[/bold]")

    scan_results: dict = {}
    for key in selected_keys:
        label, _, ScannerClass = MODULES[key]
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
    generator = PlaybookGenerator(scan_results, output, target=target, use_become=use_become)
    playbook_path, inventory_path = generator.generate()

    console.print()
    console.print(f"[green]✓[/green] Playbook written to: [bold]{playbook_path}[/bold]")
    console.print(f"[green]✓[/green] Inventory written to: [bold]{inventory_path}[/bold]")
    console.print("[dim]Review generated files before sharing or applying them.[/dim]")
