import typer
from replibook.version import __version__

app = typer.Typer(
    name="replibook",
    help="Scan a Linux server and generate an Ansible playbook.",
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"Replibook v{__version__}")
        raise typer.Exit()


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
    packages: bool | None = typer.Option(None, "--packages/--no-packages", help="Enable or disable package scanning"),
    services: bool | None = typer.Option(None, "--services/--no-services", help="Enable or disable service scanning"),
    docker: bool | None = typer.Option(None, "--docker/--no-docker", help="Enable or disable Docker scanning"),
    deployments: bool | None = typer.Option(None, "--deployments/--no-deployments", help="Enable or disable Compose scanning"),
    config: bool | None = typer.Option(None, "--config/--no-config", help="Enable or disable host config scanning"),
    redact_secrets: bool = typer.Option(True, "--redact-secrets/--no-redact-secrets", help="Redact detected secret env values"),
    vault_env_prefix: str | None = typer.Option(None, "--vault-env-prefix", help="Use vault placeholders for detected Docker secrets"),
    export_compose: bool = typer.Option(False, "--export-compose/--no-export-compose", help="Copy compose/env files into output directory"),
    include_user_services: bool = typer.Option(False, "--include-user-services", help="Include systemd --user services on Linux"),
    include_launchd: bool = typer.Option(False, "--include-launchd", help="Include launchd services on macOS"),
    snapshot: str | None = typer.Option(None, "--snapshot", help="Write scan snapshot JSON to this path"),
    version: bool = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    from replibook.cli import run
    run(
        output=output,
        run_all=run_all,
        include_packages=packages,
        include_services=services,
        include_docker=docker,
        include_deployments=deployments,
        include_config=config,
        redact_secrets=redact_secrets,
        vault_env_prefix=vault_env_prefix,
        export_compose=export_compose,
        include_user_services=include_user_services,
        include_launchd=include_launchd,
        snapshot_path=snapshot,
    )


@app.command()
def diff(
    old_snapshot: str = typer.Argument(..., help="Path to older snapshot JSON"),
    new_snapshot: str = typer.Argument(..., help="Path to newer snapshot JSON"),
) -> None:
    from replibook.cli import diff_snapshots
    diff_snapshots(old_snapshot, new_snapshot)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
