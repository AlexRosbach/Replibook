# Changelog

All notable changes to Replibook are documented here.

---

## Unreleased

### Added
- Hardened Windows EXE build script validation so `scripts/build-windows.ps1` fails when `dist/Replibook.exe` is not created.
- Review preview and safety classification for generated playbook sections, including a `replibook-review.json` sidecar report.
- Optional section exclusion after scanning via interactive prompts or `--exclude-sections`.
- Scan snapshot export via `--save-snapshot` and `replibook diff` for drift comparison between two snapshots.
- Remote scan recipe command that prints an SSH/SCP workflow for collecting scan snapshots from another machine.
- Backup and migration hints for Docker, Compose, network and scheduled-task findings.

---

## [1.1.0] — 2026-05-19

### Added
- Startup wizard that asks whether to scan or apply when `replibook` is run without explicit command-line options.
- Network scanner for interface addresses, default gateway, DNS and NetworkManager connection details where available.
- System configuration scanner for hostname, timezone and locale.
- Scheduled task scanner for cron, `/etc/cron.*` and macOS launchd plist locations.
- Generated playbooks now include reviewed network and system configuration sections.
- Generated playbooks now include reviewed scheduled task sections, with cron recreation tasks disabled by default.
- Windows desktop app frontend with Replibook branding, shared generator backend, playbook apply support and a PowerShell build script for EXE packaging.
- Native Windows scanners for installed programs, services, network configuration and scheduled tasks.
- `replibook modules`, `replibook gui`, and `replibook scan --modules ...` for commander-friendly automation.

---

## [1.0.1] — 2026-05-19

### Added
- Guided scan wizard with per-module explanations instead of one dense multi-select list.
- Local/SSH target inventory configuration, including host/IP, inventory name, SSH user, port, key path and become override.
- `replibook apply` command that validates generated files, shows the selected playbook/inventory and then calls `ansible-playbook` after confirmation.
- `replibook apply --install-deps` support to install Ansible and common required collections when missing.
- Extra confirmation guard for network-sensitive playbooks, with `--confirm-network-changes` for non-interactive runs.

### Changed
- Interactive generation now asks for target inventory details before writing `inventory.ini`.
- Documentation now explicitly states that Replibook does not back up Docker volumes, bind-mounted files, databases, uploads or application data.

---

## [1.0.0] — 2026-05-18

### Added
- Cross-platform support: auto-detects **Linux** and **macOS**
- Interactive CLI with checkbox module selection (questionary + Rich)
- Package scanner
  - Linux: `apt-mark showmanual` / `dpkg-query` fallback
  - macOS: `brew list --installed-on-request` (formulas) + `brew list --cask` (apps)
- Service scanner
  - Linux: enabled + active `systemd` services
  - macOS: `brew services` managed services
- Docker scanner: containers, images, ports, volumes, env vars, restart policies via Docker SDK
- Deployment scanner: locates `docker-compose.yml` files
  - Linux roots: `/opt`, `/srv`, `/home`, `/root`, `/docker`, `/var/lib`
  - macOS roots: `/Users`, `/opt`, `/usr/local`
  - Skips noise directories (`.git`, `node_modules`, `venv`, `build`, `dist`, etc.)
- Ansible playbook generator with OS-aware Jinja2 template
  - Uses `ansible.builtin.apt`, `ansible.builtin.service`
  - Uses `community.general.homebrew`, `community.general.homebrew_cask`, `community.general.homebrew_services`
  - Uses `community.docker.docker_container`, `community.docker.docker_compose_v2`
  - `become: true` on Linux, `become: false` on macOS (Homebrew refuses root)
- Inventory file generation (`inventory.ini`)
- `--all` flag for non-interactive runs
- `--output` flag for custom output directory
- `--version` flag
- `replibook` console-script entry point via `pipx install`
