import os
from typing import Tuple, TypeAlias

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.ticker as ticker

from analysis.optical_flow import calculate_optical_flow
from utils import find_analysis_frames

import tkinter as tk
from tkinter import ttk

from gui.config import BarcodeConfigGUI, InputConfigGUI, PreviewConfigGUI, ReaderConfigGUI
from core.config import BarcodeConfig
from utils.reader import load_flow_frames

# from .execution_tab import create_popup

FramePair: TypeAlias = Tuple[int, int]

from gui.config import BarcodeConfigGUI, PreviewConfigGUI, InputConfigGUI

def create_flow_frame(parent, config: BarcodeConfigGUI, preview_config: PreviewConfigGUI, 
                      input_config: InputConfigGUI, core_config: BarcodeConfig):
    """Create the optical flow settings tab"""
    frame = ttk.Frame(parent)

    # Access config variables directly
    co = config.optical_flow_parameters
    ci = input_config
    cp = preview_config
    cr = config.reader

    row_f = 0
    tk.Label(frame, text="Frame Step").grid(row=row_f, column=0, sticky="w", padx=5, pady=5)
    of_f_step_spin = ttk.Spinbox(
        frame, from_=1, to=1000,
        increment=1,
        textvariable=co.frame_step,
        width=7
    )
    of_f_step_spin.grid(row=row_f, column=1, padx=5, pady=5)
    row_f += 1

    tk.Label(frame, text="Optical Flow Window Size").grid(row=row_f, column=0, sticky="w", padx=5, pady=5)
    win_size_spin = ttk.Spinbox(
        frame, from_=1, to=1000,
        increment=1,
        textvariable=co.win_size,
        width=7
    )
    win_size_spin.grid(row=row_f, column=1, padx=5, pady=5)
    row_f += 1

    tk.Label(frame, text="Downsample/Binning Factor").grid(row=row_f, column=0, sticky="w", padx=5, pady=5)
    downsample_spin = ttk.Spinbox(
        frame, from_=1, to=1000,
        increment=1,
        textvariable=co.downsample,
        width=7
    )
    downsample_spin.grid(row=row_f, column=1, padx=5, pady=5)
    row_f += 1

    tk.Label(frame, text="Choose image from folder for preview:").grid(
        row=row_f, column=0, sticky="w", padx=5, pady=5
    )
    sample_file_combobox = ttk.Combobox(
        frame, textvariable=cp.sample_file, state="disabled", width=30
    )

    sample_file_combobox.grid(row=row_f, column=1, padx=5, pady=5)
    row_f += 1

    ## Optical Flow Live Preview ##
    preview_title = tk.Label(frame, text="Optical Flow Field Dynamic Preview")
    preview_title.grid(
        row=row_f, column=0, columnspan=2, padx=5, pady=(10, 2), sticky="w"
    )
    row_f += 1

    # Preview label
    tk.Label(frame, text="Optical Flow Field").grid(
        row=row_f, column=0, columnspan=2, padx=5, pady=5, sticky="n"
    )

    row_f += 1

    # Get background color for matplotlib figures
    root = parent.winfo_toplevel()
    bg_name = root.cget("bg")
    r, g, b = root.winfo_rgb(bg_name)
    bg_color = (r / 65535, g / 65535, b / 65535)

    # Optical flow field image figure
    fig_flow = Figure(figsize=(3, 3), facecolor=bg_color)
    ax_flow = fig_flow.add_subplot(111)
    ax_flow.set_facecolor(bg_color)
    ax_flow.axis("off")

    canvas_flow = FigureCanvasTkAgg(fig_flow, master=frame)
    canvas_flow.draw()
    canvas_flow.get_tk_widget().grid(
        row=row_f, column=0, columnspan=2, padx=0, pady=(10, 5)
    )

    fig_flow.tight_layout()


    # This is the label that exists when there is no file yet selected
    preview_label = tk.Label(
        frame,
        text="Upload file to see optical flow field preview.",
        compound="center",
    )
    preview_label.grid(row=row_f, column=0, columnspan=2, padx=5, pady=(10, 5))
    row_f += 1

    # Preview functionality
    all_data = {"frames": np.array([])}

    def update_preview(*args):
        frames = all_data["frames"]

        if frames is None:
            preview_label.grid()
            ax_flow.clear()
            ax_flow.set_facecolor(bg_color)
            ax_flow.axis("off")
            canvas_flow.draw()
            preview_label.config(
                image="", text="Upload file to see optical flow field preview."
            )
            return

        preview_label.grid_remove()

        opt_config = co.config
        first_pair = (0, opt_config.frame_step)

        def visualize_optical_flow(ax, fig, canvas, flow_output):
            downU, downV, directions, speed = flow_output
            
            ax.clear()
            ax.quiver(downU, downV, color="blue")
            ticks_adj = ticker.FuncFormatter(lambda x, pos: f"{x * opt_config.downsample:g}")
            ax.xaxis.set_major_formatter(ticks_adj)
            ax.yaxis.set_major_formatter(ticks_adj)
            ax.set_aspect(aspect=1, adjustable="box")
            fig_flow.tight_layout()
            canvas_flow.draw()


        try:
            flow_output = calculate_optical_flow(frames, first_pair, co, cr)
            visualize_optical_flow(ax_flow, fig_flow, canvas_flow, flow_output)
        except Exception as e:
            preview_label.grid()
            ax_flow.clear()
            ax_flow.set_facecolor(bg_color)
            ax_flow.axis("off")
            canvas_flow.draw()
            preview_label.config(
                image="", text=f"Error computing optical flow: {e}"
            )        

    def load_all_frames(*args):
        # access from outer closure or global
        if ci.mode.get() == "dir":
            dir_path = ci.dir_path.get()
            sample = cp.sample_file.get()
            if not dir_path or not sample:
                all_data["frames"] = []
                update_preview()
                return
            path = os.path.join(dir_path, sample)
        else:
            path = ci.file_path.get()

        if not path:
            all_data["frames"] = []
            update_preview()
            return

        try:
            if config.channels.parse_all_channels.get():
                channel = 0
            else:
                channel = config.channels.selected_channel.get()
            all_data["frames"] = load_flow_frames(path, channel)  # delegate to core logic
        except Exception as e:
            print(f"[Preview] couldn't load all frames: {e}")
            all_data["frames"] = []

        update_preview()

    def update_sample_file_options(*args):
        dir_path = ci.dir_path.get()
        if dir_path and os.path.isdir(dir_path):
            files = [
                os.path.join(dir, f).removeprefix(dir_path + os.path.sep)
                for dir, _, files in os.walk(dir_path)
                for f in files
                if f.lower().endswith((".tif", ".tiff", ".nd2"))
            ]
            sample_file_combobox["values"] = files
            sample_file_combobox.config(state="readonly")
            if files:
                cp.sample_file.set(files[0])
        else:
            sample_file_combobox.set("")
            sample_file_combobox["values"] = []
            sample_file_combobox.config(state="disabled")


    #Live preview setup
    #preview_title = tk.Label(frame, text="Dynamic preview of first frames optical flow:")
    #preview_title.grid(
    #   row=row_f, column=0, columnspan=2, padx=5, pady=(10, 2), sticky="w"
    #)
    row_f += 1

    # Wire up events
    ci.file_path.trace_add("write", load_all_frames)
    cp.sample_file.trace_add("write", load_all_frames)
    config.channels.selected_channel.trace_add("write", load_all_frames)
    config.channels.parse_all_channels.trace_add("write", load_all_frames)
    co.frame_step.trace_add("write", update_preview)
    co.win_size.trace_add("write", update_preview)
    co.downsample.trace_add("write", update_preview)
    cr.um_pixel_ratio.trace_add("write", update_preview)
    cr.exposure_time.trace_add("write", update_preview)
    ci.dir_path.trace_add("write", update_sample_file_options)

    tk.Label(frame, text="Fraction of Frames Evaluated (0.01–0.25)").grid(row=row_f, column=0, sticky="w", padx=5, pady=5)
    of_pf_eval_spin = ttk.Spinbox(
        frame, from_=0.01, to=0.25,
        increment=0.01,
        textvariable=co.percentage_frames_evaluated,
        format="%.2f",
        width=7
    )
    of_pf_eval_spin.grid(row=row_f, column=1, padx=5, pady=5)

    return frame