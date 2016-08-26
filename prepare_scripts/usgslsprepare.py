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


# coding=utf-8
"""
Ingest data from the command-line.
"""
from __future__ import absolute_import, division

import logging
import uuid
from xml.etree import ElementTree
import re
from pathlib import Path
import yaml
from dateutil import parser
from datetime import timedelta
import rasterio.warp
import click
from osgeo import osr
import os


_STATIONS = {'023': 'TKSC', '022': 'SGS', '010': 'GNC', '011': 'HOA',
             '012': 'HEOC', '013': 'IKR', '014': 'KIS', '015': 'LGS',
             '016': 'MGR', '017': 'MOR', '032': 'LGN', '019': 'MTI', '030': 'KHC',
             '031': 'MLK', '018': 'MPS', '003': 'BJC', '002': 'ASN', '001': 'AGS',
             '007': 'DKI', '006': 'CUB', '005': 'CHM', '004': 'BKT', '009': 'GLC',
             '008': 'EDC', '029': 'JSA', '028': 'COA', '021': 'PFS', '020': 'PAC'}


def band_name(path):
    name = path.stem
    position = name.find('_')

    if position == -1:
        raise ValueError('Unexpected tif image in eods: %r' % path)
    if re.match(r"[Bb]\d+", name[position+1:]):
        layername = name[position+2:]

    else:
        layername = name[position+1:]
    return layername


def get_projection(path):
    with rasterio.open(str(path)) as img:
        left, bottom, right, top = img.bounds
        return {
            'spatial_reference': str(img.crs_wkt),
            'geo_ref_points': {
                'ul': {'x': left, 'y': top},
                'ur': {'x': right, 'y': top},
                'll': {'x': left, 'y': bottom},
                'lr': {'x': right, 'y': bottom},
                }
        }


def get_coords(geo_ref_points, spatial_ref):
    spatial_ref = osr.SpatialReference(spatial_ref)
    t = osr.CoordinateTransformation(spatial_ref, spatial_ref.CloneGeogCS())

    def transform(p):
        lon, lat, z = t.TransformPoint(p['x'], p['y'])
        return {'lon': lon, 'lat': lat}
    return {key: transform(p) for key, p in geo_ref_points.items()}


def populate_coord(doc):
    proj = doc['grid_spatial']['projection']
    doc['extent']['coord'] = get_coords(proj['geo_ref_points'], proj['spatial_reference'])


def crazy_parse(timestr):
    try:
        return parser.parse(timestr)
    except ValueError:
        if not timestr[-2:] == "60":
            raise
        return parser.parse(timestr[:-2]+'00') + timedelta(minutes=1)


def prep_dataset(fields, path):

    for file in os.listdir(str(path)):
        print "examining file: ",file
        if file.endswith(".xml") and (not file.endswith('aux.xml')):
            print "found xml file "
            metafile = file
    # Parse xml ElementTree gives me a headache so using lxml
    doc = ElementTree.parse(os.path.join(str(path), metafile))
    root = doc.getroot()
    print "got root Attrib: ",root.attrib," text: ",root.text
    #TODO root method doesn't work here - need to include xlmns...
#    print "found global metadata",global_metadata.text
    global_metadata = None;

    for root_child in root:
        if (root_child.tag[-15:] == "global_metadata"): 
            print "found global metadata tag"
            global_metadata = root_child
            prepend = global_metadata.tag
            prepend = prepend.replace('global_metadata','')
            print "determined prepend as:",prepend
      #  print "Child found: ", root_child.tag, "|",root_child.attrib,"|", root_child.text
   
    for child in global_metadata:
        print "Child found: ", child.tag, "|",child.attrib,"|", child.text
        name = child.tag.replace(prepend,"")
        print "matching: ",name
        if (name == 'satellite'):
            satellite = child.text  
        if (name == 'instrument'):
            instrument = child.text  
        if (name == 'acquisition_date'): 
            acquisition_date =  child.text.replace("-","")
        if (name == 'scene_center_time'):
            scene_center_time =  child.text[:8]
        if (name == 'lpgs_metadata_file'):
            lpgs_metadata_file = child.text
    
    print "determined acquisition_date as: ",acquisition_date
    center_dt = crazy_parse(acquisition_date+"T"+scene_center_time)
    aos = crazy_parse(acquisition_date+"T"+scene_center_time)-timedelta(seconds=(24/2))
    print "determined aos as: ",aos
    los = aos + timedelta(seconds=24)
    groundstation = lpgs_metadata_file[16:19]
    fields.update({'instrument': instrument, 'satellite': satellite})
    print "completed pulling general metadata" 

    

    print "about to use aos, hope it's set!"
    start_time = aos
    end_time = los
    images = {band_name(im_path): {
        'path': str(im_path.relative_to(path))
    } for im_path in path.glob('*.tif')}

    doc = {
        'id': str(uuid.uuid4()),
        'processing_level': fields["level"],
        'product_type': fields["type"],
        'creation_dt':  fields["creation_dt"],
        'platform': {'code': fields["satellite"]},
        'instrument': {'name': fields["instrument"]},
        'acquisition': {
            'groundstation': {
                'name': groundstation,
                'aos': str(aos),
                'los': str(los)
            }
        },
        'extent': {
            'from_dt': str(start_time),
            'to_dt': str(end_time),
            'center_dt': str(center_dt)
        },
        'format': {'name': 'GeoTiff'},
        'grid_spatial': {
            'projection': get_projection(path/next(iter(images.values()))['path'])
        },
        'image': {
            'satellite_ref_point_start': {'path': int(fields["path"]), 'row': int(fields["row"])},
            'satellite_ref_point_end': {'path': int(fields["path"]), 'row': int(fields["row"])},
            'bands': images
        },
        #TODO include 'lineage': {'source_datasets': {'lpgs_metadata_file': lpgs_metadata_file}}
        'lineage': {'source_datasets': {}}
    }
    populate_coord(doc)
    return doc


def dataset_folder(fields):
    fmt_str = "{vehicle}_{instrument}_{type}_{level}_GA{type}{product}-{groundstation}_{path}_{row}_{date}"
    return fmt_str.format(**fields)


def prepare_datasets(nbar_path):

    fields = re.match(
        (
            r"(?P<code>LC8|LE7|LT5)"
            r"(?P<path>[0-9]{3})"
            r"(?P<row>[0-9]{3})"
            r"(?P<productyear>[0-9]{4})"
            r"(?P<julianday>[0-9]{3})"

        ), nbar_path.stem).groupdict()

    timedelta(days=int(fields["julianday"]))
    fields.update({'level': 'sr_refl', 'type': 'LEDAPS', 'creation_dt': ((crazy_parse(fields["productyear"]+'0101T00:00:00'))+timedelta(days=int(fields["julianday"])))})
    print "About to prep dataset"
    nbar = prep_dataset(fields, nbar_path)
    print "Completed preping dataset"
    return (nbar, nbar_path)


@click.command(help="Prepare USGS LS dataset for ingestion into the Data Cube.")
@click.argument('datasets',
                type=click.Path(exists=True, readable=True, writable=True),
                nargs=-1)
def main(datasets):
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)
    print "Entering program" 
    for dataset in datasets:
        path = Path(dataset)
        print "Processing", path
        logging.info("Processing %s", path)
        print "About to prepare datasets" 
        documents = prepare_datasets(path)
        print "completed preparing dataset, about to write output"
        dataset, folder = documents
        yaml_path = str(folder.joinpath('agdc-metadata.yaml'))
        logging.info("Writing %s", yaml_path)
        with open(yaml_path, 'w') as stream:
            yaml.dump(dataset, stream)

if __name__ == "__main__":
    main()