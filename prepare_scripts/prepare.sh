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


# Usage:   prepare.sh original_data_path
# Example: prepare.sh /micro_cube/kenya_original_data

data_path=$1

for a in `ls -1 ${data_path}/*.tar.gz`; do
  echo $a
  
  mkdir ${data_path}/temp;
  tar -C ${data_path}/temp -zxf $a;

  sceneid=`ls -1 ${data_path}/temp | head -n 1 | grep -o 'LE7[0-9A-Z]\+\?'`;
  echo ${sceneid};
  
  mkdir ${data_path}/${sceneid}
  mv ${data_path}/temp/* ${data_path}/${sceneid};

  python /home/localuser/usgslsprepare.py ${data_path}/${sceneid};
  
  rm -r ${data_path}/temp;
  
done

