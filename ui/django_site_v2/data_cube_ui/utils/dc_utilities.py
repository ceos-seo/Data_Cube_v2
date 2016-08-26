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
# Creation date: 2016-06-13
# Modified by: AHDS
# Last modified date:

import gdal, osr
import collections
import gc
import numpy as np
import xarray as xr
from datetime import datetime
import collections

import datacube

"""
General-use functions
"""

def create_cfmask_clean_mask(cfmask):
    """
    Description:
      Create a clean mask for clear land/water pixels,
      i.e. mask out shadow, snow, cloud, and no data
    -----
    Input:
      cfmask (xarray) - cf_mask from the ledaps products
    Output:
      clean_mask (boolean numpy array) - clear land/water mask
    """

    #########################
    # cfmask values:        #
    #   0 - clear           #
    #   1 - water           #
    #   2 - cloud shadow    #
    #   3 - snow            #
    #   4 - cloud           #
    #   255 - fill          #
    #########################

    clean_mask = np.reshape(np.in1d(cfmask.values.reshape(-1), [0, 1]),
                            cfmask.shape)
    return clean_mask

def get_spatial_ref(crs):
    """
    Description:
      Get the spatial reference of a given crs
    -----
    Input:
      crs (datacube.model.CRS) - Example: CRS('EPSG:4326')
    Output:
      ref (str) - spatial reference of given crs
    """

    crs_str = str(crs)
    epsg_code = int(crs_str.split(':')[1])
    ref = osr.SpatialReference()
    ref.ImportFromEPSG(epsg_code)
    return str(ref)

def save_to_geotiff(out_file, data_type, bands, geotransform, spatial_ref,
                    x_pixels=3712, y_pixels=3711, no_data=-9999):
    """
    Description:
      Save data in bands to a GeoTIFF
    -----
    Inputs:
      out_file (str) - name of output file
      data_type (gdal data type) - gdal.GDT_Int16, gdal.GDT_Float32, etc
      bands xarray dataset - xarray dataset containing only bands to output.
      geotransform (tuple) - (ul_lon, lon_dist, lon_rtn, ul_lat, lat_rtn, lat_dist)
      spatial_ref (str) - spatial reference of dataset's crs
    Optional Inputs:
      x_pixels (int) - num pixels in x direction
      y_pixels (int) - num pixels in y direction
      no_data (int/float) - no data value
    """
    data_vars = bands.data_vars
    driver = gdal.GetDriverByName('GTiff')
    raster = driver.Create(out_file, x_pixels, y_pixels, len(data_vars), data_type)
    raster.SetGeoTransform(geotransform)
    raster.SetProjection(spatial_ref)
    index = 1
    for key in data_vars:
        print(key)
        out_band = raster.GetRasterBand(index)
        out_band.SetNoDataValue(no_data)
        out_band.WriteArray(data_vars[key].values)
        out_band.FlushCache()
        index += 1
    raster.FlushCache()
    out_band = None
    raster = None
