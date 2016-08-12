# Django specific
from celery.decorators import task
from celery.signals import worker_process_init, worker_process_shutdown
from .models import Query, Result, ResultType, Metadata

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
from utils.dc_mosaic import create_mosaic_iterative
from utils.dc_utilities import save_to_geotiff, create_cfmask_clean_mask
from .utils import uniquify_list


# Author: AHDS
# Creation date: 2016-06-23
# Modified by:
# Last modified date:

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
@task(name="get_data_task")
def create_cloudfree_mosaic(query_id, user_id):
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

    measurements = []
    # collects the bands required to display, the data bands, and the cfmask.
    # Removes dups.
    result_type = ResultType.objects.get(
        satellite_id=query.platform, result_id=query.query_type)

    measurements.extend([result_type.red, result_type.green, result_type.blue])
    measurements.append('cf_mask')
    measurements.extend(query.measurements.rstrip(',').split(","))
    measurements = uniquify_list(measurements)

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
    result = Result(query_id=query_id, result_path="", data_path="", latitude_min=query.latitude_min,
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

        full_data = None

        # Iterates through the acquisition dates with the step in acquisitions_per_iteration.
        # Uses a time range computed with the index and index+acquisitions_per_iteration.
        # ensures that the start and end are both valid.
        print("Getting data and creating mosaic")
        acquisitions_per_iteration = 1
        index = 0
        # holds some acquisition based metadata.
        acquisition_dates = ""
        pixel_counts = ""
        pixel_percentages = ""
        while index < len(acquisitions):
            start = acquisitions[index]
            if (index + acquisitions_per_iteration - 1) < len(acquisitions):
                end = acquisitions[index + acquisitions_per_iteration - 1]
            else:
                end = acquisitions[-1] + datetime.timedelta(hours=1)

            print(start)

            single_data = dc.get_dataset_by_extent(query.product, product_type=None, platform=query.platform, time=(start, end), longitude=(
                query.longitude_min, query.longitude_max), latitude=(query.latitude_min, query.latitude_max), measurements=measurements)

            clear_mask = create_cfmask_clean_mask(single_data.cf_mask)

            # Removes the cf mask variable from the dataset after the clear mask has been created.
            # prevents the cf mask from being put through the mosaicing function as it doesn't fit
            # the correct format w/ nodata values for mosaicing.
            single_data = single_data.drop('cf_mask')

            # here the clear mask has all the clean pixels for each acquisition.
            for timeslice in range(clear_mask.shape[0]):
                time = acquisitions[index + timeslice].strftime("%m/%d/%Y")
                clean_pixels = np.sum(clear_mask[timeslice, :, :] == True)
                acquisition_dates += time + ","
                pixel_counts += str(clean_pixels) + ","
                pixel_percentages += str((clean_pixels/meta.pixel_count)*100) + ","

            full_data = create_mosaic_iterative(single_data, clean_mask=clear_mask, intermediate_product=full_data)

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

        if full_data is None:
            error_with_message(result, "There were no acquisitions for this parameter set.")
            return

        meta.acquisition_list = acquisition_dates
        meta.clean_pixels_per_acquisition = pixel_counts
        meta.clean_pixel_percentages_per_acquisition = pixel_percentages

        # Count clean pixels and correct for the number of measurements.
        clean_pixels = np.sum(full_data[measurements[0]].values != -9999)
        meta.clean_pixel_count = clean_pixels
        meta.percentage_clean_pixels = (
            meta.clean_pixel_count / meta.pixel_count) * 100
        meta.save()

        # all data has been processed, create results and finish up.
        query.complete = True
        query.save()

        #grabs the resolution.
        product_details = dc.dc.list_products()[dc.dc.list_products().name==query.product]
        geotransform = [single_data.longitude.values[0], product_details.resolution.values[0][1],
                        0.0, single_data.latitude.values[0], 0.0, product_details.resolution.values[0][0]]

        crs = str(single_data.crs)

        file_path = '/tilestore/result/' + query_id
        tif_path = file_path + '.tif'
        png_path = file_path + '.png'
        png_filled_path = file_path + "_filled.png"

        print("Creating query results.")
        save_to_geotiff(tif_path, gdal.GDT_Int16, full_data, geotransform, crs,
                        x_pixels=single_data.dims['longitude'], y_pixels=single_data.dims['latitude'])

        # we've got the tif, now do the png.
        cmd = "gdal_translate -ot Byte -outsize 50% 50% -scale 0 4096 0 255 -of PNG -b 1 -b 2 -b 3 " + \
            tif_path + ' ' + png_path
        os.system(cmd)

        cmd = "convert -transparent \"#000000\" " + png_path + " " + png_path
        os.system(cmd)
        cmd = "convert " + png_path + " -background " + \
            result_type.fill + " -alpha remove " + png_filled_path
        os.system(cmd)

        # update the results and finish up.
        result.result_path = png_path
        result.data_path = tif_path
        result.result_filled_path = png_filled_path
        result.status = "OK"
        result.save()
        print("Finished processing results")
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
    result.result_path = message
    result.save()
    print(message)
    return
