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

# Author: AHDS
# Creation date: 2016-06-23
# Modified by:
# Last modified date: 2016-08-05

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

class DataAccessApi:

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
        gets and returns data based on lat/long bounding box inputs.
        all params are optional. Leaving one out will just query the dc without it,
        eg leaving out lat/lng but giving product returns dataset containing entire product.
        params:
          product='ls7_ledaps_wgs84' -> from the ingestion config output type.
        ##########################################################################
        this can include any field in the dc.list_products() call, filtering by attributes. There are the most useful. Also
        included is instrument, format
          product_type='LEDAPS' -> from the dataset_type.metadata.product_type
          platform='LANDSAT_7' -> from the dataset_type and the ingestion metadata.
        ##########################################################################
          time=('1996-01-01', '2016-03-20') -> desired dates. Can probably be formatted in other ways.
          longitude=(34,7) -> desired longitude range. wgs84 coords
          latitude=(-1,1) -> desired latitude range. wgs84 coords.
          measurements=['red', 'green', 'blue'] -> band names derived from the ingestion config of the product.
          output_crs='EPSG:3577' -> used to reproject the data before its returned.
          resolution=(-25, 25) -> resolution of the reprojected data. first number is negative.
        others: We can specify a crs for the input extent bounds but the default is wgs84.
        returns: xarray dataset containing requested data.
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
        gets and returns data based on lat/long bounding box inputs.
        all params are optional. Leaving one out will just query the dc without it,
        eg leaving out lat/lng but giving product returns dataset containing entire product.
        params:
          product='ls7_ledaps_wgs84' -> from the ingestion config output type.
        ##########################################################################
        this can include any field in the dc.list_products() call, filtering by attributes. There are the most useful. Also
        included is instrument, format
          product_type='LEDAPS' -> from the dataset_type.metadata.product_type
          platform='LANDSAT_7' -> from the dataset_type and the ingestion metadata.
        ##########################################################################
          time=('1996-01-01', '2016-03-20') -> desired dates. Can probably be formatted in other ways.
          longitude=(34,7) -> desired longitude range. wgs84 coords
          latitude=(-1,1) -> desired latitude range. wgs84 coords.
          measurements=['red', 'green', 'blue'] -> band names derived from the ingestion config of the product.
          output_crs='EPSG:3577' -> used to reproject the data before its returned.
          resolution=(-25, 25) -> resolution of the reprojected data. first number is negative.
        others: We can specify a crs for the input extent bounds but the default is wgs84.
        returns: list of xarray datasets containing the requested data in tiled
        sections.
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
        gets a descriptor based on a request.
        params:
            platform='LANDSAT_7'
            product_type='LEDAPS'
            longitude=(34,37)
            latitude=(-1,0)
            crs='EPSG:4326' -> describes the coordinate system of params lat and long
            time=('1996-01-01', '2016-03-20')
        returns: descriptor dict of the request metadata including:
            product name
                dimensions:
                    x/long
                    y/lat
                    time
                variables
                    band name
                        data type
                        nodata val
                result min: (x, y, t)
                result max: (x, y, t)
                result shape: (x, y, t)
                storage units
                    (x, y, t):
                        min
                        max
                        shape
                        path
                .....
                ....
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
        params are the same as the scene metadata, as it uses the same frameworks.
        returns: python list of dates that can be used to query the dc for single time sliced data.
        """
        metadata = self.get_scene_metadata(platform, product, longitude=longitude, latitude=latitude, crs=crs, time=time)
        #gets a list of times, corrected for utc offset.
        # (unit[0] + unit[0].utcoffset()) if unit[0].utcoffset() else
        times = set([unit[0] for unit in metadata['storage_units'].keys()])
        return sorted(times)

    def get_datacube_metadata(self, platform, product):
        """
        gets some details on the cube and its contents.
        required params:
	    platform: "LANDSAT_7"
	    product: ls7_ledaps
        returns a dict with multiple keys containing relevant metadata.
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
