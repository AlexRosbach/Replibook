from dataclasses import dataclass, field
from datetime import datetime
import socket


@dataclass
class PackageInfo:
    name: str
    version: str
    manager: str = "apt"  # "apt" | "homebrew" | "homebrew_cask"
    state: str = "present"


@dataclass
class ServiceInfo:
    name: str
    enabled: bool
    state: str  # "started" | "stopped"
    manager: str = "systemd"  # "systemd" | "homebrew"


@dataclass
class ContainerInfo:
    name: str
    image: str
    ports: list = field(default_factory=list)
    volumes: list = field(default_factory=list)
    env_vars: dict = field(default_factory=dict)
    restart_policy: str = "unless-stopped"


@dataclass
class ComposeDeployment:
    directory: str
    name: str


@dataclass
class NetworkInterfaceInfo:
    name: str
    manager: str
    addresses: list[str] = field(default_factory=list)
    gateway4: str = ""
    nameservers: list[str] = field(default_factory=list)
    connection_name: str = ""
    method: str = "manual"


@dataclass
class SystemConfigInfo:
    hostname: str = ""
    timezone: str = ""
    locale: str = ""


@dataclass
class ScheduledTaskInfo:
    name: str
    source: str
    schedule: str = ""
    command: str = ""
    user: str = ""
    manager: str = "cron"


@dataclass
class ScanResult:
    hostname: str = field(default_factory=socket.gethostname)
    timestamp: datetime = field(default_factory=datetime.now)
    host_os: str = "linux"
    packages: list = field(default_factory=list)
    services: list = field(default_factory=list)
    containers: list = field(default_factory=list)
    deployments: list = field(default_factory=list)
    network: list = field(default_factory=list)
    system: list = field(default_factory=list)
    scheduled_tasks: list = field(default_factory=list)
