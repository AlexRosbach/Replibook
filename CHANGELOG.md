# Changelog

All notable changes to Replibook are documented here.

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
