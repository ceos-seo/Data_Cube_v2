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
# Last modified date:

from .models import Query, SatelliteBand, ResultType, Area
from datetime import datetime

# Takes post data from a request with a user id and creates a model.
# returns a query id.
# TODO: use form validation rather than doing it this way.
def create_query_from_post(user_id, post):
    start = datetime.strptime(post['time_start'], '%m/%d/%Y')
    end = datetime.strptime(post['time_end'], '%m/%d/%Y')

    bands = SatelliteBand.objects.all()
    bands_list = ""
    for band_number in post.getlist('band_selection'):
        bands_list += bands.get(satellite_id=post['platform'],
                                band_number=band_number).band_name.lower() + ','
    bands_list = bands_list.rstrip(',')
    # hardcoded product, user id. Will be changed.
    query = Query(query_start=datetime.now(), query_end=datetime.now(), user_id=user_id,
                  query_type=post['result_type'], latitude_max=post[
                      'latitude_max'], latitude_min=post['latitude_min'],
                  longitude_max=post['longitude_max'], longitude_min=post[
                      'longitude_min'],
                  time_start=start, time_end=end, platform=post[
                      'platform'], measurements=bands_list)
    if 'title' not in post or post['title'] == '':
        query.title = query.get_type_name() + " mosaic"
    else:
        query.title = post['title']
    if 'description' not in post or post['description'] == '':
        query.description = "None"
    else:
        query.description = post['description']
    query.query_id = query.generate_query_id()
    query.area_id = post['area_id']
    query.product = Area.objects.get(area_id=query.area_id).area_product
    query.complete = False
    query.save()
    return query.query_id


# pulled from peterbe.com since there were benchmarks listed.
# removes duplicates from python lists.
def uniquify_list(seq):
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]
