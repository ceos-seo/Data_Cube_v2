
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

# datacube imports.
import datacube
from datacube.api import *

# basic stuff.
from collections import defaultdict
import time
from datetime import datetime
import json

# dc data comes out as xray arrays
import xarray as xr
import xarray.ufuncs

# gdal related stuff.
import gdal
from gdalconst import *

# np for arrays
import numpy as np

# Author: AHDS
# Creation date: 2016-06-23
# Modified by:
# Last modified date: 2016-08-05

class DataAccessApi:
    """
    Class that provides wrapper functionality for the DataCube.
    """

    dc = None
    api = None

    # defaults for all the required fields.
    product_default = 'ls7_ledaps'
    platform_default = 'LANDSAT_7'

    def __init__(self):
        # using both the datacube object and the api.
        # dc is useful for all data access, api is only really used for metadata
        # fetching.
        # hardcoded config location. could parameterize.
        #self.dc = datacube.Datacube(config='/home/localuser/Datacube/data_cube_ui/config/.datacube.conf')
        self.dc = datacube.Datacube()
        self.api = datacube.api.API(datacube=self.dc)

    """
    query params are defined in datacube.api.query
    """

    def get_dataset_by_extent(self, product, product_type=None, platform=None, time=None,
                              longitude=None, latitude=None, measurements=None, output_crs=None, resolution=None):
        """
        Gets and returns data based on lat/long bounding box inputs.
        All params are optional. Leaving one out will just query the dc without it, (eg leaving out
        lat/lng but giving product returns dataset containing entire product.)

        Args:
            product (string): The name of the product associated with the desired dataset.
            product_type (string): The type of product associated with the desired dataset.
            platform (string): The platform associated with the desired dataset.
            time (tuple): A tuple consisting of the start time and end time for the dataset.
            longitude (tuple): A tuple of floats specifying the min,max longitude bounds.
            latitude (tuple): A tuple of floats specifying the min,max latitutde bounds.
            measurements (list): A list of strings that represents all measurements.
            output_crs (string): Determines reprojection of the data before its returned
            resolution (tuple): A tuple of min,max ints to determine the resolution of the data.

        Returns:
            data (xarray): dataset with the desired data.
        """

        # there is probably a better way to do this but I'm not aware of it.
        query = {}
        if product_type is not None:
            query['product_type'] = product_type
        if platform is not None:
            query['platform'] = platform
        if time is not None:
            query['time'] = time
        if longitude is not None and latitude is not None:
            query['longitude'] = longitude
            query['latitude'] = latitude

        data = self.dc.load(product=product, measurements=measurements,
                       output_crs=output_crs, resolution=resolution, **query)
        # data = self.dc.load(product=product, product_type=product_type, platform=platform, time=time, longitude=longitude,
        # latitude=latitude, measurements=measurements, output_crs=output_crs,
        # resolution=resolution)
        return data


    def get_dataset_tiles(self, product, product_type=None, platform=None, time=None,
                              longitude=None, latitude=None, measurements=None, output_crs=None, resolution=None):
        """
        Gets and returns data based on lat/long bounding box inputs.
        All params are optional. Leaving one out will just query the dc without it, (eg leaving out
        lat/lng but giving product returns dataset containing entire product.)

        Args:
            product (string): The name of the product associated with the desired dataset.
            product_type (string): The type of product associated with the desired dataset.
            platform (string): The platform associated with the desired dataset.
            time (tuple): A tuple consisting of the start time and end time for the dataset.
            longitude (tuple): A tuple of floats specifying the min,max longitude bounds.
            latitude (tuple): A tuple of floats specifying the min,max latitutde bounds.
            measurements (list): A list of strings that represents all measurements.
            output_crs (string): Determines reprojection of the data before its returned
            resolution (tuple): A tuple of min,max ints to determine the resolution of the data.

        Returns:
            data (xarray): dataset with the desired data in tiled sections.
        """

        # there is probably a better way to do this but I'm not aware of it.
        query = {}
        if product_type is not None:
            query['product_type'] = product_type
        if platform is not None:
            query['platform'] = platform
        if time is not None:
            query['time'] = time
        if longitude is not None and latitude is not None:
            query['longitude'] = longitude
            query['latitude'] = latitude

        #set up the grid workflow
        gw = GridWorkflow(self.dc.index, product=product)

        #dict of tiles.
        request_tiles = gw.list_cells(product=product, measurements=measurements,
                       output_crs=output_crs, resolution=resolution, **query)

        """
        tile_def = defaultdict(dict)
        for cell, tiles in request_tiles.items():
            for time, tile in tiles.items():
                tile_def[cell, time]['request'] = tile

        keys = list(tile_def)

        data_tiles = {}
        for key in keys:
            tile = tile_def[key]['request']
            data_tiles[key[0]] = gw.load(key[0], tile)
        """
        #cells now return stacked xarrays of data.
        data_tiles = {}
        for tile_key in request_tiles:
            tile = request_tiles[tile_key]
            data_tiles[tile_key] = gw.load(tile, measurements=measurements)

        return data_tiles


    def get_scene_metadata(self, platform, product, longitude=None, latitude=None, crs=None, time=None):
        """
        Gets a descriptor based on a request.

        Args:
            platform (string): Platform for which data is requested
            product_type (string): Product type for which data is requested
            longitude (tuple): Tuple of min,max floats for longitude
            latitude (tuple): Tuple of min,max floats for latitutde
            crs (string): Describes the coordinate system of params lat and long
            time (tuple): Tuple of start and end datetimes for requested data

        Returns:
            scene_metadata (dict): Dictionary containing a variety of data that can later be
                                   accessed.
        """

        descriptor_request = {}
        if platform is not None:
            descriptor_request['platform'] = platform
        if longitude is not None and latitude is not None:
            dimensions = {}
            longitude_dict = {}
            latitude_dict = {}
            time_dict = {}
            longitude_dict['range'] = longitude
            latitude_dict['range'] = latitude
            if crs is not None:
                longitude_dict['crs'] = crs
                latitude_dict['crs'] = crs
            dimensions['longitude'] = longitude_dict
            dimensions['latitude'] = latitude_dict
            if time is not None:
                time_dict['range'] = time
                dimensions['time'] = time_dict
            descriptor_request['dimensions'] = dimensions

        descriptor = self.api.get_descriptor(descriptor_request=descriptor_request)
        scene_metadata = {}

        if product in descriptor and len(descriptor[product]['result_min']) > 2:
            scene_metadata['lat_extents'] = (descriptor[product]['result_min'][1], descriptor[product]['result_max'][1])
            scene_metadata['lon_extents'] = (descriptor[product]['result_min'][2], descriptor[product]['result_max'][2])
            scene_metadata['time_extents'] = (descriptor[product]['result_min'][0], descriptor[product]['result_max'][0])
            scene_metadata['tile_count'] = len(descriptor[product]['storage_units'])
            scene_metadata['scene_count'] = descriptor[product]['result_shape'][0]
            scene_metadata['pixel_count'] = descriptor[product]['result_shape'][1] * descriptor[product]['result_shape'][2]
            scene_metadata['storage_units'] = descriptor[product]['storage_units']
        else:
            scene_metadata = {'lat_extents': (0,0), 'lon_extents': (0,0), 'time_extents': (0,0), 'tile_count': 0, 'scene_count': 0, 'pixel_count': 0, 'storage_units': {}}

        return scene_metadata

    def list_acquisition_dates(self, platform, product, longitude=None, latitude=None, crs=None, time=None):
        """
        Get a list of all acquisition dates for a query.

        Args:
            platform (string): Platform for which data is requested
            product_type (string): Product type for which data is requested
            longitude (tuple): Tuple of min,max floats for longitude
            latitude (tuple): Tuple of min,max floats for latitutde
            crs (string): Describes the coordinate system of params lat and long
            time (tuple): Tuple of start and end datetimes for requested data

        Returns:
            times (list): Python list of dates that can be used to query the dc for single time
                          sliced data.
        """

        metadata = self.get_scene_metadata(platform, product, longitude=longitude, latitude=latitude, crs=crs, time=time)
        #gets a list of times, corrected for utc offset.
        # (unit[0] + unit[0].utcoffset()) if unit[0].utcoffset() else
        times = set([unit[0] for unit in metadata['storage_units'].keys()])
        return sorted(times)

    def get_datacube_metadata(self, platform, product):
        """
        Gets some details on the cube and its contents.

        Args:
	    platform (string): Desired platform for requested data.
	    product (string): Desired product for requested data.

        Returns:
            datacube_metadata (dict): a dict with multiple keys containing relevant metadata.
        """

        descriptor = self.api.get_descriptor({'platform': platform})
        datacube_metadata = {}
        if product in descriptor:
            datacube_metadata['lat_extents'] = (descriptor[product]['result_min'][1], descriptor[product]['result_max'][1])
            datacube_metadata['lon_extents'] = (descriptor[product]['result_min'][2], descriptor[product]['result_max'][2])
            datacube_metadata['time_extents'] = (descriptor[product]['result_min'][0], descriptor[product]['result_max'][0])
            datacube_metadata['tile_count'] = len(descriptor[product]['storage_units'])
            datacube_metadata['scene_count'] = descriptor[product]['result_shape'][0]
            datacube_metadata['pixel_count'] = descriptor[product]['result_shape'][1] * descriptor[product]['result_shape'][2]
        else:
            datacube_metadata = {'lat_extents': (0,0), 'lon_extents': (0,0), 'time_extents': (0,0), 'tile_count': 0, 'scene_count': 0, 'pixel_count': 0}

        return datacube_metadata
