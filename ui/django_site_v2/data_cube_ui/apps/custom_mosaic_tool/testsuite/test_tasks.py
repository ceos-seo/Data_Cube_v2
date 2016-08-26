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

# Unit test dependencies
from django.test import TestCase
from django.test.client import Client

# Other dependencies.
from ..tasks import *
from ..models import Result
import datetime
from django.core import management
import time


class TestTasks(TestCase):

    # Used to show for diffs greater than certain characters.
    maxDiff = None
    multi_db = True

    def setUp(self):
        self.client = Client()
        management.call_command('loaddata', 'db_backups/task_dump_3.json', verbosity=0)
        init_worker()

    def tearDown(self):
        shutdown_worker()

    def test_create_cloudfree_mosaic(self):
        create_cloudfree_mosaic('2015-01-01-2016-01-02-0.3--0.3-35.8-35.2-blue-LANDSAT_7--true_color','localuser')
        self.assertTrue(1)
          
    def test_create_cloudfree_mosaic_repeat_query(self):
        create_cloudfree_mosaic('2015-01-01-2016-01-02-0.2--0.2-35.7-35.3-blue-LANDSAT_7--true_color','localuser')
        self.assertTrue(1)

    def test_create_cloudfree_mosaic_no_acquisitions(self):
        create_cloudfree_mosaic('2000-01-01-2001-01-02--0.2--0.2-35.3-35.3-blue-LANDSAT_7--true_color','localuser')
        self.assertTrue(1)
        
        """
        TODO(map) : If the question is ever answered on stack overflow we can hit a live db instead of a test db to test this.
    def test_create_cloudfree_mosaic_canceled_request(self):
        create_cloudfree_mosaic.delay('2015-01-01-2016-01-02-0.3--0.3-35.8-35.2-blue-LANDSAT_7--true_color','localuser')
        time.sleep(7)
        print(Result.objects.using('default').get(query_id='2015-01-01-2016-01-02-0.3--0.3-35.8-35.2-blue-LANDSAT_7--true_color'))
        self.assertTrue(1)
        """
    def test_error_with_message(self):
        error_with_message(Result.objects.get(id=693), "There was an error executing this result")
        self.assertTrue(1)
