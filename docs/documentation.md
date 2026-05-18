# Replibook — Documentation

## Table of Contents

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Scanner Modules](#scanner-modules)
6. [Generated Output](#generated-output)
7. [Applying the Playbook](#applying-the-playbook)
8. [Operational Boundaries](#operational-boundaries)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Replibook scans a running Linux or macOS machine and produces a working Ansible playbook that can recreate it on a new host. It auto-detects the operating system and uses the right toolchain on each:

- **Linux** — `apt` / `dpkg` for packages, `systemd` for services
- **macOS** — `Homebrew` formulas and casks, `brew services`

Docker container and Docker Compose deployment scanning works identically on both platforms.

For quick setup and common failure cases, also see the [Knowledge Base / FAQ](knowledgebase.md).

---

## Requirements

- **OS**: Linux (Debian/Ubuntu) or macOS
- **Python**: 3.10 or higher
- **Optional**: Docker daemon (for container scanning)
- **Optional**: Homebrew (macOS only, for package/service scanning)

---

## Installation

### Recommended: pipx

`pipx` installs Replibook in an isolated environment without polluting your system Python.

**macOS:**
```bash
brew install pipx
pipx install replibook
```

**Linux:**
```bash
apt install pipx
# or: pip install --user pipx
pipx install replibook
```

### Alternative: pip

```bash
pip install replibook
```

### From source

```bash
git clone https://github.com/AlexRosbach/replibook.git
cd replibook
pip install -e .
```

---

## Usage

### Interactive mode

Run without arguments to launch the interactive menu:

```bash
replibook
```

You'll be prompted to:
1. Select which modules to scan (checkbox menu, all selected by default)
2. Confirm or change the output directory

### One-shot mode

```bash
# Scan everything, use default output dir
replibook --all

# Scan everything, custom output dir
replibook --all --output /opt/playbooks
```

### All options

| Option | Short | Default | Description |
|---|---|---|---|
| `--output` | `-o` | `./playbooks` | Directory where playbooks are written |
| `--all` | `-a` | `false` | Skip menu, run all modules |
| `--packages/--no-packages` | | interactive | Toggle package scanning |
| `--services/--no-services` | | interactive | Toggle service scanning |
| `--docker/--no-docker` | | interactive | Toggle Docker container scanning |
| `--deployments/--no-deployments` | | interactive | Toggle compose deployment scanning |
| `--config/--no-config` | | interactive | Toggle host config/state scanning |
| `--redact-secrets/--no-redact-secrets` | | `true` | Redact detected secret env vars from Docker output |
| `--vault-env-prefix` | | | Generate Vault-style placeholders for detected Docker secrets |
| `--export-compose/--no-export-compose` | | `false` | Export compose and discovered env files into output directory |
| `--include-user-services` | | `false` | Include `systemctl --user` services (Linux) |
| `--include-launchd` | | `false` | Include launchd service discovery (macOS) |
| `--snapshot` | | | Write scan snapshot JSON |
| `diff <old> <new>` | | | Compare two snapshots and show added/removed items |
| `--version` | | | Print version and exit |
| `--help` | | | Show help and exit |

---

## Scanner Modules

### Packages

**Linux:** Supports `apt`/`dpkg`, `dnf`/`yum`/`zypper`/`rpm`, and `pacman` package inventories. Generates `ansible.builtin.apt` tasks for apt and `ansible.builtin.package` tasks for other Linux package sets.

**macOS:** Reads `brew list --installed-on-request --formula` (formulas) and `brew list --cask` (apps). Generates `community.general.homebrew` and `community.general.homebrew_cask` tasks.

### Services

**Linux:** Reads `systemctl list-unit-files --state=enabled` (enabled services) and `list-units --state=active` (currently running). Kernel/transient units are filtered. Generates `ansible.builtin.service` tasks.

**macOS:** Reads `brew services list` to find Homebrew-managed services. Generates `community.general.homebrew_services` tasks. Optional `--include-launchd` adds launchd discovery metadata.

**Linux optional:** `--include-user-services` adds `systemctl --user` service discovery.

### Docker Containers

Connects to the local Docker daemon via the Docker SDK. Captures container name, image, port mappings, volume mounts, environment variables, and restart policy. Generates `community.docker.docker_container` tasks.

By default, secret-like env keys are redacted. Use `--vault-env-prefix` to emit Vault-style placeholders and generate `vault_vars.example.yml`.

### Docker Compose Deployments

Searches for `docker-compose.yml`, `docker-compose.yaml`, `compose.yml` or `compose.yaml` files. Skips noise directories (`.git`, `node_modules`, `venv`, `build`, `dist`, `__pycache__`, etc.) for fast scanning.

Search roots:
- **Linux:** `/opt`, `/srv`, `/home`, `/root`, `/docker`, `/var/lib`
- **macOS:** `/Users`, `/opt`, `/usr/local`

Generates `community.docker.docker_compose_v2` tasks. With `--export-compose`, compose and referenced env files are copied into the output folder and playbook tasks point to that exported project source.

### Host Configuration & State

Captures users, groups, cron entries, SSH daemon settings, firewall rule output, mount information, and selected sysctl keys. Where exact cross-platform idempotent automation is not guaranteed, data is still included for operator review.

---

## Generated Output

Two files written to the output directory:

| File | Description |
|---|---|
| `<hostname>_playbook.yml` | The Ansible playbook |
| `inventory.ini` | Inventory file with the source host pre-configured for local execution |

### inventory.ini

```ini
[replibook]
myhost ansible_connection=local
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
    # ── Docker Containers ──
    # ── Docker Compose Deployments ──
```

---

## Applying the Playbook

### 1. Install Ansible on the target machine

```bash
pip install ansible
```

### 2. Install required collections

Depending on what your playbook contains:

```bash
# For Docker tasks
ansible-galaxy collection install community.docker

# For Homebrew tasks (macOS targets)
ansible-galaxy collection install community.general
```

### 3. Apply locally

```bash
ansible-playbook -i inventory.ini myhost_playbook.yml
```

### 4. Apply remotely

Edit `inventory.ini` and replace the local connection with SSH details:

```ini
[replibook]
192.168.1.50 ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/id_rsa
```

Then run from your workstation:

```bash
ansible-playbook -i inventory.ini myhost_playbook.yml
```

---

## Operational Boundaries

- Replibook does not guarantee a byte-for-byte clone of a machine. It creates a practical Ansible starting point from installed packages, services, host config/state, Docker containers and Compose deployments.
- Secret-like Docker env values are redacted by default; verify generated output before sharing.
- Some captured host state sections are emitted for manual review because exact cross-OS automation differs by environment.

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
