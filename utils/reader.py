import builtins
import functools
import os
from itertools import pairwise
from typing import List, Optional
import pims

import imageio.v3 as iio
import nd2
import numpy as np

from core import (
    BarcodeConfig,
    ChannelResults,
    BinarizationResults,
    IntensityResults,
    FlowResults,
)
from utils.analysis import check_channel_dim
from utils import vprint


def read_file(
    file_path: str,
    count_list: list,
    accept_dim: bool = False,
    allow_large_files: bool = True,
) -> Optional[np.ndarray]:
    """Read a file or numpy array using pims and return its data if valid."""

    print = functools.partial(builtins.print, flush=True)

    print(f"File {count_list[0]} of {count_list[1]}")
    print(file_path)

    # Optionally check file size if it's a file (not a numpy array)
    if isinstance(file_path, str) and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        file_size_gb = file_size / (1024**3)
        if file_size_gb > 5 and not allow_large_files:
            print("File size is too large -- this program does not process files larger than 5 GB.")
            return None

    try:
        # If file_path is a string path, use pims.open
        if isinstance(file_path, str):
            sequence = pims.open(file_path)
        # If file_path is a numpy array, use NumpyReader
        elif isinstance(file_path, np.ndarray):
            sequence = pims.NumpyReader(file_path)
        else:
            print("Unsupported input type for file_path.")
            return None

        # Convert the sequence to a numpy array of frames
        frames = np.array([frame for frame in sequence])
    except Exception as e:
        print(f"Could not read file: {e}")
        return None

    if frames.size == 0 or np.all(frames == 0):
        print("Empty file: cannot process, skipping to next file...")
        return None

    # Dim check (keep your existing logic)
    if not accept_dim and check_channel_dim(frames[0]):
        print(file_path + " is too dim, skipping to next file...")
        return None

    count_list[0] += 1
    return frames

def read_csv_to_channel_results(filepath: str) -> List[ChannelResults]:
    """Read results from a CSV file into a list of ChannelResults."""

    def get_value(value_str: str) -> float:
        """Convert string to float, handling empty strings as NaN."""
        if value_str == "" or value_str.lower() == "nan":
            return np.nan
        try:
            return float(value_str)
        except ValueError:
            # If conversion fails, return NaN
            return np.nan

    expected_headers = ChannelResults.get_headers(just_metrics=False)

    import csv

    results = []
    with open(filepath, "r", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)

        assert (
            headers == expected_headers
        ), f"CSV headers {headers} do not match expected {expected_headers}"

        for row in reader:

            data = [get_value(value) for value in row]

            if np.isnan(data[0]) or np.isnan(data[1]):
                raise ValueError(f"Invalid channel or dim_channel_flag in row: {row}")

            results.append(
                ChannelResults(
                    channel=int(data[0]),
                    dim_channel_flag=int(data[1]),
                    binarization=BinarizationResults(
                        spanning=data[2],
                        max_island_size=data[3],
                        max_void_size=data[4],
                        avg_island_percent_change=data[5],
                        avg_void_percent_change=data[6],
                        island_size_initial=data[7],
                        island_size_initial2=data[8],
                    ),
                    intensity=IntensityResults(
                        max_kurtosis=data[9],
                        max_median_skew=data[10],
                        max_mode_skew=data[11],
                        kurtosis_diff=data[12],
                        median_skew_diff=data[13],
                        mode_skew_diff=data[14],
                    ),
                    flow=FlowResults(
                        mean_speed=data[15],
                        delta_speed=data[16],
                        mean_theta=data[17],
                        mean_sigma_theta=data[18],
                    ),
                )
            )

    return results


def extract_nd2_metadata(filepath: str, config: BarcodeConfig) -> None:
    """Extract metadata from ND2 file and update config object."""

    if not nd2.is_supported_file(filepath):
        return

    try:
        with nd2.ND2File(filepath) as ndfile:
            # Extract frame timing metadata
            times = ndfile.events(orient="list")["Time [s]"]
            frame_interval = np.array([y - x for x, y in pairwise(times)]).mean()

            # Extract spatial metadata
            nm_pix_ratio = 1000 / (ndfile.voxel_size()[0])

            # Update config with extracted metadata
            config.optical_flow.frame_interval_s = frame_interval
            config.optical_flow.nm_pixel_ratio = nm_pix_ratio

            vprint(
                f"Extracted ND2 metadata: frame_interval={frame_interval:.4f}s, nm_pixel_ratio={nm_pix_ratio:.2f}"
            )

    except Exception as e:
        vprint(f"Warning: Could not extract ND2 metadata: {e}")
