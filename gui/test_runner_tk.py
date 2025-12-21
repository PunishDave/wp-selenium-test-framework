#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = PROJECT_ROOT / "tests"


def discover_test_files() -> list[str]:
    """
    Return a sorted list of test file paths (pytest-compatible), e.g.:
      tests/test_havewegot.py
      tests/test_meal_planner.py
    """
    if not TESTS_DIR.exists():
        return []

    files = sorted(TESTS_DIR.glob("test_*.py"))
    # Return relative paths for nicer display + pytest invocation
    return [str(f.relative_to(PROJECT_ROOT)) for f in files if f.is_file()]


class TestRunnerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WP Selenium Test Runner")
        self.geometry("980x640")
        self.minsize(900, 600)

        self.test_files: list[str] = []

        # vars
        self.headless_var = tk.BooleanVar(value=False)
        self.wp_user_var = tk.StringVar(value=os.environ.get("WP_ADMIN_USER", ""))
        self.wp_pass_var = tk.StringVar(value=os.environ.get("WP_ADMIN_PASS", ""))
        self.mp_pass_var = tk.StringVar(value=os.environ.get("MP_PASSWORD", ""))

        self._build_ui()
        self.refresh_tests()

    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        # Settings
        settings = ttk.LabelFrame(outer, text="Run Settings", padding=10)
        settings.pack(fill="x")

        settings.columnconfigure(1, weight=1)
        settings.columnconfigure(3, weight=1)

        ttk.Checkbutton(settings, text="Headless", variable=self.headless_var).grid(row=0, column=0, sticky="w")

        ttk.Label(settings, text="WP Admin User").grid(row=1, column=0, sticky="w", pady=(8, 2))
        ttk.Entry(settings, textvariable=self.wp_user_var).grid(row=1, column=1, sticky="ew", padx=(8, 16), pady=(8, 2))

        ttk.Label(settings, text="WP Admin Pass").grid(row=1, column=2, sticky="w", pady=(8, 2))
        ttk.Entry(settings, textvariable=self.wp_pass_var, show="•").grid(row=1, column=3, sticky="ew", pady=(8, 2))

        ttk.Label(settings, text="Meal Planner Password (optional)").grid(row=2, column=0, sticky="w", pady=(8, 2))
        ttk.Entry(settings, textvariable=self.mp_pass_var, show="•").grid(row=2, column=1, sticky="ew", padx=(8, 16), pady=(8, 2))

        ttk.Label(
            settings,
            text="Used only if the Meal Planner 'Save Week' prompt appears.",
            foreground="#666666",
        ).grid(row=2, column=2, columnspan=2, sticky="w", pady=(8, 2))

        # Test list + controls
        mid = ttk.Frame(outer)
        mid.pack(fill="both", expand=True, pady=(12, 0))
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(1, weight=1)

        header = ttk.Frame(mid)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Discovered test files").grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Refresh", command=self.refresh_tests).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(header, text="Select All", command=self.select_all).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(header, text="Select None", command=self.select_none).grid(row=0, column=3, padx=(8, 0))

        list_frame = ttk.Frame(mid)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(list_frame, selectmode="extended")
        self.listbox.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=sb.set)

        btns = ttk.Frame(mid)
        btns.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        btns.columnconfigure(0, weight=1)

        self.run_selected_btn = ttk.Button(btns, text="Run Selected", command=self.run_selected)
        self.run_selected_btn.grid(row=0, column=0, sticky="w")

        self.run_all_btn = ttk.Button(btns, text="Run All", command=self.run_all)
        self.run_all_btn.grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.stop_btn = ttk.Button(btns, text="Stop", command=self.stop_run, state="disabled")
        self.stop_btn.grid(row=0, column=2, sticky="w", padx=(8, 0))

        # Output
        out_frame = ttk.LabelFrame(outer, text="Output", padding=10)
        out_frame.pack(fill="both", expand=True, pady=(12, 0))
        out_frame.columnconfigure(0, weight=1)
        out_frame.rowconfigure(0, weight=1)

        self.output = tk.Text(out_frame, height=14, wrap="word")
        self.output.grid(row=0, column=0, sticky="nsew")

        out_sb = ttk.Scrollbar(out_frame, orient="vertical", command=self.output.yview)
        out_sb.grid(row=0, column=1, sticky="ns")
        self.output.configure(yscrollcommand=out_sb.set)

        self.proc: subprocess.Popen | None = None

    def log(self, text: str):
        self.output.insert("end", text)
        self.output.see("end")

    def refresh_tests(self):
        self.listbox.delete(0, "end")
        self.test_files = discover_test_files()
        if not self.test_files:
            self.listbox.insert("end", "(No test files found in ./tests)")
            return
        for f in self.test_files:
            self.listbox.insert("end", f)

    def select_all(self):
        if not self.test_files:
            return
        self.listbox.select_set(0, "end")

    def select_none(self):
        self.listbox.selection_clear(0, "end")

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()

        env["HEADLESS"] = "true" if self.headless_var.get() else "false"

        user = self.wp_user_var.get().strip()
        pw = self.wp_pass_var.get().strip()
        if user:
            env["WP_ADMIN_USER"] = user
        if pw:
            env["WP_ADMIN_PASS"] = pw

        mp = self.mp_pass_var.get().strip()
        if mp:
            env["MP_PASSWORD"] = mp
        else:
            env.pop("MP_PASSWORD", None)

        return env

    def _start_run(self, files: list[str] | None):
        if self.proc is not None:
            messagebox.showwarning("Already running", "A test run is already in progress.")
            return

        env = self._build_env()

        cmd = [sys.executable, "-m", "pytest", "-q"]
        if files:
            cmd.extend(files)

        self.output.delete("1.0", "end")
        self.log(f"$ {' '.join(cmd)}\n\n")

        self.run_selected_btn.configure(state="disabled")
        self.run_all_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        def worker():
            try:
                self.proc = subprocess.Popen(
                    cmd,
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                )
                assert self.proc.stdout is not None
                for line in self.proc.stdout:
                    self.output.after(0, self.log, line)
                rc = self.proc.wait()
                self.output.after(0, self.log, f"\n[exit code {rc}]\n")
            finally:
                self.proc = None
                self.output.after(0, lambda: self.run_selected_btn.configure(state="normal"))
                self.output.after(0, lambda: self.run_all_btn.configure(state="normal"))
                self.output.after(0, lambda: self.stop_btn.configure(state="disabled"))

        threading.Thread(target=worker, daemon=True).start()

    def run_selected(self):
        if not self.test_files:
            return
        sel = list(self.listbox.curselection())
        if not sel:
            messagebox.showinfo("No selection", "Select one or more test files, or click Run All.")
            return
        files = [self.listbox.get(i) for i in sel if self.listbox.get(i).startswith("tests/")]
        self._start_run(files)

    def run_all(self):
        self._start_run(None)

    def stop_run(self):
        if self.proc is None:
            return
        try:
            self.proc.terminate()
            self.log("\n[terminating...]\n")
        except Exception as e:
            self.log(f"\n[failed to terminate: {e}]\n")


if __name__ == "__main__":
    app = TestRunnerGUI()
    app.mainloop()
