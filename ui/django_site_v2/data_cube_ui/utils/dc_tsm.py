import gc
import numpy as np
import xarray as xr
import scipy.ndimage.filters as conv

from . import dc_utilities as utilities
from datetime import datetime

####################################################
# ｜ ＴＳＭ ｜
####################################################
# 0.0001 for the scale of ls7 data.
def _tsmi(dataset):
    return (dataset.red.astype('float64') + dataset.green.astype('float64'))*0.0001 / 2


def tsm(dataset_in, clean_mask=None, no_data=0):
    # Create a clean mask from cfmask if the user does not provide one
    if clean_mask is None:
        cfmask = dataset_in.cf_mask
        clean_mask = utilities.create_cfmask_clean_mask(cfmask)

    tsm = 3983 * _tsmi(dataset_in)**1.6246
    tsm.values[np.invert(clean_mask)] = no_data # Contains data for clear pixels

    # Create xarray of data
    time = dataset_in.time
    latitude = dataset_in.latitude
    longitude = dataset_in.longitude
    dataset_out = xr.Dataset({'tsm': tsm},
                             coords={'time': time,
                                     'latitude': latitude,
                                     'longitude': longitude})
    return dataset_out

def mask_tsm(dataset_in, wofs):
    wofs_criteria = wofs.copy(deep=True).normalized_data.where(wofs.normalized_data > 0.8)
    wofs_criteria.values[wofs_criteria.values > 0] = 0
    kernel = np.array([[1,1,1],[1,1,1],[1,1,1]])

    mask = conv.convolve(wofs_criteria.values, kernel, mode ='constant')
    mask = mask.astype(np.float32)

    dataset_out = dataset_in.copy(deep=True)
    dataset_out.normalized_data.values += mask
    dataset_out.total_clean.values += mask
    dataset_out.normalized_data.values[np.isnan(dataset_out.normalized_data.values)] = 0
    dataset_out.total_clean.values[np.isnan(dataset_out.total_clean.values)] = 0

    return dataset_out
