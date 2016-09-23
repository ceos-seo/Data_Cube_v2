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

# Django specific
from celery.decorators import task
from celery.signals import worker_process_init, worker_process_shutdown
from .models import Query, Result, ResultType, Metadata, AnimationType

import numpy as np
import xarray as xr
import collections
import gdal
import sys
import osr
import os
import datetime
from dateutil.tz import tzutc

from utils.data_access_api import DataAccessApi
from utils.dc_utilities import save_to_geotiff, create_cfmask_clean_mask, perform_timeseries_analysis_iterative
from utils.dc_water_classifier import wofs_classify

# Author: AHDS
# Creation date: 2016-06-23
# Modified by:
# Last modified date:

# constants up top for easy access/modification
# hardcoded colors input path..
color_path = ['~/Datacube/data_cube_ui/utils/au_water_percentage', '~/Datacube/data_cube_ui/utils/au_water_observations', '~/Datacube/data_cube_ui/utils/au_clear_observations']
acquisitions_per_iteration = 1
base_result_path = '/ui_results/water_detection/'


# Datacube instance to be initialized.
# A seperate DC instance is created for each worker.
dc = None

# Init/shutdown functions for handling dc instances.
# this is done to prevent synchronization/conflicts between workers when
# accessing DC resources.
@worker_process_init.connect
def init_worker(**kwargs):
    print("Creating DC instance for worker.")
    global dc
    dc = DataAccessApi()


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    print('Closing DC instance for worker.')
    global dc
    dc = None


# Creates metadata and result objects from a query id.
# gets the query, computes metadata for the parameters and saves the model.
# uses the metadata to query the datacube for relevant data and creates the result.
# results computed in single time slices for memory efficiency, pushed into a single numpy
# array containing the total result. this is then used to create png/tifs to populate a result model.
# result model is constantly updated with progress and checked for task
# cancellation.
@task(name="perform_water_analysis")
def perform_water_analysis(query_id, user_id):

    print("Starting for query:" + query_id)
    # its fair to assume that the query_id will exist at this point, as if it wasn't it wouldn't
    # start the task.
    queries = Query.objects.filter(query_id=query_id, user_id=user_id)
    # if there is a matching query other than the one we're using now then do nothing.
    # the ui section has already grabbed the result from the db.
    if queries.count() > 1:
        print("Repeat query, client will receive cached result.")
        if Result.objects.filter(query_id=query_id).count() > 0:
            queries.update(complete=True)
        return
    query = queries[0]
    print("Got the query, creating metadata.")

    result_type = ResultType.objects.get(
        satellite_id=query.platform, result_id=query.query_type)

    # do metadata before actually submitting the task.
    metadata = dc.get_scene_metadata(query.platform, query.product, time=(query.time_start, query.time_end), longitude=(
        query.longitude_min, query.longitude_max), latitude=(query.latitude_min, query.latitude_max))
    if not metadata:
        error_with_message(result, "There was an exception when handling this query.")
        return

    # this is x*y, could include time if we wanted.
    meta_pixel_count = metadata['pixel_count']
    meta_scene_count = metadata['scene_count']

    meta = Metadata(query_id=query.query_id, scene_count=meta_scene_count, pixel_count=meta_pixel_count,
                    latitude_min=query.latitude_min, latitude_max=query.latitude_max, longitude_min=query.longitude_min, longitude_max=query.longitude_max)
    meta.save()
    print("Created the metadata model, starting to generate results.")

    # creates the empty result.
    result = Result(query_id=query_id, water_percentage_path="", water_observations_path="", clear_observations_path="", data_path="", data_netcdf_path="", latitude_min=query.latitude_min,
                    latitude_max=query.latitude_max, longitude_min=query.longitude_min, longitude_max=query.longitude_max, total_scenes=0, scenes_processed=0, status="WAIT")
    result.save()

    # wrapping this in a try/catch, as it will throw a few different errors
    # having to do with memory etc.
    try:
        # lists all acquisition dates for use in single tmeslice queries.
        acquisitions = dc.list_acquisition_dates(query.platform, query.product, time=(query.time_start, query.time_end), longitude=(
            query.longitude_min, query.longitude_max), latitude=(query.latitude_min, query.latitude_max))
        result.total_scenes = len(acquisitions)
        result.save()

        wofs_data = None
        water_analysis = None
        # Iterates through the acquisition dates with the step in acquisitions_per_iteration.
        # Uses a time range computed with the index and index+acquisitions_per_iteration.
        # ensures that the start and end are both valid.
        print("Getting data and creating mosaic")
        index = 0
        # holds some acquisition based metadata.
        acquisition_dates = ""
        acquisition_dates = ""
        pixel_counts = ""
        water_pixel_counts = ""
        pixel_percentages = ""

        # iterate over all acquisitions in variable sized chunks.
        while index < len(acquisitions):
            start = acquisitions[index]
            if (index + acquisitions_per_iteration - 1) < len(acquisitions):
                end = acquisitions[index + acquisitions_per_iteration - 1]
            else:
                end = acquisitions[-1] + datetime.timedelta(hours=1)

            print(start)

            single_data = dc.get_dataset_by_extent(query.product, product_type=None, platform=query.platform, time=(start, end), longitude=(
                query.longitude_min, query.longitude_max), latitude=(query.latitude_min, query.latitude_max))

            # get the actual data and perform analysis.
            clean_mask = create_cfmask_clean_mask(single_data.cf_mask)
            wofs_data = wofs_classify(single_data, clean_mask=clean_mask)
            water_analysis = perform_timeseries_analysis_iterative(wofs_data, intermediate_product=water_analysis)

            # here the clear mask has all the clean pixels for each acquisition.
            # add to the comma seperated list of data.
            for timeslice in range(clean_mask.shape[0]):
                time = acquisitions[index + timeslice].strftime("%m/%d/%Y")
                clean_pixels = np.sum(clean_mask[timeslice, :, :] == True)
                water_pixels = np.sum(wofs_data.wofs.values[timeslice, :, :] == 1)
                acquisition_dates += time + ","
                pixel_counts += str(clean_pixels) + ","
                water_pixel_counts += str(water_pixels) + ","
                pixel_percentages += str((clean_pixels/meta.pixel_count)*100) + ","
                # create the files requied for animation..
                # if the dir doesn't exist, create it, then fill with a .png/.tif from the scene data.
                if query.animated_product != "None":
                    animated_product = AnimationType.objects.get(type_id=query.animated_product)
                    dir_path = base_result_path + query.query_id
                    tif_path = dir_path + '/' + str(index) + '.tif'
                    png_path = dir_path + '/' + str(index) + '.png'
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path)

                    #get metadata needed for tif creation.
                    product_details = dc.dc.list_products()[dc.dc.list_products().name==query.product]
                    geotransform = [single_data.longitude.values[0], product_details.resolution.values[0][1],
                                    0.0, single_data.latitude.values[0], 0.0, product_details.resolution.values[0][0]]
                    crs = str(single_data.crs)
                    animated_data = wofs_data.isel(time=timeslice) if animated_product.type_id == "scene_water" else water_analysis
                    save_to_geotiff(tif_path, gdal.GDT_Float64, animated_data, geotransform, crs,
                                    x_pixels=single_data.dims['longitude'], y_pixels=single_data.dims['latitude'])
                    # create pngs.
                    cmd = "gdaldem color-relief -of PNG -b " + animated_product.band_number + " " + tif_path + " " + color_path[int(animated_product.band_number)-1] + " " + png_path
                    os.system(cmd)
                    cmd = "convert -transparent \"#FFFFFF\" " + png_path + " " + png_path
                    os.system(cmd)
                    if result_type.fill is not "transparent":
                        cmd = "convert " + png_path + " -background " + \
                            result_type.fill + " -alpha remove " + png_path
                        os.system(cmd)
                    # remove the tiff.. some of these can be >1gb, so having one per scene is too much.
                    os.remove(tif_path)
            index = index + acquisitions_per_iteration

            result = Result.objects.get(query_id=query_id)
            if result.status == "CANCEL":
                Query.objects.filter(
                    query_id=result.query_id, user_id=user_id).delete()
                Metadata.objects.filter(query_id=result.query_id).delete()
                result.delete()
                print("Cancelling...")
                return
            result.scenes_processed = index
            result.save()

        if wofs_data is None:
            error_with_message(result, "There were no acquisitions for this parameter set.")
            return

        meta.acquisition_list = acquisition_dates
        meta.clean_pixels_per_acquisition = pixel_counts
        meta.clean_pixel_percentages_per_acquisition = pixel_percentages
        meta.water_pixels_per_acquisition = water_pixel_counts
        meta.save()

        #grabs the resolution.
        product_details = dc.dc.list_products()[dc.dc.list_products().name==query.product]
        geotransform = [single_data.longitude.values[0], product_details.resolution.values[0][1],
                        0.0, single_data.latitude.values[0], 0.0, product_details.resolution.values[0][0]]

        crs = str(single_data.crs)

        file_path = base_result_path + query_id
        netcdf_path = file_path + '.nc'
        tif_path = file_path + '.tif'
        result_paths = [file_path + '_water_percentage.png', file_path + "_water_observation.png", file_path + '_clear_observation.png', file_path + '_water_animation.gif']
        result_filled_paths = [file_path + '_filled_water_percentage.png', file_path + "_filled_water_observation.png", file_path + '_filled_clear_observation.png']

        print("Creating query results.")
        if query.animated_product != "None":
            import imageio
            import shutil
            with imageio.get_writer(file_path + '_water_animation.gif', mode='I') as writer:
                for index in range(len(acquisitions)):
                    image = imageio.imread(base_result_path + query.query_id + '/' + str(index) + '.png')
                    writer.append_data(image)
            result.water_animation_path = result_paths[3]
            #get rid of all intermediate products since there are a lot.
            shutil.rmtree(base_result_path + query.query_id)

        save_to_geotiff(tif_path, gdal.GDT_Float64, water_analysis, geotransform, crs,
                        x_pixels=single_data.dims['longitude'], y_pixels=single_data.dims['latitude'])

        water_analysis.to_netcdf(netcdf_path)

        # we've got the tif, now do the png set..
        #uses gdal dem with custom color maps..
        for index in range(len(color_path)):
            cmd = "gdaldem color-relief -of PNG -b " + str(index+1) + " " + tif_path + " " + color_path[index] + " " + result_paths[index]
            os.system(cmd)
            cmd = "convert -transparent \"#FFFFFF\" " + result_paths[index] + " " + result_paths[index]
            os.system(cmd)
            if result_type.fill is not "transparent":
                cmd = "convert " + result_paths[index] + " -background " + \
                    result_type.fill + " -alpha remove " + result_paths[index]
                os.system(cmd)

        # update the results and finish up.
        result.data_path = tif_path
        result.data_netcdf_path = netcdf_path
        result.water_percentage_path = result_paths[0]
        result.water_observations_path = result_paths[1]
        result.clear_observations_path = result_paths[2]

        result.status = "OK"
        result.save()
        print("Finished processing results")
        # all data has been processed, create results and finish up.
        query.complete = True
        query.query_end = datetime.datetime.now()
        query.save()

    except:
        error_with_message(result, "There was an exception when handling this query.")
        raise
    # end error wrapping.

    return

# Errors out under specific circumstances, used to pass error msgs to user.
# uses the result path as a message container: TODO? Change this.
def error_with_message(result, message):
    result.status = "ERROR"
    result.data_path = message
    result.save()
    print(message)
    return
