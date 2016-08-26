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
# Modified by:
# Last modified date: 

import numpy as np
import xarray as xr

import datacube
import dc_utilities as utilities

# Command line tool imports
import argparse
import os
import collections
import gdal
from datetime import datetime

def create_mosaic(dataset_in, clean_mask=None, no_data=-9999):
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
    if not clean_mask:
        cfmask = dataset_in.cf_mask
        clean_mask = utilities.create_cfmask_clean_mask(cfmask)

    data_vars = dataset_in.data_vars # Dict object with key as the name of the variable
                                     # and each value as the DataArray of that variable

    mosaic = collections.OrderedDict() # Dict to contain variable names as keys and 
                                       # numpy arrays containing mosaicked data
    for key in data_vars:
        # Get raw data for current variable and mask the data
        data = data_vars[key].values
        masked = np.full(data.shape, no_data)
        masked[clean_mask] = data[clean_mask]
        out = np.full(masked.shape[1:], no_data)
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

def main(platform, product_type, min_lon, max_lon, min_lat, max_lat,
         red, green, blue, start_date, end_date, dc_config):
    """
    Description:
      Command-line mosaicking tool - creates a true color mosaic from the
        data retrieved by the Data Cube and save a GeoTIFF of the results
    Assumptions:
      The command-line tool assumes there is a measurement called cf_mask
    Inputs:
      platform (str)
      product_type (str)
      min_lon (str)
      max_lon (str)
      min_lat (str)
      max_lat (str)
      start_date (str)
      end_date (str)
      dc_config (str)
    """

    # Initialize data cube object
    dc = datacube.Datacube(config=dc_config,
                           app='dc-mosaicker')

    # Validate arguments
    products = dc.list_products()
    platform_names = set([product[6] for product in products.values])
    if platform not in platform_names:
        print 'ERROR: Invalid platform.'
        print 'Valid platforms are:'
        for name in platform_names:
            print name
        return

    product_names = [product[0] for product in products.values]
    if product_type not in product_names:
        print 'ERROR: Invalid product type.'
        print 'Valid product types are:'
        for name in product_names:
            print name
        return

    measurements = dc.list_measurements()
    index_1 = measurements.keys()[0] # Doesn't matter what the actual value is,
                                     # just need to get into the next layer of the
                                     # DataFrame.. better way?
    bands = set(measurements[index_1][product_type].keys())
    if not set([red, green, blue]).issubset(bands):
        print 'ERROR: Invalid product type.'
        print 'Valid product types are:'
        for band in bands:
            print band
        return

    try:
        min_lon = float(args.min_lon)
        max_lon = float(args.max_lon)
        min_lat = float(args.min_lat)
        max_lat = float(args.max_lat)
    except:
        print 'ERROR: Longitudes/Latitudes must be float values'
        return

    try:
        start_date_str = start_date
        end_date_str = end_date
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except:
        print 'ERROR: Invalid date format. Date format: YYYY-MM-DD'
        return

    if not os.path.exists(dc_config):
        print 'ERROR: Invalid file path for dc_config'
        return

    # Retrieve data from Data Cube
    dataset_in = dc.load(platform=platform,
                         product=product_type,
                         time=(start_date, end_date),
                         lon=(min_lon, max_lon),
                         lat=(min_lat, max_lat),
                         measurements=[red, green, blue, 'cf_mask'])

    # Get information needed for saving as GeoTIFF

    # Spatial ref
    crs = dataset_in.crs
    spatial_ref = utilities.get_spatial_ref(crs)

    # Upper left coordinates
    ul_lon = dataset_in.longitude.values[0]
    ul_lat = dataset_in.latitude.values[0]

    # Resolution
    products = dc.list_products()
    resolution = products.resolution[products.name == 'ls7_ledaps']
    lon_dist = resolution.values[0][1]
    lat_dist = resolution.values[0][0]

    # Rotation
    lon_rtn = 0
    lat_rtn = 0

    geotransform = (ul_lon, lon_dist, lon_rtn, ul_lat, lat_rtn, lat_dist)

    mosaic = create_mosaic(dataset_in)

    out_file = ( str(min_lon) + '_' + str(min_lat) + '_'
               + start_date_str + '_' + end_date_str
               + '_mosaic.tif' )

    utilities.save_to_geotiff(out_file, gdal.GDT_Float32, mosaic, geotransform, spatial_ref)

if __name__ == '__main__':

    start_time = datetime.now()

    parser = argparse.ArgumentParser()
    parser.add_argument('platform', help='Data platform; example: LANDSAT_7')
    parser.add_argument('product', help='Product type; example: ls7_ledaps')
    parser.add_argument('min_lon', help='Minimum longitude')
    parser.add_argument('max_lon', help='Maximum longitude')
    parser.add_argument('min_lat', help='Minimum latitude')
    parser.add_argument('max_lat', help='Maximum latitude')
    parser.add_argument('start_date', help='Start date; format: YYYY-MM-DD')
    parser.add_argument('end_date', help='End date; format: YYYY-MM-DD')
    parser.add_argument('red', nargs='?', default='red',
                        help='Band to map to the red color channel')
    parser.add_argument('green', nargs='?', default='green',
                        help='Band to map to the green color channel')
    parser.add_argument('blue', nargs='?', default='blue',
                        help='Band to map to the blue color channel')
    parser.add_argument('dc_config', nargs='?', default='~/.datacube.conf',
                        help='Datacube configuration path; default: ~/.datacube.conf')

    args = parser.parse_args()

    main(args.platform, args.product,
         args.min_lon, args.max_lon,
         args.min_lat, args.max_lat,
         args.red, args.green, args.blue,
         args.start_date, args.end_date,
         args.dc_config)

    end_time = datetime.now()
    print 'Execution time: ' + str(end_time - start_time)
