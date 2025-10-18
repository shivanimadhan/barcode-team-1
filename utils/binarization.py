import numpy as np
from skimage.morphology import remove_small_holes, remove_small_objects
from utils import groupAvg

def invert_frame(arr):
    ones_arr = np.ones(shape = arr.shape)
    return ones_arr - arr

def binarize(frame: np.ndarray, offset_threshold: float, binning_factor: int):
    avg_intensity = np.mean(frame)
    threshold = avg_intensity * (1 + offset_threshold)
    frame = groupAvg(frame, binning_factor)
    new_frame = np.where(frame < threshold, 0, 1)
    new_frame = remove_small_objects(new_frame.astype(bool), 6, connectivity = 2)
    new_frame = remove_small_holes(new_frame, 6, connectivity=2).astype(int)
    return new_frame