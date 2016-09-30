#!/bin/bash

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
