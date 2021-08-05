#!/bin/bash
#SBATCH -A cli137 
#SBATCH -J amazonas_41
#SBATCH -N 1
#SBATCH -t 1:00:00
#SBATCH --mail-type=FAIL
#SBATCH --mail-type=END
#SBATCH --mail-user=msteckle@vols.utk.edu
#SBATCH --get-user-env
#SBATCH --mem=0

cd $SLURM_SUBMIT_DIR
date

source $HOME/.bashrc
conda activate interp

S=41
F=41
STATE=costa_rica

for(( t=${S}; t<=${F}; t++ ))
do
  echo "Start interpolation for tile ${t}"
  INFILE=/gpfs/alpine/cli137/proj-shared/6ru/${STATE}/${STATE}_biweekly/${STATE}_biweekly_${t}/${STATE}_biweekly_${t}_timeseries
  CFILE=/gpfs/alpine/cli137/proj-shared/6ru/${STATE}/${STATE}_biweekly/${STATE}_biweekly_${t}/${STATE}_biweekly_${t}_timeseries.coords

# # split the INFILE and CFILE in 100,000 chunks
  rm ${INFILE}.split.* ${CFILE}.split.*
  split -d -l 100000 ${INFILE} ${INFILE}.split. 
  split -d -l 100000 ${CFILE} ${CFILE}.split. 

  NSPLITS=`ls ${INFILE}.split.*|wc -l`
  echo "We have ${NSPLITS} chunks to process"
  for(( c=0; c<${NSPLITS}; c++ )) 
  do
    echo "Processing file: ${INFILE}.split.`printf "%02d" "${c}"`"
    python interp_and_smooth.py -f --infile ${INFILE}.split.`printf "%02d" "${c}"` --outfile ${INFILE}.split.`printf "%02d" "${c}"` --cfile ${CFILE}.split.`printf "%02d" "${c}"` --syear 2017 --eyear 2021 --percentile 5 --step "biweekly" & 
  done
  wait

  for(( c=0; c<${NSPLITS}; c++ ))
  do
    echo "Smoothing file: ${INFILE}.split.`printf "%02d" "${c}"`.interp"
    python interp_and_smooth.py -s --infile "${INFILE}.split.`printf "%02d" "${c}"`.interp" --outfile ${INFILE}.split.`printf "%02d" "${c}"` --syear 2017 --eyear 2021 &
  done
  wait

  for(( c=0; c<${NSPLITS}; c++ ))
  do
    mv /gpfs/alpine/cli137/proj-shared/6ru/${STATE}/${STATE}_biweekly/${STATE}_biweekly_${t}/${STATE}_biweekly_${t}_timeseries.coords.split.`printf "%02d" ${c}` /gpfs/alpine/cli137/proj-shared/6ru/${STATE}/${STATE}_biweekly/${STATE}_biweekly_${t}/${STATE}_biweekly_${t}_timeseries.split.`printf "%02d" ${c}`.coords
  done
  wait

done

echo "Add tasks finished.. exiting"
