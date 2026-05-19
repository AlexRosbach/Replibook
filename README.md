<div align="center">

# Replibook

**Scan a server. Generate an Ansible playbook. Reproduce it anywhere.**

[![Version](https://img.shields.io/badge/version-1.0.1-6366f1)](https://github.com/AlexRosbach/Replibook/releases/tag/v1.0.1)
[![Python](https://img.shields.io/badge/python-3.10%2B-0ea5e9)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-22c55e)](docs/documentation.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)

Replibook takes a snapshot of what's installed and running on your machine — packages, services, Docker containers, Compose deployments — and turns it into a ready-to-use Ansible playbook that recreates the same setup on another host.

Works on **Linux** (apt + systemd) and **macOS** (Homebrew). Auto-detects which one you're on.

</div>

> [!IMPORTANT]
> Generated playbooks can contain sensitive information, especially Docker environment variables and host-specific paths. Review generated output before committing, sharing, or applying it to another host.
>
> Replibook does **not** back up Docker volumes, bind-mounted files, databases, uploads, application data or arbitrary files. It generates reproduction tasks from discovered configuration metadata; handle data backups separately.

---

## Features

- Automatic OS detection for Linux and macOS
- System configuration scanning for hostname, timezone and locale
- Network configuration scanning for interfaces, addresses, gateway and DNS
- Scheduled task scanning for cron, `/etc/cron.*` and macOS launchd plist locations
- Package scanning for apt/dpkg and Homebrew
- Service scanning for systemd and Homebrew services
- Docker container scanning via the Docker SDK
- Docker Compose deployment discovery
- Ansible playbook and matching inventory generation
- Guided CLI with explained module prompts
- Local and SSH target inventory configuration
- Optional guided `apply` command for generated playbooks, including Ansible dependency setup

---

## Documentation

- [Knowledge Base / FAQ](docs/knowledgebase.md)
- [Extended documentation](docs/documentation.md)
- [Report a bug](../../issues/new?template=bug_report.yml)

Use the Knowledge Base for common setup problems and generated-playbook warnings. Use the extended documentation for installation, scanner details, output format, and troubleshooting.

---

## Quick Start

### 1. Install

```bash
pipx install git+https://github.com/AlexRosbach/Replibook.git@v1.0.1
```

> No `pipx`? Install it once: `brew install pipx` (macOS) or `apt install pipx` (Linux).
>
> To install a different release tag, replace `@v1.0.1` in the command above.
> To install the latest development version instead, omit the `@<tag>` suffix.

### 2. Run it

```bash
replibook
```

That's it. The interactive menu guides you through:
- Choosing whether you want to scan or apply an existing playbook
- Selecting what to scan, with a short explanation for each module
- Confirming where to save the playbook (default: `./playbooks`)
- Choosing whether the inventory should target the local machine or another host over SSH

You end up with two files:

```
playbooks/
├── myserver_playbook.yml   # The Ansible playbook
└── inventory.ini           # Matching inventory file
```

### 3. Apply it to another machine

Run the playbook from the machine where Replibook is installed:

```bash
replibook apply myserver_playbook.yml --inventory inventory.ini
```

If Ansible is missing, Replibook offers to install Ansible and the common collections it needs. You can also request that directly:

```bash
replibook apply myserver_playbook.yml --inventory inventory.ini --install-deps
```

Replibook shows the selected playbook and inventory before handing off to `ansible-playbook`. If a playbook appears to contain network settings, Replibook asks for an extra confirmation because a bad network change can break remote access.

---

## What gets scanned

Replibook detects your OS and picks the right tools automatically:

| Module | Linux | macOS |
|---|---|---|
| **System** | hostname, timezone, locale | hostname, timezone, locale |
| **Network** | `ip`, `resolvectl`, optional `nmcli` | `networksetup` |
| **Scheduled Tasks** | user crontab, `/etc/crontab`, `/etc/cron.d`, periodic cron directories | user crontab, LaunchAgents, LaunchDaemons |
| **Packages** | `apt-mark` / `dpkg` | `brew` formulas + casks |
| **Services** | `systemctl` (enabled + active) | `brew services` |
| **Docker** | Docker socket | Docker Desktop socket |
| **Compose** | `/opt`, `/srv`, `/home`, `/root`, `/docker` | `/Users`, `/opt`, `/usr/local` |

If a tool isn't present (e.g. no Docker, no Homebrew), that module just returns nothing — no errors.

Network tasks are generated conservatively. Replibook records the discovered configuration and emits disabled NetworkManager example tasks when enough information is available. Review and explicitly enable network tasks before applying them.
Scheduled tasks are also generated conservatively. Replibook records cron and launchd entries for review, and cron recreation tasks are disabled until you explicitly enable them.

---

## Common commands

```bash
# Interactive (default)
replibook

# Skip the menu, scan everything
replibook --all

# Custom output directory
replibook --all --output /opt/playbooks

# Generate an SSH inventory without the interactive wizard
replibook --all \
  --target-connection ssh \
  --target-host 192.168.1.50 \
  --target-user ubuntu \
  --target-key ~/.ssh/id_rsa

# Dry-run a generated playbook
replibook apply ./playbooks/myserver_playbook.yml --inventory ./playbooks/inventory.ini --check

# Apply and install missing Ansible dependencies if needed
replibook apply ./playbooks/myserver_playbook.yml --inventory ./playbooks/inventory.ini --install-deps

# Help
replibook --help
```

---

## Example Output

Interactive run:

```
╭─────────────────────────────────────────────────────╮
│  Replibook v1.0.1                                   │
│  Ansible Playbook Generator · detected: macos       │
╰─────────────────────────────────────────────────────╯

Scan modules

╭─ Installed Packages (Homebrew) ─────────────────────╮
│ Reads Homebrew formulas and casks installed on this │
│ Mac.                                                │
╰─────────────────────────────────────────────────────╯
? [ ] Include Installed Packages (Homebrew)? Yes

╭─ Homebrew Services ─────────────────────────────────╮
│ Reads services managed through brew services.       │
╰─────────────────────────────────────────────────────╯
? [ ] Include Homebrew Services? Yes

? Output directory for playbooks: ./playbooks
? Generate inventory for another host over SSH? No

  Scanning...
  → Installed Packages (Homebrew)
  → Homebrew Services
  → Docker Containers & Images
  → Docker Compose Deployments

  Installed Packages (Homebrew): 47 found
  Homebrew Services:              3 found
  Docker Containers & Images:     2 found
  Docker Compose Deployments:     1 found

  Generating playbook...

✓ Playbook written to: ./playbooks/mymac_playbook.yml
✓ Inventory written to: ./playbooks/inventory.ini
```

Generated playbook snippet (macOS):

```yaml
---
# Generated by Replibook on 2025-05-18 14:32:00
# Source host: mymac (macos)

- name: Replibook — Reproduce mymac
  hosts: replibook
  become: false
  tasks:

    # ── Homebrew Formulas ─────────────────────────────────────
    - name: Install Homebrew formulas
      community.general.homebrew:
        name:
          - git
          - htop
          - jq
        state: present
        update_homebrew: true

    # ── Homebrew Casks ────────────────────────────────────────
    - name: Install Homebrew casks
      community.general.homebrew_cask:
        name:
          - visual-studio-code
          - rectangle
        state: present

    # ── Docker Containers ──────────────────────────────────────
    - name: Run container my-app
      community.docker.docker_container:
        name: my-app
        image: nginx:latest
        state: started
        restart_policy: unless-stopped
```

---

## Permissions

| Platform | Sudo needed? |
|---|---|
| **Linux** | Only for Docker socket — either run with `sudo` or add yourself to the `docker` group |
| **macOS** | No — Homebrew refuses to run as root |

The package and service scanners don't need elevated privileges on either OS.

---

## Architecture

```
replibook/
├── scanner/          # Scanner modules (packages, services, docker, deployments)
├── generator/        # Playbook assembler + Jinja2 template
├── models/           # Data models
└── utils/            # OS detection
```

| Component | Responsibility |
|---|---|
| `main.py` | Typer CLI entry point |
| `cli.py` | Interactive menu, scan orchestration |
| `scanner/` | One module per scan domain — auto-detects Linux vs macOS |
| `generator/playbook.py` | Renders scan results into Ansible YAML via Jinja2 |
| `utils/os_detect.py` | Returns `linux` / `macos` |

**Dependencies:** Python 3.10+, Typer, Rich, questionary, Jinja2, docker-py

---

## Documentation

- [Knowledge Base / FAQ](docs/knowledgebase.md)
- [Extended documentation](docs/documentation.md)

---

## Contributing

Bug reports, feature requests and questions are welcome via [GitHub Issues](../../issues).
Please use the provided issue templates — blank issues are disabled.

Security vulnerabilities should be reported via [GitHub Security Advisories](../../security/advisories/new).

---

## License

MIT License — see [LICENSE](LICENSE) for details.
