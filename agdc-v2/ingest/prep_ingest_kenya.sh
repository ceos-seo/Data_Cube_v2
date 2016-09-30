#!/bin/bash

data_path=/micro_cube/original_data

for a in `ls -1 ${data_path}/*.tgz`; do

echo $a

mkdir ${data_path}/temp;
tar -C ${data_path}/temp -zxf $a;

sceneid=`ls -1 ${data_path}/temp | head -n 1 | grep -o 'LE7[0-9A-Z]\+\?'`;

echo ${sceneid};

mkdir ${data_path}/${sceneid}
mv ${data_path}/temp/${sceneid}/* ${data_path}/${sceneid};
rm -r ${data_path}/temp;

python2 /home/localuser/agdc-v2/ingest/usgslsprepare.py ${data_path}/${sceneid};
datacube -v dataset add -t ls7_ledaps_utm36_scene  ${data_path}/${sceneid};
datacube -v ingest -c /home/localuser/agdc-v2/ingest/ingestion_configs/ls7_sr_scenes_wgs84_kenya.yaml

rm -rf ${data_path}/${sceneid}

done
#sudo datacube-ingest stack

