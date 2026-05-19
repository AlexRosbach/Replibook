import shutil
import subprocess
import sys
from pathlib import Path

import questionary
import yaml
from rich.console import Console
from rich.panel import Panel


console = Console()

NETWORK_MODULE_KEYS = {
    "community.general.nmcli",
}

NETWORK_SCALAR_VALUES = {
    "netplan",
    "networkmanager",
    "systemd-networkd",
}

NETWORK_MAPPING_KEYS = {
    "gateway",
    "gateway4",
    "gateway6",
    "nameserver",
    "nameservers",
    "network",
}

NETWORK_PATH_PREFIXES = (
    "/etc/network/interfaces",
    "/etc/netplan",
)

PATH_VALUE_KEYS = {
    "dest",
    "path",
    "src",
}

IGNORED_ENV_MAPPING_KEYS = {
    "env",
    "environment",
}


def _confirm(message: str, default: bool = False) -> bool:
    answer = questionary.confirm(message, default=default).ask()
    if answer is None:
        raise SystemExit(0)
    return answer


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


def _has_network_sensitive_content(value: object, parent_key: str | None = None) -> bool:
    """Recursively inspect parsed YAML for network-sensitive modules, keys, and paths.

    parent_key tracks the containing mapping key so env/environment blocks can be ignored
    and path-like values can be checked only for relevant YAML keys such as dest/path/src.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = key.lower() if isinstance(key, str) else None
            if parent_key in IGNORED_ENV_MAPPING_KEYS:
                continue
            if normalized_key in NETWORK_MODULE_KEYS or normalized_key in NETWORK_MAPPING_KEYS:
                return True
            if _has_network_sensitive_content(item, normalized_key):
                return True
        return False

    if isinstance(value, list):
        return any(_has_network_sensitive_content(item, parent_key) for item in value)

    if isinstance(value, str):
        normalized_value = value.strip().lower()
        if normalized_value in NETWORK_SCALAR_VALUES:
            return True
        if parent_key in PATH_VALUE_KEYS:
            return any(normalized_value.startswith(prefix) for prefix in NETWORK_PATH_PREFIXES)

    return False


def _contains_network_sensitive_content(playbook_path: Path) -> bool:
    try:
        with playbook_path.open(encoding="utf-8", errors="ignore") as handle:
            documents = yaml.safe_load_all(handle)
            return any(_has_network_sensitive_content(document) for document in documents)
    except (OSError, yaml.YAMLError):
        return False


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
