#!/bin/bash

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

