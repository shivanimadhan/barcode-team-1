import tkinter as tk
from tkinter import ttk, filedialog

from gui.config import BarcodeConfigGUI, ComparisonConfigGUI
from core import ChannelResults

def create_comparison_frame(parent, config: BarcodeConfigGUI, 
    comparison_config: ComparisonConfigGUI):
    """Create the comparison plot generator tab"""
    frame = ttk.Frame(parent)

    cc = comparison_config

    metrics_list_str = [
        metric.value for metric in ChannelResults.get_metrics(just_metrics=True)
    ]

    row_bc = 0

    # CSV file chooser
    tk.Label(frame, text="Select CSV File:").grid(
        row=row_bc, column=0, sticky="w", padx=5, pady=5
    )
    csv_label = tk.Label(
        frame, text="No file selected", wraplength=200, justify="left"
    )
    csv_label.grid(row=row_bc, column=1, sticky="w", padx=5, pady=5)

    def browse_csv_file():
        chosen = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv")], title="Select a CSV file"
        )
        if chosen:
            cc.csv_location.set(chosen)

    tk.Button(frame, text="Browse CSV Files...", command=browse_csv_file).grid(
        row=row_bc, column=2, padx=5, pady=5)
    row_bc += 1

    # Metric 1 Selection
    tk.Label(frame, text="Metric 1:").grid(
        row=row_bc, column=0, sticky="w", padx=5, pady=5
    )
    sort_menu = ttk.OptionMenu(
        frame, cc.first_comparison_metric, metrics_list_str[0], *metrics_list_str  # default value  # all choices
    )
    sort_menu.grid(row=row_bc, column=1, sticky="w", padx=5, pady=5)
    row_bc += 1

    # Metric 2 Selection
    tk.Label(frame, text="Metric 2:").grid(
        row=row_bc, column=0, sticky="w", padx=5, pady=5
    )
    sort_menu = ttk.OptionMenu(
        frame, cc.second_comparison_metric, metrics_list_str[0], *metrics_list_str  # default value  # all choices
    )
    sort_menu.grid(row=row_bc, column=1, sticky="w", padx=5, pady=5)
    row_bc += 1

    def browse_save_csv():
        chosen = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")],
            initialfile=f"{cc.first_comparison_metric} vs {cc.second_comparison_metric}.csv",
            title="Save Comparison CSV As",
        )
        if chosen:
            cc.output_location.set(chosen)

    tk.Button(frame, text="Save As...", command=browse_save_csv).grid(
        row=row_bc, column=2, padx=5, pady=5)
    row_bc += 1
    return frame