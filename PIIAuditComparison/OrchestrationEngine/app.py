import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import sys
import subprocess

# ================================
# Path Setup
# ================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.dirname(SCRIPT_DIR)

sys.path.insert(0, os.path.join(MODULE_DIR, 'ComparisonEngine'))
sys.path.insert(0, os.path.join(MODULE_DIR, 'OutputEngine'))
sys.path.insert(0, os.path.join(MODULE_DIR, 'QualityEngine'))

from config       import OUTPUT_DIR
from compare      import compare_pii_audit
from report_excel import write_excel_report
from report_html  import write_html_report
import metrics as metrics_module

from datetime import datetime
import logging
from utils import get_logger

logger = get_logger(__name__)


# ================================
# UI Application
# ================================
class TDMDriftDetectionApp:

    def __init__(self, root):
        self.root      = root
        self.root.title("TDM Quality Framework — PII Audit Drift Detection")
        self.root.geometry("600x420")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f2f5")

        self.prev_file   = tk.StringVar()
        self.curr_file   = tk.StringVar()
        self.status_text = tk.StringVar(value="Select both audit files to begin")
        self.output_dir  = None

        self._build_ui()

        # Trace file variables — enable/disable run button
        self.prev_file.trace_add('write', self._check_files)
        self.curr_file.trace_add('write', self._check_files)

    def _build_ui(self):

        # Header
        header = tk.Frame(self.root, bg="#1a1a2e", height=60)
        header.pack(fill='x')
        header.pack_propagate(False)

        tk.Label(header, text="TDM Quality Framework",
                 font=("Segoe UI", 14, "bold"),
                 fg="white", bg="#1a1a2e").pack(side='left', padx=20, pady=10)

        tk.Label(header, text="PII Audit Drift Detection",
                 font=("Segoe UI", 10),
                 fg="#aab", bg="#1a1a2e").pack(side='left', padx=5, pady=10)

        # Main Frame
        main = tk.Frame(self.root, bg="#f0f2f5", padx=30, pady=20)
        main.pack(fill='both', expand=True)

        # Previous Audit
        tk.Label(main, text="Previous Audit File",
                 font=("Segoe UI", 10, "bold"),
                 fg="#333", bg="#f0f2f5").grid(row=0, column=0, sticky='w', pady=(0, 4))

        prev_frame = tk.Frame(main, bg="#f0f2f5")
        prev_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 16))

        self.prev_entry = tk.Entry(prev_frame, textvariable=self.prev_file,
                                   font=("Segoe UI", 10), fg="#555",
                                   relief='flat', bg="white",
                                   width=52, state='readonly')
        self.prev_entry.pack(side='left', ipady=6, padx=(0, 8))

        tk.Button(prev_frame, text="Browse",
                  font=("Segoe UI", 10),
                  bg="#2980b9", fg="white",
                  relief='flat', padx=12, pady=4,
                  cursor='hand2',
                  command=self._browse_prev).pack(side='left')

        # Current Audit
        tk.Label(main, text="Current Audit File",
                 font=("Segoe UI", 10, "bold"),
                 fg="#333", bg="#f0f2f5").grid(row=2, column=0, sticky='w', pady=(0, 4))

        curr_frame = tk.Frame(main, bg="#f0f2f5")
        curr_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(0, 24))

        self.curr_entry = tk.Entry(curr_frame, textvariable=self.curr_file,
                                   font=("Segoe UI", 10), fg="#555",
                                   relief='flat', bg="white",
                                   width=52, state='readonly')
        self.curr_entry.pack(side='left', ipady=6, padx=(0, 8))

        tk.Button(curr_frame, text="Browse",
                  font=("Segoe UI", 10),
                  bg="#2980b9", fg="white",
                  relief='flat', padx=12, pady=4,
                  cursor='hand2',
                  command=self._browse_curr).pack(side='left')

        # Separator
        ttk.Separator(main, orient='horizontal').grid(
            row=4, column=0, columnspan=2, sticky='ew', pady=(0, 20))

        # Run Button
        self.btn_run = tk.Button(main,
                                  text="▶   Run Drift Detection",
                                  font=("Segoe UI", 11, "bold"),
                                  bg="#27ae60", fg="white",
                                  relief='flat', padx=24, pady=10,
                                  cursor='hand2',
                                  state='disabled',
                                  command=self._run)
        self.btn_run.grid(row=5, column=0, sticky='w')

        # Open Output Button — hidden initially
        self.btn_output = tk.Button(main,
                                     text="📁   Open Output Folder",
                                     font=("Segoe UI", 10),
                                     bg="#2980b9", fg="white",
                                     relief='flat', padx=16, pady=10,
                                     cursor='hand2',
                                     command=self._open_output)
        # Not packed yet — shown only on success

        # Progress bar
        self.progress = ttk.Progressbar(main, mode='indeterminate', length=300)
        self.progress.grid(row=6, column=0, columnspan=2, sticky='w', pady=(16, 8))
        self.progress.grid_remove()

        # Status
        self.status_label = tk.Label(main,
                                      textvariable=self.status_text,
                                      font=("Segoe UI", 10),
                                      fg="#555", bg="#f0f2f5",
                                      wraplength=500,
                                      justify='left')
        self.status_label.grid(row=7, column=0, columnspan=2, sticky='w')

        main.grid_columnconfigure(0, weight=1)

    # ================================
    # File Browse
    # ================================
    def _browse_prev(self):
        file = filedialog.askopenfilename(
            title="Select Previous Audit File",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if file:
            self.prev_file.set(file)

    def _browse_curr(self):
        file = filedialog.askopenfilename(
            title="Select Current Audit File",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if file:
            self.curr_file.set(file)

    # ================================
    # Validation — Enable/Disable Run
    # ================================
    def _check_files(self, *args):
        prev = self.prev_file.get().strip()
        curr = self.curr_file.get().strip()

        if prev and curr:
            self.btn_run.config(state='normal', bg="#27ae60")
            self.status_text.set("Ready — click Run Drift Detection")
            self.status_label.config(fg="#27ae60")
        else:
            self.btn_run.config(state='disabled', bg="#bdc3c7")
            self.status_text.set("Select both audit files to begin")
            self.status_label.config(fg="#555")

    # ================================
    # Run Comparison
    # ================================
    def _run(self):
        prev = self.prev_file.get().strip()
        curr = self.curr_file.get().strip()

        # Validation
        if prev == curr:
            messagebox.showerror("Error",
                "Previous and current files are the same.\nPlease select two different files.")
            return

        # Hide output button
        self.btn_output.grid_remove()

        # Disable run button
        self.btn_run.config(state='disabled', bg="#bdc3c7")
        self.status_text.set("Running drift detection...")
        self.status_label.config(fg="#e67e22")

        # Show progress
        self.progress.grid()
        self.progress.start(10)

        # Run in thread — keep UI responsive
        threading.Thread(target=self._run_thread, args=(prev, curr)).start()

    def _run_thread(self, prev, curr):
        try:
            timestamp    = datetime.today().strftime('%Y%m%d_%H%M%S')
            output_excel = os.path.join(OUTPUT_DIR, f"PII_Audit_Drift_Detection_{timestamp}.xlsx")
            output_html  = os.path.join(OUTPUT_DIR, f"PII_Audit_Drift_Detection_{timestamp}.html")

            # Setup logging — add file handler directly (basicConfig only works once)
            log_file = os.path.join(OUTPUT_DIR, f"drift_detection_{timestamp}.log")
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s — %(levelname)s — %(name)s — %(message)s'
            ))
            root_logger = logging.getLogger()
            root_logger.addHandler(file_handler)
            root_logger.setLevel(logging.INFO)
            self.status_text.set("Running Drift Detection...")
            results, counts_dict = compare_pii_audit(prev, curr)
            metrics_module.set_counts(counts_dict)

            # Check if any sheets had errors — logged in compare.py
            had_errors = counts_dict.get('sheets_with_errors', 0) > 0
            self.status_text.set("Drift detected. Generating detailed reports for review...")
            write_excel_report(results, curr, output_excel)
            write_html_report(results, output_html)

            self.output_dir = OUTPUT_DIR

            # Remove file handler to avoid duplicates on next run
            root_logger.removeHandler(file_handler)
            file_handler.close()

            # Update UI on main thread
            self.root.after(0, self._on_success, len(results), had_errors)

        except FileNotFoundError as e:
            self.root.after(0, self._on_error, f"File not found: {e}")
        except ValueError as e:
            self.root.after(0, self._on_error, f"Validation error: {e}")
        except Exception as e:
            self.root.after(0, self._on_error, f"Error: {e}")

    def _on_success(self, total_changes, had_errors=False):
        self.progress.stop()
        self.progress.grid_remove()
        self.btn_run.config(state='normal', bg="#27ae60")

        if had_errors and total_changes == 0:
            self.status_text.set(
                "⚠️ Completed with errors — invalid file format. Check log file for details.")
            self.status_label.config(fg="#e67e22")
        elif total_changes > 0:
            self.status_text.set(
                f"✅ Done! {total_changes} changes detected. Reports saved to output folder.")
            self.status_label.config(fg="#27ae60")
        else:
            self.status_text.set("✅ No drift detected. No changes between audits.")
            self.status_label.config(fg="#27ae60")

        # Show output button — log file always available
        self.btn_output.grid(row=5, column=1, sticky='e', padx=(16, 0))

    def _on_error(self, message):
        self.progress.stop()
        self.progress.grid_remove()
        self.btn_run.config(state='normal', bg="#27ae60")
        self.status_text.set(f"❌ {message}")
        self.status_label.config(fg="#e74c3c")
        # Output button stays hidden
        self.btn_output.grid_remove()

    def _open_output(self):
        if self.output_dir and os.path.exists(self.output_dir):
            if sys.platform == 'win32':
                os.startfile(self.output_dir)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', self.output_dir])
            else:
                subprocess.Popen(['xdg-open', self.output_dir])


# ================================
# Run App
# ================================
if __name__ == "__main__":
    root = tk.Tk()
    app = TDMDriftDetectionApp(root)
    root.mainloop()
