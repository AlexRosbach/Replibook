from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


SECTION_LABELS = {
    "system": "System Configuration",
    "packages": "Packages / Programs",
    "services": "Services",
    "scheduled_tasks": "Scheduled Tasks",
    "docker": "Docker Containers",
    "deployments": "Docker Compose Deployments",
    "network": "Network Configuration",
}

SECTION_SAFETY = {
    "system": ("medium", "Hostname/timezone changes may affect users or require a reboot."),
    "packages": ("high", "Package/program inventory is usually safe, but installers still need review."),
    "services": ("medium", "Service enable/start changes can affect availability."),
    "scheduled_tasks": ("review", "Scheduled tasks may contain user context, paths or credentials."),
    "docker": ("review", "Docker environment variables are kept verbatim and must be reviewed before sharing."),
    "deployments": ("review", "Compose paths and bind mounts require a data-backup plan before migration."),
    "network": ("danger", "Network changes can break remote access and are disabled by default."),
}


def to_serializable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_serializable(item) for key, item in asdict(value).items()}
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): to_serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_serializable(item) for item in value]
    return value


def section_count(scan_results: dict[str, Any], section: str) -> int:
    value = scan_results.get(section, [])
    return len(value) if isinstance(value, list) else 0


def summarize_scan(scan_results: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section, label in SECTION_LABELS.items():
        if section not in scan_results:
            continue
        safety, reason = SECTION_SAFETY[section]
        rows.append({
            "key": section,
            "label": label,
            "count": section_count(scan_results, section),
            "safety": safety,
            "reason": reason,
        })
    return rows


def backup_hints(scan_results: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    if scan_results.get("docker"):
        hints.append("Docker containers were found. Back up named volumes, bind-mounted directories, uploads and databases separately before applying the generated playbook.")
    if scan_results.get("deployments"):
        hints.append("Docker Compose deployments were found. Replibook records compose project paths, but it does not copy compose files, .env files or application data.")
    if scan_results.get("network"):
        hints.append("Network configuration was found. Test from console access or out-of-band access before enabling generated network tasks.")
    if scan_results.get("scheduled_tasks"):
        hints.append("Scheduled tasks were found. Review users, paths, shell environment and external dependencies before enabling recreation tasks.")
    return hints


def build_review_report(scan_results: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sections": summarize_scan(scan_results),
        "backup_hints": backup_hints(scan_results),
    }


def filter_scan_results(scan_results: dict[str, Any], excluded_sections: set[str]) -> dict[str, Any]:
    return {key: value for key, value in scan_results.items() if key not in excluded_sections}


def save_snapshot(scan_results: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(to_serializable(scan_results), indent=2, sort_keys=True), encoding="utf-8")
    return target


def load_snapshot(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_review_report(scan_results: dict[str, Any], output_dir: str | Path, filename: str = "replibook-review.json") -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / filename
    report_path.write_text(json.dumps(build_review_report(scan_results), indent=2, sort_keys=True), encoding="utf-8")
    return report_path


def _identity(item: Any) -> str:
    if not isinstance(item, dict):
        return json.dumps(item, sort_keys=True)
    for key in ("name", "directory", "hostname", "source"):
        if item.get(key):
            return str(item[key])
    return json.dumps(item, sort_keys=True)


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for section in sorted(set(before) | set(after)):
        before_items = before.get(section, [])
        after_items = after.get(section, [])
        if not isinstance(before_items, list) or not isinstance(after_items, list):
            continue
        before_map = {_identity(item): item for item in before_items}
        after_map = {_identity(item): item for item in after_items}
        added = sorted(set(after_map) - set(before_map))
        removed = sorted(set(before_map) - set(after_map))
        changed = sorted(key for key in set(before_map) & set(after_map) if before_map[key] != after_map[key])
        if added or removed or changed:
            result[section] = {"added": added, "removed": removed, "changed": changed}
    return result
