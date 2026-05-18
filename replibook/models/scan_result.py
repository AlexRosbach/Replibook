from dataclasses import dataclass, field
from datetime import datetime
import socket


@dataclass
class PackageInfo:
    name: str
    version: str
    manager: str = "apt"  # apt | homebrew | homebrew_cask | dnf | yum | zypper | pacman | rpm
    state: str = "present"


@dataclass
class ServiceInfo:
    name: str
    enabled: bool
    state: str  # "started" | "stopped"
    manager: str = "systemd"  # systemd | systemd_user | homebrew | launchd


@dataclass
class ContainerInfo:
    name: str
    image: str
    ports: list = field(default_factory=list)
    volumes: list = field(default_factory=list)
    env_vars: dict = field(default_factory=dict)
    vault_vars: dict = field(default_factory=dict)
    restart_policy: str = "unless-stopped"


@dataclass
class ComposeDeployment:
    directory: str
    name: str
    compose_file: str = ""
    env_files: list = field(default_factory=list)


@dataclass
class CronJobInfo:
    source: str
    line: str


@dataclass
class SSHSettingInfo:
    key: str
    value: str


@dataclass
class HostConfigState:
    users: list = field(default_factory=list)
    groups: list = field(default_factory=list)
    cron_jobs: list[CronJobInfo] = field(default_factory=list)
    ssh_settings: list[SSHSettingInfo] = field(default_factory=list)
    firewall_rules: list = field(default_factory=list)
    mounts: list = field(default_factory=list)
    sysctl: dict = field(default_factory=dict)


@dataclass
class ScanResult:
    hostname: str = field(default_factory=socket.gethostname)
    timestamp: datetime = field(default_factory=datetime.now)
    host_os: str = "linux"
    packages: list = field(default_factory=list)
    services: list = field(default_factory=list)
    containers: list = field(default_factory=list)
    deployments: list = field(default_factory=list)
    config: HostConfigState = field(default_factory=HostConfigState)
