#!/bin/bash
#SBATCH -A cli137 
#SBATCH -J roraima_60-69
#SBATCH -N 1
#SBATCH -t 1:30:00
#SBATCH --mail-type=FAIL
#SBATCH --mail-type=END
#SBATCH --mail-user=msteckle@vols.utk.edu
#SBATCH --get-user-env
#SBATCH --mem=0

cd $SLURM_SUBMIT_DIR
date

source $HOME/.bashrc
conda activate interp

S=60
F=69
STATE=roraima
SYEAR=2017
EYEAR=2021 #Final year plus one
DATA_LOC=/gpfs/alpine/cli137/proj-shared/6ru/${STATE}_data

for(( t=${S}; t<=${F}; t++ ))
do
	
  # Set coordinate and timeseries file paths
  echo "Start interpolation for tile ${t}"
  FILE=${STATE}_biweekly_${t}_timeseries
  INFILE=${DATA_LOC}/${STATE}_biweekly_ascii/${FILE}
  COFILE=${DATA_LOC}/${STATE}_biweekly_ascii/${FILE}.coords
  OUFILE=${DATA_LOC}/${STATE}_biweekly/${STATE}_biweekly_${t}


  # Create outfile subdirectories
  mkdir ${OUFILE}

  # Split the INFILE and CFILE in 100,000 chunks
  rm ${OUFILE}/${FILE}.split.* ${OUFILE}/${FILE}.coords.split.*
  split -d -l 100000 ${INFILE} ${OUFILE}/${FILE}.split. 
  split -d -l 100000 ${COFILE} ${OUFILE}/${FILE}.coords.split. 

  NSPLITS=`ls ${OUFILE}/${FILE}.split.*|wc -l`
  echo "We have ${NSPLITS} chunks to process"
  for(( c=0; c<${NSPLITS}; c++ )) 
  do
    # Interpolate data
    echo "Gap-filling file: ${OUFILE}/${FILE}.split.`printf "%02d" "${c}"`"
    python interp_and_smooth.py -f \
	    --infile ${OUFILE}/${FILE}.split.`printf "%02d" "${c}"` \
	    --outfile ${OUFILE}/${FILE}.split.`printf "%02d" "${c}"` \
	    --cfile ${OUFILE}/${FILE}.coords.split.`printf "%02d" "${c}"` \
	    --syear ${SYEAR} \
	    --eyear ${EYEAR} \
	    --percentile 5 \
	    --step "biweekly" & 
  done
  wait

  for(( c=0; c<${NSPLITS}; c++ ))
  do
    # Smooth data
    echo "Smoothing file: ${OUFILE}/${FILE}.split.`printf "%02d" "${c}"`.interp"
    python interp_and_smooth.py -s \
	    --infile "${OUFILE}/${FILE}.split.`printf "%02d" "${c}"`.interp" \
	    --outfile ${OUFILE}/${FILE}.split.`printf "%02d" "${c}"` \
	    --syear ${SYEAR} \
	    --eyear ${EYEAR} &
  done
  wait

  for(( c=0; c<${NSPLITS}; c++ ))
  do
    # Rename .coords file
    mv ${OUFILE}/${FILE}.coords.split.`printf "%02d" ${c}` ${OUFILE}/${FILE}.split.`printf "%02d" ${c}`.coords
  done
  wait

done

echo "Add tasks finished.. exiting"
