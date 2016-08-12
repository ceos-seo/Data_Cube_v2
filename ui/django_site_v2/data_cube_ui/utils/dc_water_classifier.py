import gdal, osr
import collections
import gc
import numpy as np
from datetime import datetime
import collections
import argparse

import datacube

import dc_utilities as utilities

# Author: KMF
# Creation date: 2016-06-13
# Modified by:
# Last modified date: 
    
def wofs_classify(platform, bands, clean_mask, no_data=-9999, enforce_float64=False):
    """
    TODO: Add description of function, inputs, output
    
    Dataset must contain bands 1-5, 7, and the cfmask
    
    Mask type can be ledaps or cfmask
    
    According to "Landsat Surface Reflectance Quality Assessment, cfmask is likely to 
    present more accurate results than its companion bands for cloud, cloud shadow, snow,
    and water identification
    http://landsat.usgs.gov/landsat_climate_data_records_quality_calibration.php
    
    Adapted from: 
    https://github.com/GeoscienceAustralia/eo-tools/blob/stable/eotools/water_classifier.py
    
    Reference:
    "Water observations from space: ..."
    
    """
    
    def _band_ratio(a, b):
        """
        Calculates a normalized ration index
        """
        return (a - b) / (a + b)
        
    def _run_regression(band1, band2, band3, band4, band5, band7):
        """
        Regression analysis based on Australia's training data
        TODO: Return type
        """
        
        # Compute normalized ratio indices
        ndi_52 = _band_ratio(band5, band2)
        ndi_43 = _band_ratio(band4, band3)
        ndi_72 = _band_ratio(band7, band2)
        
        #classified = np.ones(shape, dtype='uint8')
        
        classified = np.full(shape, no_data)
      
        # Start with the tree's left branch, finishing nodes as needed
        
        # Left branch
        r1 = ndi_52 <= -0.01

        r2 = band1 <= 2083.5
        classified[r1 & ~r2] = 0 #Node 3

        r3 = band7 <= 323.5
        _tmp = r1 & r2
        _tmp2 = _tmp & r3
        _tmp &= ~r3

        r4 = ndi_43 <= 0.61
        classified[_tmp2 & r4] = 1 #Node 6
        classified[_tmp2 & ~r4] = 0 #Node 7

        r5 = band1 <= 1400.5
        _tmp2 = _tmp & ~r5

        r6 = ndi_43 <= -0.01
        classified[_tmp2 & r6] = 1 #Node 10
        classified[_tmp2 & ~r6] = 0 #Node 11

        _tmp &= r5

        r7 = ndi_72 <= -0.23
        _tmp2 = _tmp & ~r7

        r8 = band1 <= 379
        classified[_tmp2 & r8] = 1 #Node 14
        classified[_tmp2 & ~r8] = 0 #Node 15

        _tmp &= r7

        r9 = ndi_43 <= 0.22
        classified[_tmp & r9] = 1 #Node 17
        _tmp &= ~r9

        r10 = band1 <= 473
        classified[_tmp & r10] = 1 #Node 19
        classified[_tmp & ~r10] = 0 #Node 20

        # Left branch complete; cleanup
        del r2, r3, r4, r5, r6, r7, r8, r9, r10
        gc.collect()
        
        # Right branch of regression tree
        r1 = ~r1

        r11 = ndi_52 <= 0.23
        _tmp = r1 & r11

        r12 = band1 <= 334.5
        _tmp2 = _tmp & ~r12
        classified[_tmp2] = 0 #Node 23

        _tmp &= r12

        r13 = ndi_43 <= 0.54
        _tmp2 = _tmp & ~r13
        classified[_tmp2] = 0 #Node 25

        _tmp &= r13

        r14 = ndi_52 <= 0.12
        _tmp2 = _tmp & r14
        classified[_tmp2] = 1 #Node 27

        _tmp &= ~r14

        r15 = band3 <= 364.5
        _tmp2 = _tmp & r15

        r16 = band1 <= 129.5
        classified[_tmp2 & r16] = 1 #Node 31
        classified[_tmp2 & ~r16] = 0 #Node 32

        _tmp &= ~r15

        r17 = band1 <= 300.5
        _tmp2 = _tmp & ~r17
        _tmp &= r17
        classified[_tmp] = 1 #Node 33
        classified[_tmp2] = 0 #Node 34

        _tmp = r1 & ~r11

        r18 = ndi_52 <= 0.34
        classified[_tmp & ~r18] = 0 #Node 36
        _tmp &= r18

        r19 = band1 <= 249.5
        classified[_tmp & ~r19] = 0 #Node 38
        _tmp &= r19

        r20 = ndi_43 <= 0.45
        classified[_tmp & ~r20] = 0 #Node 40
        _tmp &= r20

        r21 = band3 <= 364.5
        classified[_tmp & ~r21] = 0 #Node 42
        _tmp &= r21

        r22 = band1 <= 129.5
        classified[_tmp & r22] = 1 #Node 44
        classified[_tmp & ~r22] = 0 #Node 45

        # Completed regression tree
        
        return classified
    
    if platform != 'LANDSAT_7':
        print 'The WoFS classifier is only available for Landsat 7'
        return

    dtype = bands.dtype
    
    # Check whether to enforce float64 calcs, unless datatype is already float64
    # Otherwise, enforce float32 calcs
    if enforce_float64:
        if dtype != 'float64':
            bands = bands.astype('float64')
    else:
        if dtype == 'float64':
            pass
        elif dtype != 'float32':
            bands = bands.astype('float32')
    
    b1 = bands[0]
    b2 = bands[1]
    b3 = bands[2]
    b4 = bands[3]
    b5 = bands[4]
    b7 = bands[5]

    shape = b1.shape
    
    classified = _run_regression(b1, b2, b3, b4, b5, b7)
        
    classified_clean = np.full(classified.shape, no_data)
    classified_clean[clean_mask] = classified[clean_mask] # Contains data for clear pixels
        
    return classified_clean

def ledaps_classify(water_band, qa_bands, no_data=-9999):
    """
    TODO: Add description of function, inputs, output
    TODO: Testing once reingestion on bdn3 is complete
    """
    
    fill_qa = qa_bands[0]
    cloud_qa = qa_bands[1]
    cloud_shadow_qa = qa_bands[2]
    adjacent_cloud_qa = qa_bands[3]
    snow_qa = qa_bands[4]
    ddv_qa = qa_bands[5]
    
    '''
    
    '''
    
    fill_mask = np.reshape(np.in1d(fill_qa.reshape(-1), [0]), 
                           fill_qa.shape)                  
    cloud_mask = np.reshape(np.in1d(cloud_qa.reshape(-1), [0]), 
                            cloud_qa.shape)                              
    cloud_shadow_mask = np.reshape(np.in1d(cloud_shadow_qa.reshape(-1), [0]), 
                                   cloud_shadow_qa.shape)
    adjacent_cloud_mask = np.reshape(np.in1d(adjacent_cloud_qa.reshape(-1), [255]), 
                                     adjacent_cloud_qa.shape)                 
    snow_mask = np.reshape(np.in1d(snow_qa.reshape(-1), [0]), 
                           snow_qa.shape)
    ddv_mask = np.reshape(np.in1d(ddv_qa.reshape(-1), [0]), 
                          ddv_qa.shape)
        
    clean_mask = fill_mask & cloud_mask & cloud_shadow_mask & adjacent_cloud_mask & snow_mask & ddv_mask
    
    print clean_mask
    
    water_mask = np.reshape(np.in1d(water_band.reshape(-1), [255]), 
                                    water_band.shape) #Will be true if 255 -> water
                                    
    classified = np.copy(water_mask)
    classified.astype(int)
    
    print classified
    
    classified_clean = np.full(classified.shape, no_data)
    classified_clean[clean_mask] = classified[clean_mask]
    
    return classified_clean

def cfmask_classify(cfmask, no_data=-9999):
    # Create clean mask
        
    # cfmask values:
    #   0 - clear
    #   1 - water
    #   2 - cloud shadow
    #   3 - snow
    #   4 - cloud
    #   255 - fill
    
    # Create a clean mask for clean land/water pixels, 
    # i.e. mask out shadow, snow, cloud, and no data
    clean_mask = np.reshape(np.in1d(cfmask.reshape(-1), [2, 3, 4, 255], invert=True), 
                            cfmask.shape)
                            
    water_mask = np.reshape(np.in1d(cfmask.reshape(-1), [1]), 
                            cfmask.shape)
                            
    classified = np.copy(water_mask)
    classified.astype(int)
    
    classified_clean = np.full(classified.shape, no_data)
    classified_clean[clean_mask] = classified[clean_mask]
    
    return classified_clean
    
if __name__ == '__main__':
    '''TODO CLEAN UP'''
    start_date = datetime.now()
    
    #TODO: Add argparser to pass in for cmd-line tool - pass in classifier, dataset
    
    #dc = utilities.enable_config()
    
    platform = 'LANDSAT_7'
    
    dc = datacube.Datacube(app='dc-water-detection')
    
    lon = 36
    lat = 0
    
    dataset_in = dc.load(product='ls7_ledaps', 
                      time=((2015, 1, 1), (2015, 12, 31)),
                      lon=(lon, lon+1), 
                      lat=(lat, lat+1))
    
                                        
    acquisition_dates = dataset_in.time.values
    
    crs = dataset_in.crs
    spatial_ref = utilities.get_spatial_ref(crs)
    
    latitudes = dataset_in.latitude.values
    longitudes = dataset_in.longitude.values

    ul_lon = longitudes[0]
    ul_lat = latitudes[0]

    #TODO: Is there a way to make it so this is not hardcoded?
    lon_dist =  0.000269493
    lat_dist = -0.000269493

    lon_rtn = 0
    lat_rtn = 0

    geotransform = (ul_lon, lon_dist, lon_rtn, ul_lat, lat_rtn, lat_dist)
    
    for index, acq_date in enumerate(acquisition_dates):
        print "Processing " + str(acq_date)
        
        
        qa_bands = np.array([dataset_in.fill_qa.values[index],
                            dataset_in.cloud_qa.values[index],
                            dataset_in.cloud_shadow_qa.values[index],
                            dataset_in.adjacent_cloud_qa.values[index],
                            dataset_in.snow_qa.values[index],
                            dataset_in.ddv_qa.values[index]])
        
        water_band = dataset_in.land_water_qa.values[index]
        
        cfmask = dataset_in.cf_mask.values[index]
        
        # cfmask values:
        #   0 - clear
        #   1 - water
        #   2 - cloud shadow
        #   3 - snow
        #   4 - cloud
        #   255 - fill
        
        fill_mask = np.reshape(np.in1d(cfmask.reshape(-1), [255]), 
                               cfmask.shape)
        cloud_mask = np.reshape(np.in1d(cfmask.reshape(-1), [4]), 
                                cfmask.shape)
        cloud_shadow_mask = np.reshape(np.in1d(cfmask.reshape(-1), [2]), 
                                       cfmask.shape)
        snow_mask = np.reshape(np.in1d(cfmask.reshape(-1), [3]), 
                               cfmask.shape)   
        
        fill_qa = np.zeros(cfmask.shape)
        cloud_qa = np.zeros(cfmask.shape)
        cloud_shadow_qa = np.zeros(cfmask.shape)
        snow_qa = np.zeros(cfmask.shape)
        
        fill_qa[fill_mask] = 255
        cloud_qa[cloud_mask] = 255
        cloud_shadow_qa[cloud_shadow_mask] = 255
        snow_qa[snow_mask] = 255
        
        adjacent_cloud_qa = np.full(cfmask.shape, 255)
        ddv_qa = np.zeros(cfmask.shape)
        
        qa_bands = np.array([fill_qa,
                             cloud_qa,
                             cloud_shadow_qa,
                             adjacent_cloud_qa,
                             snow_qa,
                             ddv_qa])
                         
        #water_class_cfmask = cfmask_classify(cfmask)
        water_class_ledaps = ledaps_classify(water_band, qa_bands)
        #out_size = water_class_ledaps.shape
        out_file = str(lon) + '_' + str(lat) + '_' + str(acq_date) + '.tif'
        #bands_out = collections.OrderedDict([('cfmask', water_class_cfmask)])
        bands_out = collections.OrderedDict([('ledaps', water_class_ledaps)])
        utilities.save_to_geotiff(out_file, gdal.GDT_Int16, bands_out, geotransform, spatial_ref)
        
        break
   
    '''
    
    for index, acq_date in enumerate(acquisition_dates):
        print "Processing " + str(acq_date)
                            
        bands_in = np.array([dataset_in.blue.values[index],
                            dataset_in.green.values[index],
                            dataset_in.red.values[index],
                            dataset_in.nir.values[index],
                            dataset_in.swir1.values[index],
                            dataset_in.swir2.values[index]])
                         
        # Create clean mask
        
        # cfmask values:
        #   0 - clear
        #   1 - water
        #   2 - cloud shadow
        #   3 - snow
        #   4 - cloud
        #   255 - fill
        
        cfmask = dataset_in.cf_mask.values[index]
        # Create a clean mask for clean land/water pixels, 
        # i.e. mask out shadow, snow, cloud, and no data
        clean_mask = np.reshape(np.in1d(cfmask.reshape(-1), [2, 3, 4, 255], invert=True), 
                                cfmask.shape)
        water_class_wofs = wofs_classify(platform, bands_in, clean_mask)
        out_file = str(lon) + '_' + str(lat) + '_' + str(acq_date) + '.tif'
        bands_out = collections.OrderedDict([('wofs', water_class_wofs)])
        utilities.save_to_geotiff(out_file, gdal.GDT_Int16, bands_out, geotransform, spatial_ref)
        '''
        
    
    end_date = datetime.now()
    print end_date - start_date