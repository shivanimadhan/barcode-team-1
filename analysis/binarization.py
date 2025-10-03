import os
from dataclasses import dataclass
from typing import Tuple, List, Optional
from itertools import pairwise
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numpy.fft import fft2,ifft2,fftshift
from scipy import ndimage
from skimage import io, color, filters, measure, morphology
from skimage.measure import label, regionprops
from utils import groupAvg, average_largest, find_analysis_frames, vprint, radial_average, flatten
from utils.setup import setup_csv_writer
from utils.binarization import invert_frame, binarize
from core import BinarizationConfig, ReaderConfig, WriterConfig, BinarizationResults

def check_span(frame: np.ndarray):
    def check_connected(frame: np.ndarray, axis: int = 0):
        # Ensures that either connected across left-right or up-down axis
        if not axis in [0, 1]:
            raise Exception("Axis must be 0 or 1.")
    
        struct = ndimage.generate_binary_structure(2, 2)
        frame_connections, _ = ndimage.label(input=frame, structure=struct)
    
        if axis == 0:
            labeled_first = np.unique(frame_connections[0,:])
            labeled_last = np.unique(frame_connections[-1,:])
        if axis == 1:
            labeled_first = np.unique(frame_connections[:,0])
            labeled_last = np.unique(frame_connections[:,-1])
    
        labeled_first = set(labeled_first[labeled_first != 0])
        labeled_last = set(labeled_last[labeled_last != 0])
        return 1 if labeled_first.intersection(labeled_last) else 0
    return (check_connected(frame, axis = 0) or check_connected(frame, axis = 1))

def find_largest_void(frame: np.ndarray):
    eval_frame = invert_frame(frame)
    labeled, a = label(eval_frame, connectivity= 2, return_num =True) # identify the regions of connectivity 2
    if a == 0 or not regionprops(labeled):
        return frame.shape[0] * frame.shape[1]    
    regions = regionprops(labeled) # determines the region properties of the labeled
    region_areas = sorted([r.area for r in regions], reverse = True)
    largest_void = region_areas[0]
    return largest_void # returns largest region(s) area

def find_island_properties(frame: np.ndarray):
    def get_island_distances(centroid1, centroid2):
        y1, x1 = centroid1
        y2, x2 = centroid2
        return np.sqrt((x1-x2)**2 + (y1-y2)**2)
    def get_anisotropy_factor(major_axis_length, minor_axis_length):
        if major_axis_length and minor_axis_length:
            return major_axis_length/minor_axis_length
        else:
            return np.nan
    labeled, a = label(frame, connectivity= 2, return_num =True)
    props = ["area", "axis_major_length", "axis_minor_length", "centroid"]
    if a == 0 or not regionprops(labeled):
        return
    regions = regionprops(labeled)
    region_areas = sorted([r.area for r in regions], reverse = True)
    total_island_area = sum(region_areas)
    mean_island_area = np.mean(region_areas)
    largest_island_area, second_largest_island_area = region_areas[:2]
    region_centroids = [r.centroid for r in regions]
    region_axis_major = [r.axis_major_length for r in regions]
    region_axis_minor = [r.axis_minor_length for r in regions]
    mean_island_distance = np.mean([get_island_distances(i, j) for (i,j) in pairwise(region_centroids)])
    mean_anisotropy = np.nanmean([get_anisotropy_factor(major, minor) for (major, minor) in zip(region_axis_major, region_axis_minor)])
    return largest_island_area, second_largest_island_area, total_island_area, mean_island_area, mean_island_distance, mean_anisotropy

def structural_image_autocorrelation(frame: np.ndarray):
    mean = np.mean(frame)
    stdev = np.std(frame)
    frame = (frame - mean)/stdev
    corr_image = np.real(fftshift(ifft2(fft2(frame)*np.conj(fft2(frame)))))/(frame.shape[0]*frame.shape[1])
    radial_avg = radial_average(corr_image)
    return corr_image, radial_avg

def calculate_mean_correlation_length(radial_avg_lst: np.ndarray, micron_pixel_ratio: float, binning_factor: float, save_rds) -> float:
    gravgse=np.zeros((radial_avg_lst.shape[1],3))
    xvalues = np.arange(radial_avg_lst.shape[1]) * micron_pixel_ratio * binning_factor
    mean_g_r = np.mean(radial_avg_lst, axis = 0)
    std_g_r = np.std(radial_avg_lst, axis = 0)
    gravgse[:,0] = xvalues[:]
    gravgse[:,1] = mean_g_r[:]
    gravgse[:,2] = std_g_r[:]
    correlation_length = flatten(xvalues[np.argwhere(mean_g_r > np.exp(-1))])[0] if np.argwhere(mean_g_r > np.exp(-1)).any() else xvalues[-1]
    return correlation_length, gravgse

def analyze_binarization(video: np.ndarray, name: str, bin_config: BinarizationConfig, in_config: ReaderConfig, out_config: WriterConfig) -> Tuple[Optional[plt.Figure], BinarizationResults]:
    vprint('Beginning Binarization Analysis')
    num_frames = len(video)
    frame_step = bin_config.frame_step
    threshold_offset = bin_config.threshold_offset
    frame_eval_percent = bin_config.percentage_frames_evaluated
    um_pixel_ratio = in_config.um_pixel_ratio
    binning_factor = 2
    
    frame_indices, frame_step = find_analysis_frames(video, frame_step)

    csvwriter, csvfile = None, None
    if out_config.save_rds:
        from visualization import write_binarization_rds
        filename = os.path.join(name, 'BinarizationData.csv')
        csvwriter, csvfile = setup_csv_writer(filename)
    if out_config.save_visualizations:
        from visualization import save_binarization_visualization
        from visualization import save_binarization_plots

        
    void_area_lst = []
    island_area_lst = []
    island_area_lst2 = []
    total_island_area_lst = []
    mean_island_area_lst = []
    mean_island_distance_lst = []
    mean_anisotropy_lst = []
    correlation_rad_avg_lst = []
    connected_lst = []

    correlation_max = int(video.shape[1]/2 * binning_factor)
    mid_point = frame_indices[int((len(frame_indices) - 1)/2)]
    save_spots = np.array([0, mid_point, frame_indices[-1]])

    for frame_idx in frame_indices:
        new_image = binarize(video[frame_idx], threshold_offset)
        new_frame = groupAvg(new_image, binning_factor, bin_mask = True)
        if frame_idx in save_spots and out_config.save_visualizations:
            save_binarization_visualization(video[frame_idx], new_frame, frame_idx, name)

        if out_config.save_rds:
            write_binarization_rds(csvwriter, new_frame, frame_idx)

        max_void_area = find_largest_void(new_frame)
        max_island_area, max_island_area2, total_island_area, mean_island_area, island_distance, anisotropy = find_island_properties(new_frame)
        _, rad_avg = structural_image_autocorrelation(new_frame)

        void_area_lst.append(max_void_area)
        island_area_lst.append(max_island_area)
        island_area_lst2.append(max_island_area2)
        total_island_area_lst.append(total_island_area)
        mean_island_area_lst.append(mean_island_area)
        mean_island_distance_lst.append(island_distance)
        mean_anisotropy_lst.append(anisotropy)
        connected_lst.append(check_span(new_frame))
        correlation_rad_avg_lst.append(rad_avg[:correlation_max])

    if csvfile:
        csvfile.close()
    
    correlation_rad_avg_lst = np.array(correlation_rad_avg_lst)
    correlation_length, g_r_list = calculate_mean_correlation_length(correlation_rad_avg_lst, um_pixel_ratio, binning_factor, out_config.save_rds)

    start_eval_index = int(np.ceil(len(void_area_lst)*frame_eval_percent))
    final_eval_index = len(void_area_lst) - start_eval_index

    void_size_initial = np.mean(void_area_lst[:start_eval_index])
    void_percent_gain_list = np.array(void_area_lst)/void_size_initial
    
    island_size_initial = np.mean(island_area_lst[:start_eval_index])
    island_size_initial2 = np.mean(island_area_lst2[:start_eval_index])
    island_percent_gain_list = np.array(island_area_lst)/island_size_initial

    fig = None
    if out_config.save_visualizations:
        fig = save_binarization_plots(void_percent_gain_list, island_percent_gain_list, num_frames, frame_step)

    img_dims = video[0].shape[0] * video[0].shape[1] / (binning_factor ** 2)
    
    max_void_percent_change = np.mean(void_area_lst[final_eval_index:])/void_size_initial
    void_size_initial = void_size_initial / img_dims
    max_void_size = average_largest(void_area_lst)/img_dims
    max_island_percent_change = np.mean(island_area_lst[final_eval_index:])/island_size_initial
    island_size_initial = island_size_initial / img_dims
    island_size_initial2 = island_size_initial2 / img_dims
    max_island_size = average_largest(island_area_lst)/img_dims    
    connectivity = len([connected for connected in connected_lst if connected == 1])/len(connected_lst)
    mean_island_area = np.mean(mean_island_area_lst)/img_dims
    island_anisotropy = np.mean(mean_anisotropy_lst)
    total_island_area = np.mean(total_island_area_lst)/img_dims
    mean_island_distance = np.mean(mean_island_distance_lst) * um_pixel_ratio
    results = BinarizationResults(
        spanning = connectivity, 
        max_island_size = max_island_size, 
        max_void_size = max_void_size,
        max_island_percent_change = max_island_percent_change, 
        max_void_percent_change = max_void_percent_change,
        island_size_initial=island_size_initial, 
        island_size_initial2=island_size_initial2,
        island_anisotropy=island_anisotropy,
        mean_island_size=mean_island_area,
        total_island_size=total_island_area, 
        mean_island_separation=mean_island_distance, 
        island_correlation_length=correlation_length
    )

    return fig, results