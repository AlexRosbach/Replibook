import typer
from click.core import ParameterSource
from replibook.version import __version__

app = typer.Typer(
    name="replibook",
    help="Scan a Linux, macOS or Windows host and generate an Ansible playbook.",
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
    modules: str | None,
    exclude_sections: str | None,
    save_snapshot: str | None,
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
            selected_modules=_parse_modules(modules),
            exclude_sections=exclude_sections,
            save_snapshot_path=save_snapshot,
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


def _output_option() -> str:
    return typer.Option(
        "./playbooks",
        "--output", "-o",
        help="Output directory for generated playbooks",
    )


def _run_all_option() -> bool:
    return typer.Option(
        False,
        "--all", "-a",
        help="Run all scanner modules without interactive selection",
    )


def _modules_option() -> str | None:
    return typer.Option(
        None,
        "--modules",
        help="Comma-separated scanner keys to run non-interactively, e.g. system,network,scheduled_tasks",
    )


def _exclude_sections_option() -> str | None:
    return typer.Option(
        None,
        "--exclude-sections",
        help="Comma-separated generated sections to omit after scan preview, e.g. network,scheduled_tasks",
    )


def _save_snapshot_option() -> str | None:
    return typer.Option(
        None,
        "--save-snapshot",
        help="Write raw scan data to a JSON file for review or later drift comparison",
    )


def _target_connection_option() -> str:
    return typer.Option(
        "local",
        "--target-connection",
        help="Inventory connection type: local or ssh",
    )


def _target_name_option() -> str | None:
    return typer.Option(
        None,
        "--target-name",
        help="Inventory host name",
    )


def _target_host_option() -> str | None:
    return typer.Option(
        None,
        "--target-host",
        help="Target IP address or hostname for SSH inventory",
    )


def _target_user_option() -> str | None:
    return typer.Option(
        None,
        "--target-user",
        help="SSH user for generated inventory",
    )


def _target_port_option() -> int | None:
    return typer.Option(
        None,
        "--target-port",
        help="SSH port for generated inventory",
    )


def _target_identity_file_option() -> str | None:
    return typer.Option(
        None,
        "--target-key",
        help="SSH private key path for generated inventory",
    )


def _target_become_option() -> bool | None:
    return typer.Option(
        None,
        "--target-become/--no-target-become",
        help="Override become/sudo usage in the generated playbook",
    )


def _version_option() -> bool:
    return typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit",
    )


def _parse_modules(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def _resolve_scan_option(ctx: typer.Context, name: str, value: object) -> object:
    """Return an explicitly provided scan value, else inherit an explicitly provided parent callback value."""
    if ctx.get_parameter_source(name) is not ParameterSource.DEFAULT:
        return value

    parent = ctx.parent
    if parent and parent.get_parameter_source(name) is not ParameterSource.DEFAULT:
        return parent.params.get(name, value)

    return value


def _has_explicit_scan_option(ctx: typer.Context) -> bool:
    return any(
        ctx.get_parameter_source(name) is not ParameterSource.DEFAULT
        for name in (
            "output",
            "run_all",
            "modules",
            "exclude_sections",
            "save_snapshot",
            "target_connection",
            "target_name",
            "target_host",
            "target_user",
            "target_port",
            "target_identity_file",
            "target_become",
        )
    )


@app.callback()
def default(
    ctx: typer.Context,
    output: str = _output_option(),
    run_all: bool = _run_all_option(),
    modules: str | None = _modules_option(),
    exclude_sections: str | None = _exclude_sections_option(),
    save_snapshot: str | None = _save_snapshot_option(),
    target_connection: str = _target_connection_option(),
    target_name: str | None = _target_name_option(),
    target_host: str | None = _target_host_option(),
    target_user: str | None = _target_user_option(),
    target_port: int | None = _target_port_option(),
    target_identity_file: str | None = _target_identity_file_option(),
    target_become: bool | None = _target_become_option(),
    version: bool = _version_option(),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    if not _has_explicit_scan_option(ctx):
        from replibook.wizard import run_wizard

        run_wizard(output=output)
        return

    _run_scan(
        output=output,
        run_all=run_all,
        modules=modules,
        exclude_sections=exclude_sections,
        save_snapshot=save_snapshot,
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
    ctx: typer.Context,
    output: str = _output_option(),
    run_all: bool = _run_all_option(),
    modules: str | None = _modules_option(),
    exclude_sections: str | None = _exclude_sections_option(),
    save_snapshot: str | None = _save_snapshot_option(),
    target_connection: str = _target_connection_option(),
    target_name: str | None = _target_name_option(),
    target_host: str | None = _target_host_option(),
    target_user: str | None = _target_user_option(),
    target_port: int | None = _target_port_option(),
    target_identity_file: str | None = _target_identity_file_option(),
    target_become: bool | None = _target_become_option(),
    version: bool = _version_option(),
) -> None:
    resolved = {
        name: _resolve_scan_option(ctx, name, value)
        for name, value in (
            ("output", output),
            ("run_all", run_all),
            ("modules", modules),
            ("exclude_sections", exclude_sections),
            ("save_snapshot", save_snapshot),
            ("target_connection", target_connection),
            ("target_name", target_name),
            ("target_host", target_host),
            ("target_user", target_user),
            ("target_port", target_port),
            ("target_identity_file", target_identity_file),
            ("target_become", target_become),
        )
    }

    _run_scan(
        output=resolved["output"],
        run_all=resolved["run_all"],
        modules=resolved["modules"],
        exclude_sections=resolved["exclude_sections"],
        save_snapshot=resolved["save_snapshot"],
        target_connection=resolved["target_connection"],
        target_name=resolved["target_name"],
        target_host=resolved["target_host"],
        target_user=resolved["target_user"],
        target_port=resolved["target_port"],
        target_identity_file=resolved["target_identity_file"],
        target_become=resolved["target_become"],
    )


@app.command()
def modules() -> None:
    """List scanner keys available on this platform."""
    from replibook.modules import module_labels
    from replibook.utils import detect_os

    host_os = detect_os()
    typer.echo(f"Detected backend: {host_os}")
    for key, (label, description, _) in module_labels(host_os).items():
        typer.echo(f"{key}\t{label}\t{description}")


@app.command("diff")
def diff(
    before: str = typer.Argument(..., help="Earlier scan snapshot JSON"),
    after: str = typer.Argument(..., help="Later scan snapshot JSON"),
) -> None:
    """Compare two scan snapshots and show added, removed and changed items."""
    import json
    from replibook.review import diff_snapshots, load_snapshot

    result = diff_snapshots(load_snapshot(before), load_snapshot(after))
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@app.command("remote-recipe")
def remote_recipe(
    host: str = typer.Argument(..., help="SSH host to scan"),
    user: str | None = typer.Option(None, "--user", "-u", help="SSH user"),
    port: int = typer.Option(22, "--port", "-p", help="SSH port"),
    output: str = typer.Option("./playbooks", "--output", "-o", help="Local output folder after copying the snapshot"),
) -> None:
    """Print a copy-paste remote scan workflow using scan snapshots."""
    prefix = f"{user + '@' if user else ''}{host}"
    remote_snapshot = "/tmp/replibook-scan.json"
    typer.echo("Run this workflow from the machine that should collect the remote inventory:")
    typer.echo("")
    typer.echo(f"ssh -p {port} {prefix} 'python3 -m pip install --user git+https://github.com/AlexRosbach/Replibook.git && python3 -m replibook.main scan --all --save-snapshot {remote_snapshot} --output /tmp/replibook-remote --no-target-become'")
    typer.echo(f"scp -P {port} {prefix}:{remote_snapshot} ./replibook-{host}.json")
    typer.echo("")
    typer.echo("Then compare it later with:")
    typer.echo(f"replibook diff ./replibook-{host}.json ./replibook-{host}-new.json")
    typer.echo("")
    typer.echo(f"Use {output} as the local playbook output folder when generating from a local scan or reviewed workflow.")


@app.command()
def gui() -> None:
    """Start the Replibook desktop app."""
    from replibook.gui.app import main as gui_main

    gui_main()


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
