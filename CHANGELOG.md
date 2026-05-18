# Changelog

All notable changes to Replibook are documented here.

---

## [Unreleased]

### Added
- Linux package scanning support for `dnf`, `yum`, `zypper`, `rpm` and `pacman`
- Host configuration/state scanner (users, groups, cron, SSH settings, firewall output, mounts, selected sysctl)
- Docker env secret redaction by default and optional Vault placeholder generation (`--vault-env-prefix`)
- Optional compose/env export into output directory (`--export-compose`)
- Granular module selection flags (`--packages`, `--services`, `--docker`, `--deployments`, `--config`)
- Snapshot generation (`--snapshot`) and snapshot diff command (`replibook diff <old> <new>`)
- Optional service expansion flags (`--include-user-services`, `--include-launchd`)
- Initial unit-test suite (`unittest`) and GitHub Actions CI/release validation workflows

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
