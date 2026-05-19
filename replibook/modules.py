from replibook.scanner import (
    DeploymentScanner,
    DockerScanner,
    NetworkScanner,
    PackageScanner,
    ScheduledTaskScanner,
    ServiceScanner,
    SystemScanner,
)


def module_labels(host_os: str) -> dict:
    """Return scanner metadata for the current backend platform."""
    if host_os == "macos":
        return {
            "system": (
                "System Configuration",
                "Reads hostname, timezone and locale as a baseline for the target host.",
                SystemScanner,
            ),
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
            "scheduled_tasks": (
                "Scheduled Tasks",
                "Reads user cron entries and LaunchAgents/LaunchDaemons as reviewable scheduled tasks.",
                ScheduledTaskScanner,
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
            "network": (
                "Network Configuration",
                "Reads IP details from macOS network services.",
                NetworkScanner,
            ),
        }
    if host_os == "windows":
        return {
            "system": (
                "System Configuration",
                "Reads hostname, timezone and locale from Windows.",
                SystemScanner,
            ),
            "packages": (
                "Installed Programs",
                "Reads installed applications from the Windows uninstall registry.",
                PackageScanner,
            ),
            "services": (
                "Windows Services",
                "Reads running and automatically started Windows services.",
                ServiceScanner,
            ),
            "scheduled_tasks": (
                "Scheduled Tasks",
                "Reads non-Microsoft Windows Task Scheduler entries for review.",
                ScheduledTaskScanner,
            ),
            "docker": (
                "Docker Containers & Images",
                "Reads Docker Desktop containers, images, ports, volumes and environment values.",
                DockerScanner,
            ),
            "deployments": (
                "Docker Compose Deployments",
                "Searches common Windows project folders for Compose files.",
                DeploymentScanner,
            ),
            "network": (
                "Network Configuration",
                "Reads Windows interface addresses, gateways and DNS through PowerShell.",
                NetworkScanner,
            ),
        }
    return {
        "system": (
            "System Configuration",
            "Reads hostname, timezone and locale as a baseline for the target host.",
            SystemScanner,
        ),
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
        "scheduled_tasks": (
            "Scheduled Tasks",
            "Reads user crontab, /etc/crontab, /etc/cron.d and periodic cron directories.",
            ScheduledTaskScanner,
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
        "network": (
            "Network Configuration",
            "Reads interface addresses, default gateway, DNS and NetworkManager details when available.",
            NetworkScanner,
        ),
    }
