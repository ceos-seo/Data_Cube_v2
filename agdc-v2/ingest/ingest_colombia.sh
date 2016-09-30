#!/bin/bash

start_time=$(date)

echo ${start_time}

data_path=/colombia_cubes/micro/original_data

#datacube product add /home/localuser/agdc-v2/ingest/dataset_types/ls7_sr_scenes_wgs84.yaml

for scene_path in `ls -d ${data_path}/*/`; do
  echo ${scene_path};
  datacube dataset add -t ls7_ledaps_utm18_scene ${scene_path};
done

datacube ingest -c /home/localuser/agdc-v2/ingest/ingestion_configs/ls7_sr_scenes_wgs84_colombia.yaml

end_time=$(date)
echo "Ingestion was started at ${start_time}"
echo "Ingestion completed at ${end_time}"

