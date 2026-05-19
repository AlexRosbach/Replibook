from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel

from replibook.apply import apply_playbook
from replibook.cli import run as run_scan
from replibook.version import __version__


console = Console()


def run_wizard(output: str = "./playbooks") -> None:
    console.print(Panel(
        f"[bold cyan]Replibook v{__version__}[/bold cyan]\n"
        "Choose what you want to do.",
        expand=False,
    ))

    scan_now = _confirm("Do you want to scan this machine and generate a playbook?", default=True)
    if scan_now:
        run_scan(output=output, run_all=False)
        return

    console.print("\n[bold]Apply generated configuration[/bold]")
    console.print("[dim]Replibook will validate the selected files, offer missing dependencies, and then call Ansible.[/dim]")

    playbook = _text("Playbook path:", default=_guess_playbook(output))
    inventory = _text("Inventory path:", default=str(Path(output) / "inventory.ini"))
    check = _confirm("Run as a dry-run first (--check)?", default=True)
    install_deps = _confirm("Install Ansible dependencies if they are missing?", default=True)

    apply_playbook(
        playbook=playbook,
        inventory=inventory,
        check=check,
        yes=False,
        install_deps=install_deps,
    )


def _confirm(message: str, default: bool) -> bool:
    answer = questionary.confirm(message, default=default).ask()
    if answer is None:
        raise SystemExit(0)
    return answer


def _text(message: str, default: str = "") -> str:
    answer = questionary.text(message, default=default).ask()
    if answer is None:
        raise SystemExit(0)
    return answer.strip()


def _guess_playbook(output: str) -> str:
    output_dir = Path(output)
    if output_dir.exists():
        playbooks = sorted(output_dir.glob("*_playbook.yml"))
        if playbooks:
            return str(playbooks[-1])
    return str(output_dir / "myhost_playbook.yml")
