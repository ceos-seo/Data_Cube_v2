# Copyright 2016 United States Government as represented by the Administrator 
# of the National Aeronautics and Space Administration. All Rights Reserved.
#
# Portion of this code is Copyright Geoscience Australia, Licensed under the 
# Apache License, Version 2.0 (the "License"); you may not use this file 
# except in compliance with the License. You may obtain a copy of the License 
# at
#
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# The CEOS 2 platform is licensed under the Apache License, Version 2.0 (the 
# "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at 
# http://www.apache.org/licenses/LICENSE-2.0. 
# 
# Unless required by applicable law or agreed to in writing, software 
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT 
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the 
# License for the specific language governing permissions and limitations 
# under the License.

# Author: KMF
# Creation date: 2016-06-14
# Modified by: AHDS
# Last modified date:

import gdal, osr
import collections
import gc
import numpy as np
import xarray as xr
from datetime import datetime
import collections
from collections import OrderedDict

import datacube
from . import dc_utilities as utilities

def create_mosaic_iterative(dataset_in, clean_mask=None, no_data=-9999, intermediate_product=None):
    """
    Description:
      Creates a most recent - oldest mosaic of the input dataset. If no clean mask is given,
      the 'cf_mask' variable must be included in the input dataset, as it will be used
      to create a clean mask
    -----
    Inputs:
      dataset_in (xarray.Dataset) - dataset retrieved from the Data Cube; should contain
        coordinates: time, latitude, longitude
        variables: variables to be mosaicked
        If user does not provide a clean_mask, dataset_in must also include the cf_mask
        variable
    Optional Inputs:
      clean_mask (nd numpy array with dtype boolean) - true for values user considers clean;
        if user does not provide a clean mask, one will be created using cfmask
      no_data (int/float) - no data pixel value; default: -9999
    Output:
      dataset_out (xarray.Dataset) - mosaicked data with
        coordinates: latitude, longitude
        variables: same as dataset_in
    """

    # Create clean_mask from cfmask if none given
    if clean_mask is None:
        cfmask = dataset_in.cf_mask
        clean_mask = utilities.create_cfmask_clean_mask(cfmask)
        dataset_in = dataset_in.drop('cf_mask')

    data_vars = dataset_in.data_vars # Dict object with key as the name of the variable
                                     # and each value as the DataArray of that variable

    mosaic = OrderedDict() # Dict to contain variable names as keys and numpy arrays containing
                # mosaicked data

    for key in data_vars:
        # Get raw data for current variable and mask the data
        data = data_vars[key].values
        masked = np.full(data.shape, no_data)
        masked[clean_mask] = data[clean_mask]
        if intermediate_product is None:
            out = np.full(masked.shape[1:], no_data)
        else:
            out = intermediate_product[key].values
        # Mosaic current variable (most recent - oldest)
        for index in reversed(range(len(clean_mask))):
            swap = np.reshape(np.in1d(out.reshape(-1), [no_data]),
                              out.shape)
            out[swap] = masked[index][swap]
            mosaic[key] = (['latitude', 'longitude'], out)

    latitude = dataset_in.latitude
    longitude = dataset_in.longitude

    dataset_out = xr.Dataset(mosaic,
                             coords={'latitude': latitude,
                                     'longitude': longitude})

    return dataset_out
