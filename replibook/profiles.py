from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScanProfile:
    key: str
    label: str
    description: str
    modules: tuple[str, ...]


SCAN_PROFILES: dict[str, ScanProfile] = {
    "role": ScanProfile(
        key="role",
        label="Role reproduction",
        description="Practical default for rebuilding a configured server or workstation without container noise.",
        modules=("system", "packages", "services", "scheduled_tasks", "network"),
    ),
    "terminal_server": ScanProfile(
        key="terminal_server",
        label="Terminal server",
        description="Captures the configuration most relevant for reproducing a terminal server.",
        modules=("system", "packages", "services", "scheduled_tasks", "network"),
    ),
    "web_server": ScanProfile(
        key="web_server",
        label="Web server",
        description="Captures packages, services, scheduled tasks, network context and optional container workloads.",
        modules=("system", "packages", "services", "scheduled_tasks", "docker", "deployments", "network"),
    ),
    "database_server": ScanProfile(
        key="database_server",
        label="Database server",
        description="Captures server packages, database-related services, scheduled jobs and network context for review.",
        modules=("system", "packages", "services", "scheduled_tasks", "network"),
    ),
    "workstation": ScanProfile(
        key="workstation",
        label="Workstation",
        description="Captures installed programs, local services, scheduled tasks and basic network context.",
        modules=("system", "packages", "services", "scheduled_tasks", "network"),
    ),
    "automation_node": ScanProfile(
        key="automation_node",
        label="Automation node",
        description="Captures packages, services, scheduled tasks and container workloads used by automation hosts.",
        modules=("system", "packages", "services", "scheduled_tasks", "docker", "deployments", "network"),
    ),
    "container_host": ScanProfile(
        key="container_host",
        label="Container host",
        description="Adds Docker containers and Compose deployments for Docker-focused hosts.",
        modules=("system", "packages", "services", "docker", "deployments", "network"),
    ),
    "full": ScanProfile(
        key="full",
        label="Full audit",
        description="Runs every available scanner. Useful for discovery, but often too noisy for reproduction.",
        modules=("system", "packages", "services", "scheduled_tasks", "docker", "deployments", "network"),
    ),
}


DEFAULT_SCAN_PROFILE = "role"


def profile_choices() -> list[ScanProfile]:
    return list(SCAN_PROFILES.values())


def modules_for_profile(profile: str, available_modules: dict) -> list[str]:
    """Return modules from a profile that exist on the current platform."""
    if profile not in SCAN_PROFILES:
        raise ValueError(f"Unknown scan profile: {profile}")
    return [key for key in SCAN_PROFILES[profile].modules if key in available_modules]
