# Replibook Knowledge Base

This page collects common setup issues, generated-playbook warnings, and operating notes.

## Generated playbooks may contain secrets

**Symptom**

The generated playbook includes Docker environment variables or paths that should not be public.

**Meaning**

Replibook reads Docker container metadata from the local Docker daemon. Docker stores environment variables in inspectable metadata, including values that may be secrets.

**Fix**

Before committing or sharing generated playbooks:

- Replace secret values with Ansible Vault variables.
- Remove one-off host-specific paths that should not be reproduced elsewhere.
- Review Docker volume mounts and port bindings.
- Keep generated output out of public repositories until reviewed.

## `command not found: replibook` after installation

Run:

```bash
pipx ensurepath
```

Then restart the shell. If installed with plain `pip`, make sure the Python user scripts directory is on `PATH`.

## Docker scanning returns no containers

Check whether Docker is installed and reachable from the current user:

```bash
docker ps
```

On Linux, either run Replibook with permissions to access the Docker socket or add the user to the `docker` group.

## Package scanner returns empty on macOS

Replibook only scans Homebrew-managed packages on macOS. Install Homebrew or accept that this module returns no packages.

## Package scanner returns empty on Linux

The first implementation supports apt/dpkg-based systems. RPM-based distributions such as Fedora, RHEL, Rocky, AlmaLinux and openSUSE are not supported yet.

## Generated playbook fails on another OS

Replibook generates OS-specific tasks. A playbook generated on Debian/Ubuntu targets apt/systemd semantics; a playbook generated on macOS targets Homebrew semantics. Generate and apply within matching operating-system families.

## Version tags

The repository uses semantic version tags. The initial public baseline is `v1.0.0`.

