# Replibook — Documentation

## Table of Contents

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Windows Desktop App](#windows-desktop-app)
6. [Scanner Modules](#scanner-modules)
7. [Generated Output](#generated-output)
8. [Applying the Playbook](#applying-the-playbook)
9. [Operational Boundaries](#operational-boundaries)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Replibook scans a running Linux or macOS machine and produces a working Ansible playbook that can recreate it on a new host. It auto-detects the operating system and uses the right toolchain on each:

- **Linux** — `apt` / `dpkg` for packages, `systemd` for services
- **macOS** — `Homebrew` formulas and casks, `brew services`

Docker container and Docker Compose deployment scanning works identically on both platforms.
System and network configuration scanning provide additional context for reproducing a host, with network changes guarded by review steps.

For quick setup and common failure cases, also see the [Knowledge Base / FAQ](knowledgebase.md).

---

## Requirements

- **OS**: Linux (Debian/Ubuntu), macOS or Windows
- **Python**: 3.10 or higher
- **Optional**: Docker daemon (for container scanning)
- **Optional**: Homebrew (macOS only, for package/service scanning)
- **Optional on Windows app**: WSL or another Ansible-capable command for applying playbooks

---

## Installation

### Recommended: pipx from GitHub

`pipx` installs Replibook in an isolated environment without polluting your system Python.

**macOS:**
```bash
brew install pipx
pipx install git+https://github.com/AlexRosbach/Replibook.git@v1.0.1
```

**Linux:**
```bash
apt install pipx
# or: pip install --user pipx
pipx install git+https://github.com/AlexRosbach/Replibook.git@v1.0.1
```

### Install a specific version

```bash
pipx install git+https://github.com/AlexRosbach/Replibook.git@v1.0.1
# replace @v1.0.1 with another tag, or omit @<tag> for latest development
```

### Alternative: pip from GitHub

```bash
python3 -m pip install --user git+https://github.com/AlexRosbach/Replibook.git@v1.0.1
# or inside a virtual environment:
python3 -m pip install git+https://github.com/AlexRosbach/Replibook.git@v1.0.1
```

### From source

```bash
git clone https://github.com/AlexRosbach/Replibook.git
cd Replibook
pip install -e .
```

### Windows executable

`Replibook.exe` is built by the `Build Windows Desktop App` GitHub Actions workflow and published as a workflow artifact. Release builds can attach the same artifact to the GitHub release assets.

To build it manually on Windows:

```powershell
git clone https://github.com/AlexRosbach/Replibook.git
cd Replibook
.\scripts\build-windows.ps1
```

The output is written to `dist\Replibook.exe`.

---

## Usage

### Interactive mode

Run without arguments to launch the interactive menu:

```bash
replibook
```

You'll be prompted to:
1. Choose whether to scan this machine or apply an existing playbook
2. Select which modules to scan, with a short explanation for each module
3. Confirm or change the output directory
4. Decide whether the generated inventory targets this machine or another host over SSH

### One-shot mode

```bash
# Scan everything, use default output dir
replibook --all

# Scan everything, custom output dir
replibook --all --output /opt/playbooks

# Scan everything and generate SSH inventory for another host
replibook --all \
  --target-connection ssh \
  --target-name web01 \
  --target-host 192.168.1.50 \
  --target-user ubuntu \
  --target-port 22 \
  --target-key ~/.ssh/id_rsa
```

### All options

| Option | Short | Default | Description |
|---|---|---|---|
| `--output` | `-o` | `./playbooks` | Directory where playbooks are written |
| `--all` | `-a` | `false` | Skip menu, run all modules |
| `--modules` | | | Comma-separated scanner keys for automation, e.g. `system,network,scheduled_tasks` |
| `--target-connection` | | `local` | Inventory connection type: `local` or `ssh` |
| `--target-name` | | | Inventory host name |
| `--target-host` | | | Target IP address or hostname for SSH inventory |
| `--target-user` | | | SSH user for generated inventory |
| `--target-port` | | | SSH port for generated inventory |
| `--target-key` | | | SSH private key path for generated inventory |
| `--target-become` / `--no-target-become` | | OS default | Override sudo/become usage in the generated playbook |
| `--version` | | | Print version and exit |
| `--help` | | | Show help and exit |

### Commander / automation usage

Every major workflow exposed by the desktop app is also reachable from the command line:

```bash
# List scanner module keys for this platform
replibook modules

# Run only selected scanner modules
replibook scan --modules system,network,scheduled_tasks --output ./playbooks

# Run all scanners without prompts
replibook scan --all --output ./playbooks

# Launch the desktop app from a shell or automation launcher
replibook gui

# Apply from automation
replibook apply ./playbooks/myhost_playbook.yml --inventory ./playbooks/inventory.ini --check --yes
```

### Apply command

Replibook can also guide the handoff to Ansible:

```bash
# Confirm and apply a generated playbook
replibook apply ./playbooks/myhost_playbook.yml --inventory ./playbooks/inventory.ini

# Dry-run with Ansible check mode
replibook apply ./playbooks/myhost_playbook.yml --inventory ./playbooks/inventory.ini --check

# Install missing Ansible dependencies before applying
replibook apply ./playbooks/myhost_playbook.yml --inventory ./playbooks/inventory.ini --install-deps
```

The `apply` command does not hide Ansible. It validates the selected files, offers to install missing Ansible dependencies, shows what will run, asks for confirmation, then calls `ansible-playbook`.

If network-related configuration is detected, Replibook asks for a second confirmation before applying changes. In non-interactive runs, network-sensitive playbooks require `--confirm-network-changes`; otherwise Replibook refuses to apply them.

## Windows Desktop App

The Windows app is a thin frontend over the same Replibook scanner, generator and apply workflow. It is meant for operators who want a clickable tool without replacing the backend.

What it does:
- creates playbook and inventory files through the shared generator backend
- runs native Windows scans for system, installed programs, services, network settings, Docker, Compose files and scheduled tasks
- exposes target inventory settings for local and SSH targets
- applies generated playbooks by calling an Ansible command
- defaults to `wsl ansible-playbook` on Windows, but accepts a custom command
- blocks network-sensitive playbooks unless the user explicitly enables network confirmation

Important limitation:

Windows inventory differs from Linux/macOS inventory. Replibook records Windows programs and some scheduler details as review-first facts when there is no safe, generic Ansible install task. That keeps the information visible without generating fragile automation.

---

## Scanner Modules

### System Configuration

Reads hostname, timezone and locale. Generated playbooks include hostname/timezone tasks where supported and a locale review message.

### Network Configuration

**Linux:** Reads interface IPv4 addresses through `ip`, default gateway through `ip route`, DNS through `resolvectl` or `/etc/resolv.conf`, and NetworkManager connection details through `nmcli` when available.

**macOS:** Reads network services, IP details, router and DNS through `networksetup`.

**Windows:** Reads interface aliases, IPv4 addresses, gateways and DNS servers through `Get-NetIPConfiguration`.

Network output is intentionally conservative. Replibook records the discovered settings and emits disabled NetworkManager example tasks when enough data is available. Review interface names, IP addresses, gateways and DNS before enabling those tasks.

### Scheduled Tasks

**Linux:** Reads the current user's crontab, `/etc/crontab`, files in `/etc/cron.d`, and scripts in `/etc/cron.hourly`, `/etc/cron.daily`, `/etc/cron.weekly` and `/etc/cron.monthly`.

**macOS:** Reads the current user's crontab plus plist names from user and system LaunchAgents/LaunchDaemons locations.

**Windows:** Reads non-Microsoft Windows Task Scheduler entries for review. Replibook does not try to recreate arbitrary scheduled tasks automatically because triggers, principals and credentials need operator review.

Scheduled task output is generated as review-first content. Replibook records source, schedule, user and command where available; cron recreation tasks are disabled by default so paths, users, environment and secrets can be reviewed first.

### Packages

**Linux:** Reads `apt-mark showmanual` to get packages the user explicitly installed (not auto-installed dependencies). Falls back to `dpkg-query` if `apt-mark` is unavailable. Generates `ansible.builtin.apt` tasks.

**macOS:** Reads `brew list --installed-on-request --formula` (formulas) and `brew list --cask` (apps). Generates `community.general.homebrew` and `community.general.homebrew_cask` tasks.

**Windows:** Reads installed programs from the Windows uninstall registry. These entries are emitted as review facts because many installers do not expose a safe unattended install command.

### Services

**Linux:** Reads `systemctl list-unit-files --state=enabled` (enabled services) and `list-units --state=active` (currently running). Kernel/transient units are filtered. Generates `ansible.builtin.service` tasks.

**macOS:** Reads `brew services list` to find Homebrew-managed services. Generates `community.general.homebrew_services` tasks. (Launchd-only services outside Homebrew are not scanned.)

**Windows:** Reads running or automatically started services through PowerShell. Generated `ansible.windows.win_service` tasks are disabled by default until service impact is reviewed.

### Docker Containers

Connects to the local Docker daemon via the Docker SDK. Captures container name, image, port mappings, volume mounts, environment variables, and restart policy. Generates `community.docker.docker_container` tasks.

> ⚠ Environment variables are included verbatim. **Review before committing** — replace any secrets with Ansible Vault references.

### Docker Compose Deployments

Searches for `docker-compose.yml`, `docker-compose.yaml`, `compose.yml` or `compose.yaml` files. Skips noise directories (`.git`, `node_modules`, `venv`, `build`, `dist`, `__pycache__`, etc.) for fast scanning.

Search roots:
- **Linux:** `/opt`, `/srv`, `/home`, `/root`, `/docker`, `/var/lib`
- **macOS:** `/Users`, `/opt`, `/usr/local`

Generates `community.docker.docker_compose_v2` tasks.

---

## Generated Output

Two files written to the output directory:

| File | Description |
|---|---|
| `<hostname>_playbook.yml` | The Ansible playbook |
| `inventory.ini` | Inventory file for local execution or the SSH target selected in the wizard/options |

### inventory.ini

```ini
[replibook]
myhost ansible_connection=local
```

SSH target:

```ini
[replibook]
web01 ansible_host=192.168.1.50 ansible_user=ubuntu ansible_port=22 ansible_ssh_private_key_file=~/.ssh/id_rsa
```

### Playbook structure

```yaml
---
# Generated by Replibook on 2025-05-18 14:32:00
# Source host: myhost (linux)

- name: Replibook — Reproduce myhost
  hosts: replibook
  become: true        # false on macOS — Homebrew refuses to run as root
  tasks:
    # ── Apt Packages ──        (Linux only)
    # ── Homebrew Formulas ──   (macOS only)
    # ── Homebrew Casks ──      (macOS only)
    # ── Systemd Services ──    (Linux only)
    # ── Homebrew Services ──   (macOS only)
    # ── Scheduled Tasks ──
    # ── Docker Containers ──
    # ── Docker Compose Deployments ──
```

---

## Applying the Playbook

### 1. Install Ansible dependencies

Replibook can install Ansible and common required collections when `apply` runs:

```bash
replibook apply myhost_playbook.yml --inventory inventory.ini --install-deps
```

Manual equivalent:

```bash
pip install ansible
ansible-galaxy collection install community.docker
ansible-galaxy collection install community.general
```

### 2. Apply locally

```bash
replibook apply myhost_playbook.yml --inventory inventory.ini
```

### 3. Apply remotely

Either configure the SSH target in the Replibook wizard or edit `inventory.ini` manually:

```ini
[replibook]
192.168.1.50 ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/id_rsa
```

Then run from your workstation:

```bash
replibook apply myhost_playbook.yml --inventory inventory.ini
```

Use `--check` first if you want Ansible to report planned changes without applying them.

Network-sensitive playbooks are guarded:

```bash
replibook apply network_playbook.yml --inventory inventory.ini --yes --confirm-network-changes
```

---

## Operational Boundaries

- Replibook does not guarantee a byte-for-byte clone of a machine. It creates a practical Ansible starting point from installed packages, services, Docker containers, Compose deployments, system settings and network metadata.
- Generated playbooks can include sensitive Docker environment variables. Review and replace secrets with Ansible Vault variables before sharing output.
- Replibook does not back up Docker volumes, bind-mounted files, databases, uploads, application data or arbitrary files. Back up and restore data separately.
- The `apply` command is a convenience wrapper around `ansible-playbook`; understanding and reviewing the generated playbook still matters.
- Network-related playbooks require extra confirmation because they can interrupt SSH connectivity or remote access.
- Generated network tasks are disabled examples where appropriate; enable them only after review.
- Scheduled task recreation tasks are disabled examples where appropriate; review user context, paths and secrets before enabling them.
- Linux package scanning currently targets apt/dpkg-based systems. RPM-based distributions are not supported yet.
- macOS scanning targets Homebrew-managed packages and services. Launchd services outside Homebrew are not scanned.
- Docker Compose discovery records project directories; it does not copy compose files, env files or application data.

---

## Troubleshooting

### `command not found: replibook` after install

`pipx` install location may not be on your `PATH`. Run once:

```bash
pipx ensurepath
```

Restart your shell.

### Permission denied on Docker socket (Linux)

Either run with `sudo` or add your user to the `docker` group:

```bash
sudo usermod -aG docker $USER
# Log out + back in
```

### Package scanner returns empty on macOS

You need Homebrew installed: https://brew.sh

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Package scanner returns empty on Linux

Replibook expects `apt-mark` or `dpkg-query`. On RPM-based systems (RHEL/Fedora/CentOS) the package scanner is not yet supported — track [issue tracker](../../issues) for status.

### Generated playbook fails on the target

- Confirm the target OS matches the source (the playbook uses OS-specific modules)
- Install required Ansible collections (see above)
- Review the playbook for secrets in environment variables before applying

### `brew services list` is empty on macOS

That's normal if you haven't started any services via `brew services start <name>`. Services started another way (Launchd plists, `.app` bundles) aren't scanned.
