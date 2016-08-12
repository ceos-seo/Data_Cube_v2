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
