import getpass

import questionary
from rich.console import Console
from rich.panel import Panel

from replibook.generator.playbook import PlaybookGenerator, TargetConfig
from replibook.modules import module_labels
from replibook.profiles import DEFAULT_SCAN_PROFILE, SCAN_PROFILES, modules_for_profile, profile_choices
from replibook.review import (
    build_review_report,
    filter_scan_results,
    save_snapshot,
    summarize_scan,
    write_review_report,
)
from replibook.runtime import scan_selected_modules
from replibook.utils import detect_os
from replibook.version import __version__

console = Console()


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


def _select_profile(modules: dict) -> tuple[str, list[str]]:
    choices = [
        questionary.Choice(
            title=f"{profile.label} — {profile.description}",
            value=profile.key,
        )
        for profile in profile_choices()
    ]
    answer = questionary.select(
        "What kind of scan do you want?",
        choices=choices,
        default=DEFAULT_SCAN_PROFILE,
    ).ask()
    if answer is None:
        raise SystemExit(0)
    return answer, modules_for_profile(answer, modules)


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


def _parse_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def _review_sections(scan_results: dict, excluded_sections: set[str], interactive: bool) -> tuple[dict, set[str]]:
    rows = summarize_scan(scan_results)
    if rows:
        console.print("\n[bold]Review preview[/bold]")
        for row in rows:
            console.print(
                f"  [dim]{row['label']}:[/dim] [white]{row['count']}[/white] "
                f"safety={row['safety']} — {row['reason']}"
            )

    if interactive:
        for row in rows:
            include = _ask_bool(f"Include {row['label']} in generated playbook?", default=True)
            if not include:
                excluded_sections.add(row["key"])

    filtered = filter_scan_results(scan_results, excluded_sections)
    report = build_review_report(filtered)
    if report["backup_hints"]:
        console.print("\n[bold yellow]Backup / migration notes[/bold yellow]")
        for hint in report["backup_hints"]:
            console.print(f"  [yellow]•[/yellow] {hint}")
    return filtered, excluded_sections


def run(
    output: str,
    run_all: bool = False,
    selected_modules: list[str] | None = None,
    profile: str | None = None,
    exclude_sections: str | None = None,
    save_snapshot_path: str | None = None,
    target_connection: str = "local",
    target_name: str | None = None,
    target_host: str | None = None,
    target_user: str | None = None,
    target_port: int | None = None,
    target_identity_file: str | None = None,
    target_become: bool | None = None,
) -> None:
    host_os = detect_os()
    MODULES = module_labels(host_os)

    console.print(Panel(
        f"[bold cyan]Replibook v{__version__}[/bold cyan]\n"
        f"Ansible Playbook Generator [dim]· detected: {host_os}[/dim]",
        expand=False,
    ))

    if sum(bool(value) for value in (run_all, selected_modules, profile)) > 1:
        raise ValueError("Use only one of --all, --modules or --profile")

    interactive_mode = not (run_all or selected_modules or profile)

    if run_all or selected_modules or profile:
        if profile:
            selected_keys = modules_for_profile(profile, MODULES)
            profile_label = SCAN_PROFILES[profile].label
            console.print(f"[dim]Scan profile:[/dim] {profile_label}")
        else:
            selected_keys = selected_modules or list(MODULES.keys())
        invalid = [key for key in selected_keys if key not in MODULES]
        if invalid:
            raise ValueError(f"Unknown scanner module(s): {', '.join(invalid)}")
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
        selected_profile, selected_keys = _select_profile(MODULES)
        profile = selected_profile
        console.print(f"[dim]Selected modules:[/dim] {', '.join(selected_keys)}")
        if _ask_bool("Fine-tune modules manually?", default=False):
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

    def print_progress(message: str) -> None:
        console.print(f"  [cyan]→[/cyan] {message.removeprefix('Scanning ').removesuffix('...')}")

    scan_results = scan_selected_modules(selected_keys, on_progress=print_progress)
    if save_snapshot_path:
        snapshot = save_snapshot(scan_results, save_snapshot_path)
        console.print(f"  [green]✓[/green] Scan snapshot written to: [bold]{snapshot}[/bold]")

    counts = {
        "system": len(scan_results.get("system", [])),
        "packages": len(scan_results.get("packages", [])),
        "services": len(scan_results.get("services", [])),
        "scheduled_tasks": len(scan_results.get("scheduled_tasks", [])),
        "docker": len(scan_results.get("docker", [])),
        "deployments": len(scan_results.get("deployments", [])),
        "network": len(scan_results.get("network", [])),
    }

    console.print()
    for key, count in counts.items():
        if key in scan_results:
            label = MODULES[key][0]
            console.print(f"  [dim]{label}:[/dim] [white]{count}[/white] found")

    scan_results, excluded = _review_sections(
        scan_results,
        _parse_csv(exclude_sections),
        interactive=interactive_mode,
    )
    if excluded:
        console.print(f"\n[dim]Excluded sections:[/dim] {', '.join(sorted(excluded))}")

    console.print("\n[bold]Generating playbook...[/bold]")
    review_report = write_review_report(scan_results, output)
    generator = PlaybookGenerator(scan_results, output, target=target, use_become=use_become)
    generator.review_report_path = str(review_report)
    playbook_path, inventory_path = generator.generate()

    console.print()
    console.print(f"[green]✓[/green] Playbook written to: [bold]{playbook_path}[/bold]")
    console.print(f"[green]✓[/green] Inventory written to: [bold]{inventory_path}[/bold]")
    console.print(f"[green]✓[/green] Review report written to: [bold]{review_report}[/bold]")
    console.print("[dim]Review generated files before sharing or applying them.[/dim]")
    console.print("[dim]GitHub: https://github.com/AlexRosbach/Replibook · Report a bug: https://github.com/AlexRosbach/Replibook/issues/new?template=bug_report.yml[/dim]")
