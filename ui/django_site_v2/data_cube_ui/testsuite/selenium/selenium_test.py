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

# Selenium dependencies
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import platform
import os

# Configuration options for Firefox
caps = DesiredCapabilities.FIREFOX
caps["marionette"] = True
caps["binary"] = "C:\\Program Files (x86)\\Mozilla Firefox\\firefox"

# Configuration options for Chrome
my_chrome_options = Options()
my_chrome_options.add_argument("--ignore-gpu-blacklist")

# Constants
url = "http://192.168.100.233"

# Driver
driver = None

# Connecting to browser and opening.
# Returns the driver to be used to navigate.
def open_browser(url):
    global driver

    # For Firefox.  Can't use yet due to lack of functionality.
    # TODO(map) : Code block for Firefox and OS checks
    #driver = webdriver.Firefox(capabilities=caps)
    
    # Checking for type of OS
    if "Linux" in platform.platform():
        driver = webdriver.Chrome('/home/localuser/Datacube/data_cube_ui/testsuite/drivers/chromedriver_linux', chrome_options=my_chrome_options)
    elif "Windows" in platform.platform():
        driver_location = os.getcwd().replace("selenium","drivers") + "\\chromedriver_windows"
        driver = webdriver.Chrome(driver_location, chrome_options=my_chrome_options)
    
    driver.get(url)
    driver.maximize_window()
    return driver

# Logging in.
def log_in():
    driver.find_element_by_id("login-button").click()
    driver.find_element_by_id("id_username").send_keys("localuser")
    driver.find_element_by_id("id_password").send_keys("amadev12")
    time.sleep(2)
    driver.find_element_by_id("log-in-submit").click()


def get_cube(cube_name):
    action = webdriver.ActionChains(driver)
    elem = driver.find_element_by_id("map_tools")
    action.move_to_element(elem)
    time.sleep(2)
    action.move_to_element(driver.find_element_by_id(cube_name))
    time.sleep(2)
    action.perform()
    
    time.sleep(2)
    driver.find_element_by_id(cube_name).click()

# Run a job for Landsat 7.
def create_a_job_no_clicks():
    # Default leaving the Result Type to first selection.
    # Select the first band only.
    driver.find_element_by_id("LANDSAT_7_band_selection_ms").click()
    checkboxes = driver.find_elements_by_xpath("//input[@type='checkbox']")
    for checkbox in checkboxes:
        if 'LANDSAT_7' in checkbox.get_attribute('id'):
            checkbox.click()
            break
    driver.find_element_by_id("LANDSAT_7_band_selection_ms").click()
    # Set Lon,Lat min and max.
    driver.find_element_by_id("LANDSAT_7_latitude_min").send_keys("-0.5")
    driver.find_element_by_id("LANDSAT_7_latitude_max").send_keys("0.25")
    driver.find_element_by_id("LANDSAT_7_longitude_min").send_keys("-75.2")
    driver.find_element_by_id("LANDSAT_7_longitude_max").send_keys("-74.5")
    # Set the date.
    driver.find_element_by_id("LANDSAT_7_time_start").send_keys("01/01/2010")
    driver.find_element_by_id("LANDSAT_7_time_end").clear()
    driver.find_element_by_id("LANDSAT_7_time_end").send_keys("01/01/2011")
    driver.find_element_by_id("LANDSAT_7_time_end").send_keys(Keys.TAB)
    time.sleep(2)
    # Add additional info.
    driver.find_element_by_id("additional-info").click()
    time.sleep(2)
    driver.find_element_by_id("query-title").send_keys("Sample Title")
    driver.find_element_by_id("query-description").send_keys("Sample Description")
    time.sleep(2)
    driver.find_element_by_id("save-and-close").click()
    time.sleep(2)
    driver.find_element_by_id("submit-request").click()
    time.sleep(30)

# Clicks on the first item in the Track History and loads the result.
def show_results():
    driver.find_element_by_id("past_0").click()
    time.sleep(2)
    driver.find_element_by_id("load0").click()
    time.sleep(2)
    driver.find_element_by_id("ui-id-2").click()
    time.sleep(2)
    driver.find_element_by_id("result_2010-01-01-2011-01-01-0.25--0.5--74.5--75.2-blue-LANDSAT_7--true_color").click()
    time.sleep(10)
    
# Navigate to task manager.
def go_to_task_manager():
    driver.find_element_by_id("logout-button")
    driver.find_element_by_id("task-manager-nav").click()
    time.sleep(2)

# Click on the details for a single query.
def get_details_page():
    driver.find_element_by_class_name("btn").click()

try:
    driver = open_browser(url)
    # Setting to poll for 5 seconds if element isn't present.
    driver.implicitly_wait(5)

    log_in()

    # Go to any Cube page.
    # Currently out due to no data being present.
    #get_cube("colombia")
    #get_cube("kenya")
    get_cube("kenya_micro")
    get_cube("colombia_micro")
    
    # Creates a Request
    create_a_job_no_clicks()

    show_results()
    
    # Go to Task Manager page.
    go_to_task_manager()
    
    # Go to Details page.
    get_details_page()

finally:
    #time.sleep(2)
    time.sleep(60)
    driver.quit()
