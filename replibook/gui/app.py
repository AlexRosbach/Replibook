from __future__ import annotations

import os
import platform
import shlex
import subprocess
import sys
import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path

try:
    import customtkinter as ctk
    from tkinter import BooleanVar, StringVar, filedialog, messagebox
except ImportError as exc:  # pragma: no cover - depends on host Python build
    raise SystemExit(
        "Replibook GUI requires Tkinter and CustomTkinter. Install the GUI dependencies "
        "or use the CLI with `replibook`."
    ) from exc

from replibook.apply import contains_network_sensitive_content
from replibook.generator.playbook import TargetConfig
from replibook.modules import module_labels
from replibook.profiles import DEFAULT_SCAN_PROFILE, SCAN_PROFILES, modules_for_profile, profile_choices
from replibook.review import save_snapshot, summarize_scan, write_review_report
from replibook.runtime import scan_selected_modules, write_generated_playbook
from replibook.utils import detect_os
from replibook.version import __version__


GITHUB_URL = "https://github.com/AlexRosbach/Replibook"
BUG_REPORT_URL = "https://github.com/AlexRosbach/Replibook/issues/new?template=bug_report.yml"


def _asset_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    for candidate in (
        base / "assets" / name,
        base / "replibook" / "assets" / name,
        Path(__file__).resolve().parents[1] / "assets" / name,
    ):
        if candidate.exists():
            return candidate
    return Path(__file__).resolve().parents[1] / "assets" / name


def _split_command(command: str) -> list[str]:
    return shlex.split(command, posix=(os.name != "nt"))


class ReplibookDesktop:
    def __init__(self) -> None:
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title(f"Replibook {__version__}")
        self.root.geometry("1180x780")
        self.root.minsize(980, 680)
        self.host_os = detect_os()
        self.module_vars: dict[str, BooleanVar] = {}
        self.profile_var = StringVar(value=DEFAULT_SCAN_PROFILE)
        self.profile_buttons: dict[str, ctk.CTkButton] = {}

        icon = _asset_path("replibook-icon.ico")
        if icon.exists() and platform.system() == "Windows":
            try:
                self.root.iconbitmap(str(icon))
            except Exception:
                pass

        self.output_dir = StringVar(value=str(Path.cwd() / "playbooks"))
        self.target_connection = StringVar(value="local")
        self.target_name = StringVar(value="replibook")
        self.target_host = StringVar()
        self.target_user = StringVar()
        self.target_port = StringVar(value="22")
        self.target_key = StringVar()
        self.target_become = BooleanVar(value=self.host_os == "linux")

        self.playbook_path = StringVar(value=str(Path.cwd() / "playbooks" / "myhost_playbook.yml"))
        self.inventory_path = StringVar(value=str(Path.cwd() / "playbooks" / "inventory.ini"))
        self.ansible_command = StringVar(value=self._default_ansible_command())
        self.apply_check = BooleanVar(value=True)
        self.confirm_network = BooleanVar(value=False)

        self._build_ui()

    def _default_ansible_command(self) -> str:
        if platform.system() == "Windows":
            return "wsl ansible-playbook"
        return "ansible-playbook"

    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self.root, width=280, corner_radius=0, fg_color="#111827")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(
            sidebar,
            text="Replibook",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(28, 4))
        ctk.CTkLabel(
            sidebar,
            text=f"v{__version__} - {self.host_os}",
            text_color="#9ca3af",
        ).grid(row=1, column=0, sticky="w", padx=24)

        ctk.CTkLabel(
            sidebar,
            text="Scan profiles",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#e5e7eb",
        ).grid(row=2, column=0, sticky="w", padx=24, pady=(26, 8))

        profiles_frame = ctk.CTkScrollableFrame(sidebar, fg_color="transparent", height=370)
        profiles_frame.grid(row=3, column=0, sticky="nsew", padx=16)
        for index, profile in enumerate(profile_choices()):
            button = ctk.CTkButton(
                profiles_frame,
                text=f"{profile.label}\n{profile.description}",
                anchor="w",
                justify="left",
                height=68,
                corner_radius=10,
                command=lambda key=profile.key: self._set_profile(key),
            )
            button.grid(row=index, column=0, sticky="ew", pady=5)
            profiles_frame.grid_columnconfigure(0, weight=1)
            self.profile_buttons[profile.key] = button

        ctk.CTkButton(sidebar, text="GitHub", command=lambda: webbrowser.open(GITHUB_URL)).grid(
            row=4, column=0, sticky="ew", padx=24, pady=(20, 8)
        )
        ctk.CTkButton(sidebar, text="Report a bug", fg_color="#374151", hover_color="#4b5563", command=lambda: webbrowser.open(BUG_REPORT_URL)).grid(
            row=5, column=0, sticky="ew", padx=24
        )

        content = ctk.CTkFrame(self.root, fg_color="#f8fafc", corner_radius=0)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Role-oriented Ansible reproduction",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#111827",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Choose a practical scan profile, review the findings, then generate a playbook.",
            text_color="#64748b",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        tabs = ctk.CTkTabview(content, corner_radius=12)
        tabs.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 24))
        self.create_tab = tabs.add("Create")
        self.apply_tab = tabs.add("Apply")
        self.log_tab = tabs.add("Log")
        self._build_create_tab()
        self._build_apply_tab()
        self._build_log_tab()
        self._set_profile(DEFAULT_SCAN_PROFILE)

    def _build_create_tab(self) -> None:
        tab = self.create_tab
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        profile_card = ctk.CTkFrame(tab, corner_radius=12, fg_color="#ffffff")
        profile_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(12, 10))
        profile_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(profile_card, text="Active profile", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 2)
        )
        self.active_profile_label = ctk.CTkLabel(profile_card, text="", text_color="#64748b", justify="left", anchor="w")
        self.active_profile_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 16))

        modules_card = ctk.CTkFrame(tab, corner_radius=12, fg_color="#ffffff")
        modules_card.grid(row=1, column=0, sticky="nsew", padx=(8, 10), pady=8)
        modules_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(modules_card, text="Scanner modules", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 8)
        )
        module_frame = ctk.CTkScrollableFrame(modules_card, fg_color="transparent")
        module_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        modules_card.grid_rowconfigure(1, weight=1)

        modules = module_labels(self.host_os if self.host_os in {"linux", "macos", "windows"} else "linux")
        for index, (key, (label, description, _)) in enumerate(modules.items()):
            var = BooleanVar(value=key in modules_for_profile(DEFAULT_SCAN_PROFILE, modules))
            self.module_vars[key] = var
            row = ctk.CTkFrame(module_frame, fg_color="#f8fafc", corner_radius=10)
            row.grid(row=index, column=0, sticky="ew", pady=5)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkCheckBox(row, text="", variable=var, width=26).grid(row=0, column=0, padx=(12, 4), pady=12)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(weight="bold"), anchor="w").grid(
                row=0, column=1, sticky="ew", padx=(0, 12), pady=(10, 0)
            )
            ctk.CTkLabel(row, text=description, text_color="#64748b", anchor="w", justify="left", wraplength=380).grid(
                row=1, column=1, sticky="ew", padx=(0, 12), pady=(0, 10)
            )
            module_frame.grid_columnconfigure(0, weight=1)

        settings_card = ctk.CTkFrame(tab, corner_radius=12, fg_color="#ffffff")
        settings_card.grid(row=1, column=1, sticky="nsew", padx=(10, 8), pady=8)
        settings_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(settings_card, text="Target and output", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(16, 10)
        )
        self._entry_row(settings_card, 1, "Output folder", self.output_dir, self._pick_output_dir)
        self._segmented_row(settings_card, 2, "Target", self.target_connection, ("local", "ssh"))
        self._entry_row(settings_card, 3, "Inventory name", self.target_name)
        self._entry_row(settings_card, 4, "SSH host/IP", self.target_host)
        self._entry_row(settings_card, 5, "SSH user", self.target_user)
        self._entry_row(settings_card, 6, "SSH port", self.target_port)
        self._entry_row(settings_card, 7, "SSH key", self.target_key, self._pick_target_key)
        ctk.CTkCheckBox(settings_card, text="Use sudo/become in generated playbook", variable=self.target_become).grid(
            row=8, column=1, sticky="w", padx=8, pady=(8, 16)
        )
        ctk.CTkButton(settings_card, text="Generate playbook", height=42, command=self.generate_playbook).grid(
            row=9, column=1, sticky="ew", padx=8, pady=(4, 18)
        )

    def _build_apply_tab(self) -> None:
        tab = self.apply_tab
        tab.grid_columnconfigure(0, weight=1)
        card = ctk.CTkFrame(tab, corner_radius=12, fg_color="#ffffff")
        card.grid(row=0, column=0, sticky="nsew", padx=8, pady=12)
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Apply generated playbook", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(18, 4)
        )
        ctk.CTkLabel(
            card,
            text="On Windows, use WSL or another Ansible-capable command.",
            text_color="#64748b",
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=18, pady=(0, 12))
        self._entry_row(card, 2, "Playbook", self.playbook_path, self._pick_playbook)
        self._entry_row(card, 3, "Inventory", self.inventory_path, self._pick_inventory)
        self._entry_row(card, 4, "Ansible command", self.ansible_command)
        ctk.CTkCheckBox(card, text="Dry-run first (--check)", variable=self.apply_check).grid(
            row=5, column=1, sticky="w", padx=8, pady=6
        )
        ctk.CTkCheckBox(card, text="Allow network-sensitive playbooks", variable=self.confirm_network).grid(
            row=6, column=1, sticky="w", padx=8, pady=6
        )
        ctk.CTkButton(card, text="Run Ansible", height=42, command=self.apply_playbook).grid(
            row=7, column=1, sticky="ew", padx=8, pady=(14, 18)
        )

    def _build_log_tab(self) -> None:
        self.log = ctk.CTkTextbox(self.log_tab, corner_radius=12, font=("Consolas", 11), wrap="word")
        self.log.grid(row=0, column=0, sticky="nsew", padx=8, pady=12)
        self.log_tab.grid_columnconfigure(0, weight=1)
        self.log_tab.grid_rowconfigure(0, weight=1)

    def _entry_row(
        self,
        frame: ctk.CTkFrame,
        row: int,
        label: str,
        value: StringVar,
        picker: Callable[[], None] | None = None,
    ) -> None:
        ctk.CTkLabel(frame, text=label, anchor="w").grid(row=row, column=0, sticky="w", padx=(18, 8), pady=7)
        ctk.CTkEntry(frame, textvariable=value).grid(row=row, column=1, sticky="ew", padx=8, pady=7)
        if picker:
            ctk.CTkButton(frame, text="Browse", width=92, command=picker).grid(row=row, column=2, sticky="e", padx=(8, 18), pady=7)

    def _segmented_row(self, frame: ctk.CTkFrame, row: int, label: str, value: StringVar, values: tuple[str, ...]) -> None:
        ctk.CTkLabel(frame, text=label, anchor="w").grid(row=row, column=0, sticky="w", padx=(18, 8), pady=7)
        ctk.CTkSegmentedButton(frame, values=list(values), variable=value).grid(row=row, column=1, sticky="ew", padx=8, pady=7)

    def _pick_output_dir(self) -> None:
        if selected := filedialog.askdirectory(initialdir=self.output_dir.get() or str(Path.cwd())):
            self.output_dir.set(selected)

    def _pick_target_key(self) -> None:
        if selected := filedialog.askopenfilename():
            self.target_key.set(selected)

    def _pick_playbook(self) -> None:
        if selected := filedialog.askopenfilename(filetypes=[("YAML", "*.yml *.yaml"), ("All files", "*.*")]):
            self.playbook_path.set(selected)

    def _pick_inventory(self) -> None:
        if selected := filedialog.askopenfilename(filetypes=[("Inventory", "*.ini"), ("All files", "*.*")]):
            self.inventory_path.set(selected)

    def _set_profile(self, key: str) -> None:
        self.profile_var.set(key)
        modules = module_labels(self.host_os if self.host_os in {"linux", "macos", "windows"} else "linux")
        selected = set(modules_for_profile(key, modules))
        for module_key, var in self.module_vars.items():
            var.set(module_key in selected)

        profile = SCAN_PROFILES[key]
        self.active_profile_label.configure(
            text=f"{profile.label}: {profile.description}\nModules: {', '.join(selected)}"
        )
        for profile_key, button in self.profile_buttons.items():
            if profile_key == key:
                button.configure(fg_color="#2563eb", hover_color="#1d4ed8")
            else:
                button.configure(fg_color="#1f2937", hover_color="#374151")

    def _target(self) -> TargetConfig:
        return self._target_from_values(
            self.target_connection.get(),
            self.target_name.get(),
            self.target_host.get(),
            self.target_user.get(),
            self.target_port.get(),
            self.target_key.get(),
        )

    def _target_from_values(
        self,
        connection: str,
        name: str,
        host: str,
        user: str,
        port: str,
        identity_file: str,
    ) -> TargetConfig:
        if connection == "ssh":
            return TargetConfig(
                name=name.strip() or "target",
                connection="ssh",
                host=host.strip(),
                user=user.strip() or None,
                port=int(port.strip() or "22"),
                identity_file=identity_file.strip() or None,
            )
        return TargetConfig(name=name.strip() or "localhost")

    def _append_log(self, message: str) -> None:
        self.log.insert("end", message + "\n")
        self.log.see("end")

    def generate_playbook(self) -> None:
        selected = [key for key, var in self.module_vars.items() if var.get()]
        if not selected:
            messagebox.showerror("Replibook", "Select at least one scanner module.")
            return
        output_dir_value = self.output_dir.get()
        target = self._target()
        use_become = self.target_become.get()

        def worker() -> None:
            try:
                self.root.after(0, self._append_log, "Generating playbook...")
                scan_results = scan_selected_modules(
                    selected,
                    on_progress=lambda msg: self.root.after(0, self._append_log, msg),
                )
                output_dir = Path(output_dir_value)
                snapshot_path = save_snapshot(scan_results, output_dir / "replibook-scan.json")
                review_path = write_review_report(scan_results, output_dir)
                preview_lines = [
                    f"{row['label']}: {row['count']} item(s), safety={row['safety']}"
                    for row in summarize_scan(scan_results)
                ]
                preview_text = "\n".join(preview_lines) or "No scanner results found."
                self.root.after(0, self._append_log, f"Scan snapshot written: {snapshot_path}")
                self.root.after(0, self._append_log, f"Review report written: {review_path}")
                decision = {"continue": False}
                event = threading.Event()

                def ask_review() -> None:
                    decision["continue"] = messagebox.askyesno(
                        "Replibook review preview",
                        preview_text + "\n\nGenerate playbook from this scan?",
                    )
                    event.set()

                self.root.after(0, ask_review)
                event.wait()
                if not decision["continue"]:
                    self.root.after(0, self._append_log, "Generation cancelled after review preview.")
                    return
                playbook, inventory = write_generated_playbook(
                    scan_results,
                    output_dir_value,
                    target=target,
                    use_become=use_become,
                )
                self.root.after(0, self.playbook_path.set, playbook)
                self.root.after(0, self.inventory_path.set, inventory)
                self.root.after(0, self._append_log, f"Playbook written: {playbook}")
                self.root.after(0, self._append_log, f"Inventory written: {inventory}")
                self.root.after(0, messagebox.showinfo, "Replibook", "Playbook and inventory generated.")
            except Exception as exc:
                self.root.after(0, self._append_log, f"Error: {exc}")
                self.root.after(0, messagebox.showerror, "Replibook", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def apply_playbook(self) -> None:
        playbook = Path(self.playbook_path.get())
        inventory = Path(self.inventory_path.get())
        if not playbook.exists() or not inventory.exists():
            messagebox.showerror("Replibook", "Playbook and inventory must exist.")
            return
        if contains_network_sensitive_content(playbook) and not self.confirm_network.get():
            messagebox.showerror("Replibook", "Network-sensitive playbook detected. Enable the network confirmation first.")
            return
        if not messagebox.askyesno("Replibook", "Run Ansible with the selected files?"):
            return
        ansible_command = self.ansible_command.get()
        apply_check = self.apply_check.get()

        def worker() -> None:
            try:
                command = _split_command(ansible_command) + ["-i", str(inventory), str(playbook)]
                if apply_check:
                    command.append("--check")
                self.root.after(0, self._append_log, "Running: " + " ".join(command))
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                assert process.stdout is not None
                for line in process.stdout:
                    self.root.after(0, self._append_log, line.rstrip())
                code = process.wait()
                self.root.after(0, self._append_log, f"Ansible exited with code {code}")
                if code == 0:
                    self.root.after(0, messagebox.showinfo, "Replibook", "Ansible finished successfully.")
                else:
                    self.root.after(0, messagebox.showerror, "Replibook", f"Ansible exited with code {code}.")
            except Exception as exc:
                self.root.after(0, self._append_log, f"Error: {exc}")
                self.root.after(0, messagebox.showerror, "Replibook", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    ReplibookDesktop().run()


if __name__ == "__main__":
    main()
