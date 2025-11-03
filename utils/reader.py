import os, functools, builtins
from itertools import pairwise
import nd2
import imageio.v3 as iio
import numpy as np
from utils import vprint
from core import BarcodeConfig, ChannelResults, BinarizationResults, IntensityResults, FlowResults

def check_first_frame_dim(file):
    min_intensity = np.min(file[0])
    mean_intensity = np.mean(file[0])
    return 2 * np.exp(-1) * mean_intensity <= min_intensity

def read_file(filepath, count_list, config: BarcodeConfig = None, accept_dim: bool = False, allow_large_files = True, frames = None):
    print = functools.partial(builtins.print, flush=True)
    
    if count_list[1] != 1:    
        print(f'File {count_list[0]} of {count_list[1]}')
        print(filepath)
        count_list[0] += 1

    file_size = os.path.getsize(filepath)
    file_size_gb = file_size / (1024 ** 3)
    if file_size_gb > 5 and not allow_large_files:
        print("File size is too large -- this program does not process files larger than 5 GB.")
        return None

    if filepath.endswith(('.tif', '.tiff', 'avi', "mp4")):
        file = iio.imread(filepath)
        file = np.reshape(file, (file.shape + (1,))) if len(file.shape) == 3 else file
        if file.shape[3] != min(file.shape):
            file = np.swapaxes(np.swapaxes(file, 1, 2), 2, 3)
    elif filepath.endswith('.nd2'):
        with nd2.ND2File(filepath) as ndfile:
            if len(ndfile.sizes) >= 5:
                count_list[0] += 1
                raise TypeError("Incorrect file dimensions: file must be time series data with 1+ channels (4 dimensions total)")
            if "Z" in ndfile.sizes:
                count_list[0] += 1
                raise TypeError('Z-stack identified, skipping to next file...')
            if 'T' not in ndfile.sizes or len(ndfile.shape) <= 2 or ndfile.sizes['T'] <= 5:
                count_list[0] += 1
                raise TypeError('Too few frames, unable to capture dynamics, skipping to next file...')
            if ndfile == None:
                raise TypeError('Unable to read file, skipping to next file...')
            file = ndfile.asarray()
            file = np.swapaxes(np.swapaxes(file, 1, 2), 2, 3)
            try:
                times = ndfile.events(orient="list")["Time [s]"]
                frame_interval = np.array([y - x for x, y in pairwise(times)]).mean()
                micron_pix_ratio = 1/ndfile.voxel_size()[0]
                config.reader.exposure_time = frame_interval
                config.reader.um_pixel_ratio = micron_pix_ratio
                vprint(f"Extracted ND2 metadata: frame_interval={frame_interval:.4f}s, nm_pixel_ratio={micron_pix_ratio:.2f}")
            except Exception as e:
                vprint(f"Warning: Could not extract ND2 metadata: {e}")
    if (file == 0).all():
        print('Empty file: can not process, skipping to next file...')
        return None
    
    if accept_dim == False and check_first_frame_dim(file) == True:
        print(filepath + 'is too dim, skipping to next file...')
        return None
        
    if frames:
        return file[frames]
    else:
        return file

def load_binarization_frame(file_path, channel = 0):
    frame = read_file(file_path, count_list = (1, 1), frames = [0], accept_dim=True)
    return frame[0,:,:,channel]

def load_intensity_frames(file_path, channel = 0):
    file = read_file(file_path, count_list = (1, 1), frames = [0, -1], accept_dim=True)
    frame1 = file[0,:,:,channel]
    frame2 = file[-1,:,:,channel]
    return frame1, frame2, len(file)

def load_flow_frames(file_path, channel = 0):
    frames = read_file(file_path, count_list = (1, 1), accept_dim=True)
    return frames[:,:,:,channel]

def read_csv_to_channel_results(filepath: str) -> list[ChannelResults]:
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
    expected_physical_headers = ChannelResults.get_physical_headers(just_metrics=False)


    v1_header_length = 19 # Channel, Flags, 7 IB, 6 ID, 4 OF
    v2_header_length = 25 # Channel, Flags, 12 IB, 6 ID, 5 OF

    import csv

    results = []
    with open(filepath, "r", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)

        assert (
            (headers == expected_headers) or (headers == expected_physical_headers)
        ), f"CSV headers {headers} do not match expected {expected_headers} or {expected_physical_headers}"

        for row in reader:
            filename = row[0]
            data = [get_value(value) for value in row[1:]]
            if np.isnan(data[0]) or np.isnan(data[1]):
                raise ValueError(f"Invalid channel or dim_channel_flag in row: {row}")
            if len(data) == v1_header_length:
                results.append(
                    ChannelResults(
                        filepath = filename,
                        channel=int(data[0]),
                        dim_channel_flag=int(data[1]),
                        binarization=BinarizationResults(
                            connectivity=data[2],
                            max_island_size=data[3],
                            max_void_size=data[4],
                            max_island_percent_change=data[5],
                            max_void_percent_change=data[6],
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
            elif len(data) == v2_header_length:
                if headers == expected_headers:
                    results.append(ChannelResults(
                        filepath = filename,
                        channel = int(data[0]),
                        dim_channel_flag=int(data[1]),
                        binarization=BinarizationResults(
                            connectivity=data[2],
                            max_island_size=data[3],
                            max_void_size=data[4],
                            max_island_percent_change=data[5],
                            max_void_percent_change=data[6],
                            island_size_initial=data[7],
                            island_size_initial2=data[8],
                            island_anisotropy = data[9],
                            mean_island_size = data[10],
                            total_island_size = data[11],
                            mean_island_separation = data[12],
                            island_correlation_length = data[13],
                        ),
                        intensity=IntensityResults(
                            max_kurtosis=data[14],
                            max_median_skew=data[15],
                            max_mode_skew=data[16],
                            kurtosis_diff=data[17],
                            median_skew_diff=data[18],
                            mode_skew_diff=data[19],
                        ),
                        flow=FlowResults(
                            mean_speed=data[20],
                            delta_speed=data[21],
                            mean_theta=data[22],
                            mean_sigma_theta=data[23],
                            velocity_correlation_length=data[24]
                        )
                    ))
                elif headers == expected_physical_headers:
                    results.append(
                        ChannelResults(
                            filepath=filename,
                            channel=int(data[0]),
                            dim_channel_flag=int(data[1]),
                            binarization=BinarizationResults(
                                connectivity=data[2],
                                max_island_size_quantity=data[3],
                                max_void_size_quantity=data[4],
                                avg_island_percent_change=data[5],
                                avg_void_percent_change=data[6],
                                island_size_initial_quantity=data[7],
                                island_size_initial2_quantity=data[8],
                                island_anisotropy = data[9],
                                mean_island_size_quantity = data[10],
                                total_island_size_quantity = data[11],
                                mean_island_separation = data[12],
                                island_correlation_length = data[13],
                            ),
                            intensity=IntensityResults(
                                max_kurtosis=data[14],
                                max_median_skew=data[15],
                                max_mode_skew=data[16],
                                kurtosis_diff=data[17],
                                median_skew_diff=data[18],
                                mode_skew_diff=data[19],
                            ),
                            flow=FlowResults(
                                mean_speed=data[20],
                                delta_speed=data[21],
                                mean_theta=data[22],
                                mean_sigma_theta=data[23],
                                velocity_correlation_length=data[24],
                            ),
                        )
                    )
    return results