import shutil
import subprocess
import sys
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel


console = Console()

NETWORK_KEYWORDS = (
    "community.general.nmcli",
    "netplan",
    "networkmanager",
    "systemd-networkd",
    "/etc/network/interfaces",
    "/etc/netplan",
    "network:",
    "ip address",
    "gateway",
    "nameserver",
)


def _confirm(message: str, default: bool = False) -> bool:
    answer = questionary.confirm(message, default=default).ask()
    return bool(answer)


def _command_path(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found

    sibling = Path(sys.executable).parent / name
    if sibling.exists():
        return str(sibling)
    return None


def _install_ansible_dependencies() -> None:
    console.print("[bold]Installing Ansible dependencies...[/bold]")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ansible"])

    ansible_galaxy = _command_path("ansible-galaxy")
    if ansible_galaxy:
        subprocess.check_call([
            ansible_galaxy,
            "collection",
            "install",
            "community.docker",
            "community.general",
        ])
    else:
        console.print("[yellow]ansible-galaxy was not found after installing Ansible.[/yellow]")
        console.print("[dim]Install required collections manually if the playbook needs them.[/dim]")


def _contains_network_sensitive_content(playbook_path: Path) -> bool:
    try:
        content = playbook_path.read_text(errors="ignore").lower()
    except OSError:
        return False
    return any(keyword in content for keyword in NETWORK_KEYWORDS)


def apply_playbook(
    playbook: str,
    inventory: str = "inventory.ini",
    check: bool = False,
    yes: bool = False,
    install_deps: bool = False,
    confirm_network_changes: bool = False,
) -> None:
    playbook_path = Path(playbook)
    inventory_path = Path(inventory)

    if not playbook_path.exists():
        console.print(f"[red]Playbook not found:[/red] {playbook_path}")
        raise SystemExit(1)
    if not inventory_path.exists():
        console.print(f"[red]Inventory not found:[/red] {inventory_path}")
        raise SystemExit(1)
    ansible_playbook = _command_path("ansible-playbook")
    if not ansible_playbook:
        console.print("[yellow]ansible-playbook is not installed or not on PATH.[/yellow]")
        if install_deps or (not yes and _confirm("Install Ansible and common Replibook collections now?")):
            try:
                _install_ansible_dependencies()
            except subprocess.CalledProcessError as exc:
                console.print(f"[red]Dependency installation failed with exit code {exc.returncode}.[/red]")
                raise SystemExit(exc.returncode)
        else:
            console.print("[dim]Install Ansible first, then rerun this command.[/dim]")
            raise SystemExit(1)

    ansible_playbook = _command_path("ansible-playbook")
    if not ansible_playbook:
        console.print("[red]ansible-playbook is still not available after dependency handling.[/red]")
        raise SystemExit(1)

    network_sensitive = _contains_network_sensitive_content(playbook_path)
    if network_sensitive and not check and not confirm_network_changes:
        console.print(Panel(
            "This playbook appears to contain network-related configuration.\n"
            "Applying network changes can break SSH connectivity or remote access.",
            title="Network safety check",
            expand=False,
        ))
        if yes:
            console.print("[red]Refusing non-interactive network apply without --confirm-network-changes.[/red]")
            raise SystemExit(1)
        if not _confirm("I understand this may affect network connectivity. Continue?", default=False):
            console.print("[yellow]Apply cancelled.[/yellow]")
            raise SystemExit(0)

    command = [
        ansible_playbook,
        "-i",
        str(inventory_path),
        str(playbook_path),
    ]
    if check:
        command.append("--check")

    console.print(Panel(
        "\n".join([
            f"Playbook:  {playbook_path}",
            f"Inventory: {inventory_path}",
            f"Mode:      {'check/dry-run' if check else 'apply changes'}",
            f"Network:   {'sensitive content detected' if network_sensitive else 'no obvious network settings detected'}",
            "",
            "Replibook will now hand off to ansible-playbook.",
        ]),
        title="Apply generated configuration",
        expand=False,
    ))

    if not yes:
        if not _confirm("Continue?", default=False):
            console.print("[yellow]Apply cancelled.[/yellow]")
            raise SystemExit(0)

    raise SystemExit(subprocess.call(command))
