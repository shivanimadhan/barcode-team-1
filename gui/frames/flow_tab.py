import tkinter as tk
from tkinter import ttk

from gui.config import BarcodeConfigGUI

from .execution_tab import create_popup


def create_flow_frame(parent, config: BarcodeConfigGUI):
    """Create the optical flow settings tab"""
    frame = ttk.Frame(parent)

    # Access config variables directly
    co = config.optical_flow

    row_f = 0

    frame_step_label=tk.Label(frame, text="Frame Step (Minimum: 1 Frame):")
    frame_step_label.grid(row=row_f, column=0, sticky="w", padx=5, pady=5)

    flow_f_step_spin = ttk.Spinbox(
        frame, from_=1, to=1000, increment=1, textvariable=co.frame_step, width=7
    )
    flow_f_step_spin.grid(row=row_f, column=1, padx=5, pady=5)

    # Add info box
    create_popup(frame, "Change interval (in frames) between frames used to calculate optical flow field. Will affect speed of program, with larger intervals decreasing program runtime.", row_f, frame_step_label)

    row_f += 1

    win_size_label=tk.Label(frame, text="Window Size (Minimum: 1 Pixel):")
    win_size_label.grid(row=row_f, column=0, sticky="w", padx=5, pady=5)

    win_size_spin = ttk.Spinbox(
        frame, from_=1, to=1000, increment=1, textvariable=co.window_size, width=7
    )
    win_size_spin.grid(row=row_f, column=1, padx=5, pady=5)

    # Add info box
    create_popup(frame, "Define size of region around each pixel used to calculate optical flow field. Larger window sizes result in less noise, but blurrier motion fields. Smaller window sizes detect smaller movement within the material, but are more susceptible to random noise.", row_f, win_size_label)

    row_f += 1

    downsamp_label=tk.Label(frame, text="Downsample (Minimum: 1 Pixel):")
    downsamp_label.grid(row=row_f, column=0, sticky="w", padx=5, pady=5)

    downsample_spin = ttk.Spinbox(
        frame, from_=1, to=1000, increment=1, textvariable=co.downsample_factor, width=7
    )
    downsample_spin.grid(row=row_f, column=1, padx=5, pady=5)

    # Add info box
    create_popup(frame, "Control interval between pixels that flow field is sampled at. Increasing downsampling reduces noise (along with precision) and is recommended for large-scale movement of areas of material. Decreasing downsampling is recommended for movement of many smaller areas of material.", row_f, downsamp_label)

    row_f += 1

    nm_pix_label=tk.Label(frame, text="Nanometer to Pixel Ratio [1 nm – 1 mm]:")
    nm_pix_label.grid(row=row_f, column=0, sticky="w", padx=5, pady=5)
    nm_pixel_spin = ttk.Spinbox(
        frame,
        from_=1,
        to=10**6,
        increment=1,
        textvariable=co.nm_pixel_ratio,
        width=9,
    )
    nm_pixel_spin.grid(row=row_f, column=1, padx=5, pady=5)

    # Add info box
    create_popup(frame, "Set ratio of nanometers to pixels in image. Input known information about imaging conditions to set this value (should be automatic for .ND2 files).", row_f, nm_pix_label)

    row_f += 1

    exp_time_label = tk.Label(frame, text="Exposure Time [1–1000]:")
    exp_time_label.grid(row=row_f, column=0, sticky="w", padx=5, pady=5)

    frame_interval_spin = ttk.Spinbox(
        frame,
        from_=1,
        to=10**3,
        increment=1,
        textvariable=co.frame_interval_s,
        width=7,
    )
    frame_interval_spin.grid(row=row_f, column=1, padx=5, pady=5)

    # Add info box
    create_popup(frame, "Control interval (in seconds) between optical flow frames. Used to adjust optical flow output units from pixels/field to nanometers/second.", row_f, exp_time_label) 

    return frame
