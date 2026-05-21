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
    from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox, ttk
except ImportError as exc:  # pragma: no cover - depends on host Python build
    raise SystemExit(
        "Replibook GUI requires Tkinter. Install the Tk package for your Python distribution "
        "(for example python3-tk on Debian/Ubuntu) or use the CLI with `replibook`."
    ) from exc

from replibook.apply import contains_network_sensitive_content
from replibook.generator.playbook import TargetConfig
from replibook.modules import module_labels
from replibook.profiles import DEFAULT_SCAN_PROFILE, SCAN_PROFILES, modules_for_profile, profile_choices
from replibook.review import save_snapshot, summarize_scan, write_review_report
from replibook.runtime import scan_selected_modules, write_generated_playbook
from replibook.utils import detect_os
from replibook.version import __version__


def _asset_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    candidate = base / "assets" / name
    if candidate.exists():
        return candidate
    return Path(__file__).resolve().parents[1] / "assets" / name


def _split_command(command: str) -> list[str]:
    return shlex.split(command, posix=(os.name != "nt"))


class ReplibookDesktop:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title(f"Replibook {__version__}")
        self.root.geometry("1040x760")
        self.root.minsize(900, 640)
        self.host_os = detect_os()
        self.module_vars: dict[str, BooleanVar] = {}
        self.profile_var = StringVar(value=DEFAULT_SCAN_PROFILE)

        icon = _asset_path("replibook-icon.png")
        if icon.exists():
            self._icon_image = self._load_icon(icon)
            if self._icon_image is not None:
                self.root.iconphoto(True, self._icon_image)

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

        self._configure_style()
        self._build_ui()

    def _load_icon(self, path: Path):
        try:
            from tkinter import PhotoImage

            return PhotoImage(file=str(path))
        except Exception:
            return None

    def _default_ansible_command(self) -> str:
        if platform.system() == "Windows":
            return "wsl ansible-playbook"
        return "ansible-playbook"

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self.root.configure(bg="#f6f7fb")
        default_font = ("Segoe UI", 10)
        style.configure(".", font=default_font)
        style.configure("TFrame", background="#f6f7fb")
        style.configure("Panel.TFrame", background="#ffffff", relief="flat")
        style.configure("Header.TFrame", background="#111827")
        style.configure("HeaderTitle.TLabel", background="#111827", foreground="#ffffff", font=("Segoe UI", 24, "bold"))
        style.configure("HeaderText.TLabel", background="#111827", foreground="#cbd5e1")
        style.configure("TLabel", background="#f6f7fb", foreground="#111827")
        style.configure("Panel.TLabel", background="#ffffff", foreground="#111827")
        style.configure("Hint.TLabel", background="#ffffff", foreground="#64748b")
        style.configure("TCheckbutton", background="#ffffff", foreground="#111827")
        style.configure("TRadiobutton", background="#ffffff", foreground="#111827")
        style.configure("TButton", padding=(11, 7))
        style.configure("Accent.TButton", background="#2563eb", foreground="#ffffff", padding=(13, 8))
        style.configure("Link.TButton", padding=(8, 5))
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(22, 18, 22, 14), style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=0)

        if getattr(self, "_icon_image", None) is not None:
            ttk.Label(header, image=self._icon_image).grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 14))
        ttk.Label(header, text="Replibook", style="HeaderTitle.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(
            header,
            text=f"Role-oriented Ansible reproduction · detected backend: {self.host_os}",
            style="HeaderText.TLabel",
        ).grid(row=1, column=1, sticky="w")
        support = ttk.Frame(header, style="Header.TFrame")
        support.grid(row=0, column=2, rowspan=2, sticky="e")
        ttk.Button(support, text="GitHub", style="Link.TButton", command=self._open_github).pack(side="left", padx=(0, 8))
        ttk.Button(support, text="Report a bug", style="Link.TButton", command=self._open_bug_report).pack(side="left")

        notebook = ttk.Notebook(self.root)
        notebook.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))
        notebook.add(self._scan_tab(notebook), text="Create")
        notebook.add(self._apply_tab(notebook), text="Apply")
        notebook.add(self._log_tab(notebook), text="Log")

    def _open_github(self) -> None:
        webbrowser.open("https://github.com/AlexRosbach/Replibook")

    def _open_bug_report(self) -> None:
        webbrowser.open("https://github.com/AlexRosbach/Replibook/issues/new?template=bug_report.yml")

    def _scan_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=18, style="Panel.TFrame")
        frame.columnconfigure(1, weight=1)
        modules = module_labels(self.host_os if self.host_os in {"linux", "macos", "windows"} else "linux")

        info = (
            "This platform is not fully supported for local scans yet. Replibook will still generate a starter inventory."
            if self.host_os == "unknown"
            else "Select scanner modules, target settings and output location, then generate the playbook and inventory."
        )
        ttk.Label(frame, text=info, wraplength=860, style="Panel.TLabel").grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        row = 1
        ttk.Label(frame, text="Scan profile", style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=3, padx=(0, 12))
        profile_box = ttk.Combobox(
            frame,
            textvariable=self.profile_var,
            values=[profile.key for profile in profile_choices()],
            state="readonly",
        )
        profile_box.grid(row=row, column=1, sticky="ew", pady=3)
        profile_box.bind("<<ComboboxSelected>>", lambda _event: self._apply_profile())
        ttk.Label(frame, text="Use Role reproduction for normal server/workstation rebuilds; Full audit is intentionally noisy.", style="Hint.TLabel").grid(
            row=row + 1, column=1, columnspan=2, sticky="ew", pady=(0, 8)
        )
        row += 2

        for key, (label, description, _) in modules.items():
            var = BooleanVar(value=key in modules_for_profile(DEFAULT_SCAN_PROFILE, modules))
            self.module_vars[key] = var
            ttk.Checkbutton(frame, text=label, variable=var).grid(row=row, column=0, sticky="nw", padx=(0, 12))
            ttk.Label(frame, text=description, wraplength=640, style="Panel.TLabel").grid(row=row, column=1, columnspan=2, sticky="ew")
            row += 1

        ttk.Separator(frame).grid(row=row, column=0, columnspan=3, sticky="ew", pady=12)
        row += 1
        self._entry_row(frame, row, "Output folder", self.output_dir, self._pick_output_dir)
        row += 1

        ttk.Label(frame, text="Target", style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=(10, 4))
        target_frame = ttk.Frame(frame, style="Panel.TFrame")
        target_frame.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(10, 4))
        ttk.Radiobutton(target_frame, text="Local", value="local", variable=self.target_connection).pack(side="left")
        ttk.Radiobutton(target_frame, text="SSH", value="ssh", variable=self.target_connection).pack(side="left", padx=(12, 0))
        row += 1

        self._entry_row(frame, row, "Inventory name", self.target_name)
        row += 1
        self._entry_row(frame, row, "SSH host/IP", self.target_host)
        row += 1
        self._entry_row(frame, row, "SSH user", self.target_user)
        row += 1
        self._entry_row(frame, row, "SSH port", self.target_port)
        row += 1
        self._entry_row(frame, row, "SSH key", self.target_key, self._pick_target_key)
        row += 1
        ttk.Checkbutton(frame, text="Use sudo/become in generated playbook", variable=self.target_become).grid(
            row=row, column=1, sticky="w", pady=(4, 10)
        )
        row += 1
        ttk.Button(frame, text="Generate", command=self.generate_playbook, style="Accent.TButton").grid(row=row, column=1, sticky="w")
        return frame

    def _apply_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=18, style="Panel.TFrame")
        frame.columnconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="Select a generated playbook and inventory. On Windows, use WSL or another Ansible-capable command.",
            wraplength=780,
            style="Panel.TLabel",
        ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        self._entry_row(frame, 1, "Playbook", self.playbook_path, self._pick_playbook)
        self._entry_row(frame, 2, "Inventory", self.inventory_path, self._pick_inventory)
        self._entry_row(frame, 3, "Ansible command", self.ansible_command)
        ttk.Checkbutton(frame, text="Dry-run first (--check)", variable=self.apply_check).grid(row=4, column=1, sticky="w")
        ttk.Checkbutton(frame, text="Allow network-sensitive playbooks", variable=self.confirm_network).grid(
            row=5, column=1, sticky="w"
        )
        ttk.Button(frame, text="Run Ansible", command=self.apply_playbook, style="Accent.TButton").grid(row=6, column=1, sticky="w", pady=(12, 0))
        return frame

    def _log_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=18, style="Panel.TFrame")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.log = ttk.Treeview(frame, columns=("message",), show="headings")
        self.log.heading("message", text="Message")
        self.log.grid(row=0, column=0, sticky="nsew")
        return frame

    def _entry_row(
        self,
        frame: ttk.Frame,
        row: int,
        label: str,
        value: StringVar,
        picker: Callable[[], None] | None = None,
    ) -> None:
        ttk.Label(frame, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=3, padx=(0, 12))
        ttk.Entry(frame, textvariable=value).grid(row=row, column=1, sticky="ew", pady=3)
        if picker:
            ttk.Button(frame, text="Browse", command=picker).grid(row=row, column=2, sticky="w", padx=(8, 0), pady=3)

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

    def _apply_profile(self) -> None:
        modules = module_labels(self.host_os if self.host_os in {"linux", "macos", "windows"} else "linux")
        selected = set(modules_for_profile(self.profile_var.get(), modules))
        for key, var in self.module_vars.items():
            var.set(key in selected)

    def _target(self) -> TargetConfig:
        if self.target_connection.get() == "ssh":
            return TargetConfig(
                name=self.target_name.get().strip() or "target",
                connection="ssh",
                host=self.target_host.get().strip(),
                user=self.target_user.get().strip() or None,
                port=int(self.target_port.get().strip() or "22"),
                identity_file=self.target_key.get().strip() or None,
            )
        return TargetConfig(name=self.target_name.get().strip() or "localhost")

    def _append_log(self, message: str) -> None:
        self.log.insert("", "end", values=(message,))
        self.log.yview_moveto(1)

    def generate_playbook(self) -> None:
        selected = [key for key, var in self.module_vars.items() if var.get()]
        if not selected and self.host_os != "unknown":
            messagebox.showerror("Replibook", "Select at least one scanner module.")
            return

        def worker() -> None:
            try:
                self.root.after(0, self._append_log, "Generating playbook...")
                scan_results = {}
                if self.host_os != "unknown":
                    scan_results = scan_selected_modules(
                        selected,
                        on_progress=lambda msg: self.root.after(0, self._append_log, msg),
                    )
                    output_dir = Path(self.output_dir.get())
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
                    self.output_dir.get(),
                    target=self._target(),
                    use_become=self.target_become.get(),
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

        def worker() -> None:
            try:
                command = _split_command(self.ansible_command.get()) + ["-i", str(inventory), str(playbook)]
                if self.apply_check.get():
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
