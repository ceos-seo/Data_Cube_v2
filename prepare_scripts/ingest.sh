#!/bin/bash

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

# Usage:   ingest.sh original_data_path dataset_type ingestion_config
# Example: ingest.sh /micro_cube/kenya_original_data dataset_types/ls7_sr_scenes_wgs84_kenya.yaml ingestion_configs/ls7_sr_scenes_wgs84_kenya.yaml

start_time=$(date)

echo ${start_time}

data_path=$1 

datacube product add $2

for scene_path in `ls -d ${data_path}/*/`; do
  echo ${scene_path};
  datacube dataset add --auto-match ${scene_path};
done

datacube ingest -c $3

end_time=$(date)
echo "Ingestion was started at ${start_time}"
echo "Ingestion completed at ${end_time}"
