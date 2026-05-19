import typer
from replibook.version import __version__

app = typer.Typer(
    name="replibook",
    help="Scan a Linux or macOS host and generate an Ansible playbook.",
    add_completion=False,
    invoke_without_command=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"Replibook v{__version__}")
        raise typer.Exit()


def _run_scan(
    output: str,
    run_all: bool,
    target_connection: str,
    target_name: str | None,
    target_host: str | None,
    target_user: str | None,
    target_port: int | None,
    target_identity_file: str | None,
    target_become: bool | None,
) -> None:
    from replibook.cli import run

    try:
        run(
            output=output,
            run_all=run_all,
            target_connection=target_connection,
            target_name=target_name,
            target_host=target_host,
            target_user=target_user,
            target_port=target_port,
            target_identity_file=target_identity_file,
            target_become=target_become,
        )
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)


@app.callback()
def default(
    ctx: typer.Context,
    output: str = typer.Option(
        "./playbooks",
        "--output", "-o",
        help="Output directory for generated playbooks",
    ),
    run_all: bool = typer.Option(
        False,
        "--all", "-a",
        help="Run all scanner modules without interactive selection",
    ),
    target_connection: str = typer.Option(
        "local",
        "--target-connection",
        help="Inventory connection type: local or ssh",
    ),
    target_name: str | None = typer.Option(
        None,
        "--target-name",
        help="Inventory host name",
    ),
    target_host: str | None = typer.Option(
        None,
        "--target-host",
        help="Target IP address or hostname for SSH inventory",
    ),
    target_user: str | None = typer.Option(
        None,
        "--target-user",
        help="SSH user for generated inventory",
    ),
    target_port: int | None = typer.Option(
        None,
        "--target-port",
        help="SSH port for generated inventory",
    ),
    target_identity_file: str | None = typer.Option(
        None,
        "--target-key",
        help="SSH private key path for generated inventory",
    ),
    target_become: bool | None = typer.Option(
        None,
        "--target-become/--no-target-become",
        help="Override become/sudo usage in the generated playbook",
    ),
    version: bool = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    _run_scan(
        output=output,
        run_all=run_all,
        target_connection=target_connection,
        target_name=target_name,
        target_host=target_host,
        target_user=target_user,
        target_port=target_port,
        target_identity_file=target_identity_file,
        target_become=target_become,
    )


@app.command()
def scan(
    output: str = typer.Option(
        "./playbooks",
        "--output", "-o",
        help="Output directory for generated playbooks",
    ),
    run_all: bool = typer.Option(
        False,
        "--all", "-a",
        help="Run all scanner modules without interactive selection",
    ),
    target_connection: str = typer.Option(
        "local",
        "--target-connection",
        help="Inventory connection type: local or ssh",
    ),
    target_name: str | None = typer.Option(
        None,
        "--target-name",
        help="Inventory host name",
    ),
    target_host: str | None = typer.Option(
        None,
        "--target-host",
        help="Target IP address or hostname for SSH inventory",
    ),
    target_user: str | None = typer.Option(
        None,
        "--target-user",
        help="SSH user for generated inventory",
    ),
    target_port: int | None = typer.Option(
        None,
        "--target-port",
        help="SSH port for generated inventory",
    ),
    target_identity_file: str | None = typer.Option(
        None,
        "--target-key",
        help="SSH private key path for generated inventory",
    ),
    target_become: bool | None = typer.Option(
        None,
        "--target-become/--no-target-become",
        help="Override become/sudo usage in the generated playbook",
    ),
    version: bool = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    _run_scan(
        output=output,
        run_all=run_all,
        target_connection=target_connection,
        target_name=target_name,
        target_host=target_host,
        target_user=target_user,
        target_port=target_port,
        target_identity_file=target_identity_file,
        target_become=target_become,
    )


@app.command()
def apply(
    playbook: str = typer.Argument(..., help="Generated playbook file"),
    inventory: str = typer.Option(
        "inventory.ini",
        "--inventory", "-i",
        help="Inventory file to use",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Run Ansible in check mode",
    ),
    yes: bool = typer.Option(
        False,
        "--yes", "-y",
        help="Skip confirmation prompt",
    ),
    install_deps: bool = typer.Option(
        False,
        "--install-deps",
        help="Install Ansible and common required collections if missing",
    ),
    confirm_network_changes: bool = typer.Option(
        False,
        "--confirm-network-changes",
        help="Allow non-interactive apply of network-sensitive playbooks",
    ),
) -> None:
    from replibook.apply import apply_playbook

    apply_playbook(
        playbook=playbook,
        inventory=inventory,
        check=check,
        yes=yes,
        install_deps=install_deps,
        confirm_network_changes=confirm_network_changes,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
