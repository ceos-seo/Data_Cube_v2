
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

import data_access_api
from data_access_api import *
def main():
    # test code
    print("test main")
#    print("Data Cube Metadata\n")
#    print(get_datacube_metadata('LANDSAT_7','ls7_ledaps'))
    print(get_datacube_metadata_full())
    print(list())
#    print("all scene metadata")
#    print(get_scene_metadata('LANDSAT_7','ls7_ledaps'))
#    print("Data Cube Scene Metadata\n")
#    print(get_scene_metadata())
#    print(list_products())
    print(list_products_and_measurements())
    print(list_platforms_and_products())

if __name__ == "__main__":
    main()
