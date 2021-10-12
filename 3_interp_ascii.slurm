#!/bin/bash
#SBATCH -A cli137 
#SBATCH -J roraima_0-9
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

S=0
F=9
STATE=roraima
SYEAR=2017
EYEAR=2021 #Final year plus one
DATA_LOC=/gpfs/alpine/cli137/proj-shared/6ru/${STATE}_data

for(( t=${S}; t<=${F}; t++ ))
do
	
  # Set coordinate and timeseries file paths
  echo "Start interpolation for tile ${t}"
  INFILE=${DATA_LOC}/${STATE}_biweekly_ascii/${STATE}_biweekly_${t}_timeseries
  COFILE=${DATA_LOC}/${STATE}_biweekly_ascii/${STATE}_biweekly_${t}_timeseries.coords
  OUFILE=${DATA_LOC}/${STATE}_biweekly/${STATE}_biweekly_${t}

  # Create outfile subdirectories
  mkdir ${OUFILE}

  # Split the INFILE and CFILE in 100,000 chunks
  rm ${INFILE}.split.* ${COFILE}.split.*
  split -d -l 100000 ${INFILE} ${INFILE}.split. 
  split -d -l 100000 ${COFILE} ${COFILE}.split. 

  NSPLITS=`ls ${INFILE}.split.*|wc -l`
  echo "We have ${NSPLITS} chunks to process"
  for(( c=0; c<${NSPLITS}; c++ )) 
  do
    # Interpolate data
    echo "Gap-filling file: ${INFILE}.split.`printf "%02d" "${c}"`"
    python interp_and_smooth.py -f --infile ${INFILE}.split.`printf "%02d" "${c}"` --outfile ${OUFILE}/${STATE}_biweekly_timeseries.split.`printf "%02d" "${c}"` --cfile ${COFILE}.split.`printf "%02d" "${c}"` --syear ${SYEAR} --eyear ${EYEAR} --percentile 5 --step "biweekly" & 
  done
  wait

  for(( c=0; c<${NSPLITS}; c++ ))
  do
    # Smooth data
    echo "Smoothing file: ${INFILE}.split.`printf "%02d" "${c}"`.interp"
    python interp_and_smooth.py -s --infile "${INFILE}.split.`printf "%02d" "${c}"`.interp" --outfile ${OUFILE}/${STATE}_biweekly_timeseries.split.`printf "%02d" "${c}"` --syear ${SYEAR} --eyear ${EYEAR} &
  done
  wait

  for(( c=0; c<${NSPLITS}; c++ ))
  do
    # Rename .coords file
    mv ${OUFILE}/${STATE}_biweekly_timeseries.coords.split.`printf "%02d" ${c}` ${OUFILE}/${STATE}_biweekly_timeseries.split.`printf "%02d" ${c}`.coords
  done
  wait

done

echo "Add tasks finished.. exiting"
