import os 
import cv2 as cv
import numpy as np
from numpy.fft import fft2,ifft2,fftshift
from utils import groupAvg, find_analysis_frames, vprint, radial_average, flatten
from utils.setup import setup_csv_writer
from core import OpticalFlowConfig, ReaderConfig, WriterConfig, FlowResults
from gui.config import OpticalFlowConfigGUI, ReaderConfigGUI

def velocity_correlation(flow_field):
    downU, downV, _, _ = flow_field
    corr_v_x = np.real(fftshift(ifft2(fft2(downU)*np.conj(fft2(downU)))))/(downU.shape[0]*downU.shape[1])
    corr_v_y = np.real(fftshift(ifft2(fft2(downV)*np.conj(fft2(downV)))))/(downV.shape[0]*downV.shape[1])
    corr_mag = np.sqrt(corr_v_x ** 2 + corr_v_y ** 2)
    radial_avg = radial_average(corr_mag)
    return corr_v_x, corr_v_y, radial_avg

def calculate_mean_correlation_length(radial_avg_lst: np.ndarray, micron_pixel_ratio: float, 
                                      binning_factor: float, out_config: WriterConfig, name: str = None) -> float:
    csvwriter, csvfile = None, None
    if out_config.save_rds:
        filename = os.path.join(name, 'VelocityCorrelation.csv')
        csvwriter, csvfile = setup_csv_writer(filename)
    
    if csvfile:
        csvfile.close()
    
    gravgse=np.zeros((radial_avg_lst.shape[1],3))
    xvalues = np.arange(radial_avg_lst.shape[1]) * micron_pixel_ratio * binning_factor
    mean_g_r = np.mean(radial_avg_lst, axis = 0)
    std_g_r = np.std(radial_avg_lst, axis = 0)
    gravgse[:,0] = xvalues[:]
    gravgse[:,1] = mean_g_r[:]
    gravgse[:,2] = std_g_r[:]
    correlation_length = flatten(xvalues[np.argwhere(mean_g_r > np.exp(-1))])[0] if np.argwhere(mean_g_r > np.exp(-1)).any() else xvalues[-1]
    return correlation_length, gravgse

def analyze_optical_flow(video: np.ndarray, name: str, flow_config: OpticalFlowConfig, 
                         in_config: ReaderConfig, out_config: WriterConfig) -> FlowResults:
    # Defines print to enable printing only if verbose setting set to True
    vprint('Beginning Optical Flow Analysis')
    frame_eval_percent = flow_config.percentage_frames_evaluated
    frame_stride = flow_config.frame_step
    win_size = flow_config.win_size
    downsample = flow_config.downsample
    exposure_time = in_config.exposure_time
    um_pix_ratio = in_config.um_pixel_ratio
    frame_indices, frame_stride = find_analysis_frames(video, frame_stride)
    correlation_max = int(video.shape[1]/(2 * downsample))
    flow_field_indices = [(frame_indices[i], frame_indices[i + 1]) for i in range(len(frame_indices) - 1)]
    num_frames_analysis = int(np.ceil(frame_eval_percent * len(flow_field_indices)))

    mid_point = flow_field_indices[int((len(flow_field_indices) - 1)/2)]
    visualization_flow_fields = [flow_field_indices[0], mid_point, flow_field_indices[-1]]

    vx_list = []
    vy_list = []
    velocity_correlations = []
    speeds = []

    # Prepares the intermediate file for saving if setting is turned on
    csvwriter, csvfile = None, None
    if out_config.save_rds:
        from visualization import write_flow_field_rds, write_correlation_rds
        filename = os.path.join(name, 'OpticalFlow.csv')
        filename_vcorr = os.path.join(name, 'VelocityCorrelation.csv')
        csvwriter, csvfile = setup_csv_writer(filename)
        vcorr_csvwriter, vcorr_file = setup_csv_writer(filename_vcorr)
    for frame_pair in flow_field_indices:
        start, stop = frame_pair
        flow = cv.calcOpticalFlowFarneback(video[start], video[stop], None, 0.5, 3, win_size, 3, 5, 1.2, 0)
        flow_reduced = groupAvg(flow, downsample)
        downU = flow_reduced[:,:,0]
        downV = flow_reduced[:,:,1]
        downU = np.flipud(downU)* 1/(exposure_time) * 1/(stop - start) * um_pix_ratio
        downV = -1 * np.flipud(downV)* 1/(exposure_time) * 1/(stop - start) * um_pix_ratio

        if out_config.save_rds:
            write_flow_field_rds(csvwriter, downU, downV, start, stop)
        
        speed = (downU ** 2 + downV ** 2) ** (1/2)
        direction = np.arctan2(downV, downU)
        flow_field = [downU, downV, direction, speed]
        v_x_corr, v_y_corr, v_rad_avg = velocity_correlation(flow_field)
        v_rad_avg = v_rad_avg[:correlation_max]
        xvalues = np.arange(len(v_rad_avg)) * um_pix_ratio * downsample
        correlation_length = flatten(xvalues[np.argwhere(v_rad_avg > np.exp(-1))])[0] if np.argwhere(v_rad_avg > np.exp(-1)).any() else xvalues[-1]
        if out_config.save_rds:
            write_correlation_rds(vcorr_csvwriter, frame_pair, xvalues, v_rad_avg)

        if (start, stop) in visualization_flow_fields and out_config.save_visualizations:
            from visualization import save_flow_field_visualization
            save_flow_field_visualization(flow_field, start, stop, name, downsample)
        
        # Conversion: px/interval * interval/frame * 1/(sec/frame) * um/px
        vx_list.append(np.mean(np.cos(direction)))
        vy_list.append(np.mean(np.sin(direction)))
        velocity_correlations.append(correlation_length)
        speeds.append(np.mean(speed))
        
    # Close the CSV intermediate file
    if csvfile:
        csvfile.close()
    if vcorr_file:
        vcorr_file.close()
    vx_list = np.array(vx_list)
    vy_list = np.array(vy_list)
    speeds = np.array(speeds)
    correlation_lengths = np.array(velocity_correlations)
    mean_correlation_length = np.mean(correlation_lengths)

    vector_lengths = np.sqrt(vx_list ** 2 + vy_list ** 2)
    sigma_thetas = np.sqrt(-2 * np.log(vector_lengths))

    theta = np.arctan2(np.nanmean(vy_list), np.nanmean(vx_list)) # Metric for average flow direction # "Mean Flow Direction"
    sigma_theta = np.nanmean(sigma_thetas) # Metric for st. dev of flow (-pi, pi) # "Flow Directional Spread"
    mean_speed = np.nanmean(speeds) # Metric for avg. speed (units of um/s) # Average speed
    delta_speed = np.nanmean(speeds[-num_frames_analysis:]) - np.nanmean(speeds[:num_frames_analysis]) # Metric for change in speed # "Speed Change"
    results = FlowResults(mean_speed = mean_speed, delta_speed = delta_speed, mean_theta = theta, 
                          mean_sigma_theta = sigma_theta, velocity_correlation_length = mean_correlation_length)
    return results

def calculate_optical_flow(video: np.ndarray, frame_pair: tuple[int, int], 
                           flow_config: OpticalFlowConfigGUI, in_config: ReaderConfigGUI):
    win_size = flow_config.win_size.get()
    downsample = flow_config.downsample.get()
    exposure_time = in_config.exposure_time.get()
    um_pix_ratio = in_config.um_pixel_ratio.get()
    start, stop = frame_pair
    flow = cv.calcOpticalFlowFarneback(video[start], video[stop], None, 0.5, 3, win_size, 3, 5, 1.2, 0)
    flow_reduced = groupAvg(flow, downsample)
    downU = flow_reduced[:,:,0]
    downV = flow_reduced[:,:,1]
    # Conversion: px/interval * interval/frame * 1/(sec/frame) * um/px
    downU = np.flipud(downU)* 1/(exposure_time) * 1/(stop - start) * um_pix_ratio
    downV = -1 * np.flipud(downV)* 1/(exposure_time) * 1/(stop - start) * um_pix_ratio
    
    speed = (downU ** 2 + downV ** 2) ** (1/2)
    direction = np.arctan2(downV, downU)
    flow_field = [downU, downV, direction, speed]
    return flow_field