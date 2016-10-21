
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

# Author: KMF
# Creation date: 2016-06-14
# Modified by: AHDS
# Last modified date:

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

    #masks data with clean_mask. all values that are clean_mask==False are set to nodata.
    for key in list(dataset_in.data_vars):
        dataset_in[key].values[np.invert(clean_mask)] = no_data
    if intermediate_product is not None:
        dataset_out = intermediate_product.copy(deep=True)
    else:
        dataset_out = None
    for index in reversed(range(len(clean_mask))):
        dataset_slice = dataset_in.isel(time=index).astype("int16").drop('time')
        if dataset_out is None:
            dataset_out = dataset_slice.copy(deep=True)
            #clear out the params as they can't be written to nc.
            dataset_out.attrs = OrderedDict()
        else:
            for key in list(dataset_in.data_vars):
                dataset_out[key].values[dataset_out[key].values==-9999] = dataset_slice[key].values[dataset_out[key].values==-9999]
    return dataset_out

def create_median_mosaic(dataset_in, clean_mask=None, no_data=-9999, intermediate_product=None):
    """
	Description:
		Method for calculating the median pixel value for a given dataset.
	-----
	Input:
		dataset_in (xarray dataset) - the set of data with clouds and no data removed.
	Optional Inputs:
		no_data (int/float) - no data value.
	"""
    # Create clean_mask from cfmask if none given
    if clean_mask is None:
        cfmask = dataset_in.cf_mask
        clean_mask = utilities.create_cfmask_clean_mask(cfmask)
        dataset_in = dataset_in.drop('cf_mask')

    #required for np.nan
    dataset_in = dataset_in.astype("float64")

    for key in list(dataset_in.data_vars):
        dataset_in[key].values[np.invert(clean_mask)] = no_data

    dataset_out = dataset_in.isel(time=0).drop('time').copy(deep=True)
    dataset_out.attrs = OrderedDict()
    # Loop over every key.
    for key in list(dataset_in.data_vars):
        dataset_in[key].values[dataset_in[key].values==no_data] = np.nan
        dataset_out[key].values = np.nanmedian(dataset_in[key].values, axis=0)
        dataset_out[key].values[dataset_out[key].values==np.nan] = no_data

    return dataset_out.astype('int16')


def create_max_ndvi_mosaic(dataset_in, clean_mask=None, no_data=-9999, intermediate_product=None):
    """
	Description:
		Method for calculating the pixel value for the max ndvi value.
	-----
	Input:
		dataset_in (xarray dataset) - the set of data with clouds and no data removed.
	Optional Inputs:
		no_data (int/float) - no data value.
	"""
    # Create clean_mask from cfmask if none given
    if clean_mask is None:
        cfmask = dataset_in.cf_mask
        clean_mask = utilities.create_cfmask_clean_mask(cfmask)
        dataset_in = dataset_in.drop('cf_mask')

    for key in list(dataset_in.data_vars):
        dataset_in[key].values[np.invert(clean_mask)] = no_data

    if intermediate_product is not None:
        dataset_out = intermediate_product.copy(deep=True)
    else:
        dataset_out = None

    for timeslice in range(clean_mask.shape[0]):
        dataset_slice = dataset_in.isel(time=timeslice).astype("float64").drop('time')
        ndvi = (dataset_slice.nir - dataset_slice.red) / (dataset_slice.nir + dataset_slice.red)
        ndvi.values[np.invert(clean_mask)[timeslice,::]] = -1000000000
        dataset_slice['ndvi'] = ndvi
        if dataset_out is None:
            dataset_out = dataset_slice.copy(deep=True)
            #clear out the params as they can't be written to nc.
            dataset_out.attrs = OrderedDict()
        else:
            for key in list(dataset_slice.data_vars):
                dataset_out[key].values[dataset_slice.ndvi.values > dataset_out.ndvi.values] = dataset_slice[key].values[dataset_slice.ndvi.values > dataset_out.ndvi.values]
    return dataset_out

def create_min_ndvi_mosaic(dataset_in, clean_mask=None, no_data=-9999, intermediate_product=None):
    """
	Description:
		Method for calculating the pixel value for the min ndvi value.
	-----
	Input:
		dataset_in (xarray dataset) - the set of data with clouds and no data removed.
	Optional Inputs:
		no_data (int/float) - no data value.
	"""
    # Create clean_mask from cfmask if none given
    if clean_mask is None:
        cfmask = dataset_in.cf_mask
        clean_mask = utilities.create_cfmask_clean_mask(cfmask)
        dataset_in = dataset_in.drop('cf_mask')

    for key in list(dataset_in.data_vars):
        dataset_in[key].values[np.invert(clean_mask)] = no_data

    if intermediate_product is not None:
        dataset_out = intermediate_product.copy(deep=True)
    else:
        dataset_out = None

    for timeslice in range(clean_mask.shape[0]):
        dataset_slice = dataset_in.isel(time=timeslice).astype("float64").drop('time')
        ndvi = (dataset_slice.nir - dataset_slice.red) / (dataset_slice.nir + dataset_slice.red)
        ndvi.values[np.invert(clean_mask)[timeslice,::]] = 1000000000
        dataset_slice['ndvi'] = ndvi
        if dataset_out is None:
            dataset_out = dataset_slice.copy(deep=True)
            #clear out the params as they can't be written to nc.
            dataset_out.attrs = OrderedDict()
        else:
            for key in list(dataset_slice.data_vars):
                dataset_out[key].values[dataset_slice.ndvi.values < dataset_out.ndvi.values] = dataset_slice[key].values[dataset_slice.ndvi.values < dataset_out.ndvi.values]
    return dataset_out
