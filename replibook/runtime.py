from collections.abc import Callable

from replibook.generator.playbook import PlaybookGenerator, TargetConfig
from replibook.modules import module_labels
from replibook.review import write_review_report
from replibook.utils import detect_os

ProgressCallback = Callable[[str], None]


def scan_selected_modules(selected_keys: list[str], on_progress: ProgressCallback | None = None) -> dict:
    """Run selected scanner modules and return the raw generator input."""
    host_os = detect_os()
    modules = module_labels(host_os)
    scan_results: dict = {}

    for key in selected_keys:
        if key not in modules:
            raise ValueError(f"Unknown scanner module: {key}")
        label, _, scanner_class = modules[key]
        if on_progress:
            on_progress(f"Scanning {label}...")
        scan_results[key] = scanner_class().scan()

    return scan_results


def write_generated_playbook(
    scan_results: dict,
    output: str,
    target: TargetConfig | None = None,
    use_become: bool | None = None,
) -> tuple[str, str]:
    """Write playbook and inventory through the shared backend generator."""
    generator = PlaybookGenerator(scan_results, output, target=target, use_become=use_become)
    generator.review_report_path = str(write_review_report(scan_results, output))
    return generator.generate()
