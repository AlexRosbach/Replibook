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
    version: bool = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    from replibook.cli import run
    run(output=output, run_all=run_all)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
