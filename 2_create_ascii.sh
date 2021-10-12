#!/bin/bash
# This script generates ASCII files in the format <state_step_num>
# INPATH accepts <state_step>; will add on <_num> later

START=75 #first tile
END=98 #last tile
INPATH=/mnt/locutus/remotesensing/6ru/sentinel_2/acre/acre_biweekly
OUTPATH=/mnt/locutus/remotesensing/6ru/sentinel_2/acre/acre_biweekly_ascii
STEPS=100 #total number of steps (i.e. 0-99 is 100 steps)

for(( j=$START; j<=$END; j++ ))
do

	o=${OUTPATH}

	echo "Working in ${INPATH}"
	dire="$(basename -- $INPATH)"

	b=${INPATH}/${dire}_${j}
	tile="$(basename -- $b)"
	echo "Working on tile ${b}"

	# Find missing tifs and append names to array
	echo "Finding missing tifs."
	myArr=()
	for(( i=0; i<=$(($STEPS-1)); i++ ))
	do
		if [ -f "${b}/${i}.tif" ]
		then
			continue
		else
			echo "${i}.tif is missing."
			myArr+=(${i})
		fi
	done
	
	# Create dummy tifs from previous array
	echo "Creating dummy tifs."
	for val in "${myArr[@]}"
	do
		files=( ${b}/*.tif )
		gdal_calc.py -A "${files[0]}" --outfile="${b}/${val}.tif" --calc="A*0" --NoDataValue=0
		echo "Created dummy ${tile}/${val}.tif"
	done

	# Import into grass
	echo "Importing into GRASS."
	for(( i=0; i<=$(($STEPS-1)); i++ ))
	do
		r.in.gdal -e input="${b}/${i}.tif" output="${tile}_${i}"

	done

	# Export stack
	echo "Exporting 0-$(($STEPS-1)) stack."
	g.region rast=${tile}_65
	r.stats -1g input=$(g.mlist rast sep=, pat="${tile}_*") \
					   output="${o}/${tile}_timeseries" \
					   fs=space \
					   nv=0
	
	# Separate coords and data
	awk '{print $1" "$2}' ${o}/${tile}_timeseries \
		> ${o}/${tile}_timeseries.coords
	echo "Created coordinate file: ${o}/${tile}_timeseries.coords"

	awk '{$1=$2=""}1' ${o}/${tile}_timeseries \
		> ${o}/${tile}_timeseries.tmp

	# Remove leading spaces
	awk '{$1=$1}1' ${o}/${tile}_timeseries.tmp > ${o}/${tile}_timeseries
	rm ${o}/${tile}_timeseries.tmp
	echo "Created stack for interpolation: ${o}/${tile}_timeseries"

	# Remove from grass
	g.mremove -f rast="${tile}_*"

done
