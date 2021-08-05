#!/bin/bash
# This script generates ASCII files in the format <state_step_num>
# INPATH accepts <state_step>; will add on <_num> later

START=0 #first tile
END=5 #last tile
INPATH=/mnt/locutus/remotesensing/6ru/era/amazonas_precip/amazonas_precip
OUTPATH=/mnt/locutus/remotesensing/6ru/era/era_ascii/amazonas_precip_ascii
STEPS=100 #total number of steps (i.e. 0-99 is 100 steps)

for(( j=$START; j<=$END; j++ ))
do

	b=${INPATH}_${j}
	o=${OUTPATH}

	echo "Working in ${b}"
	dire="$(basename -- $b)"
	echo "${dire}"

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
		echo "Created dummy ${dire}/${val}.tif"
	done

	# Import into grass
	echo "Importing into GRASS."
	for(( i=0; i<=$(($STEPS-1)); i++ ))
	do
		r.in.gdal -e input="${b}/${i}.tif" output="${dire}_${i}"

	done

	# Export stack
	echo "Exporting 0-$(($STEPS-1)) stack."
	g.region rast=${dire}_65
	r.stats -1g input=$(g.mlist rast sep=, pat="${dire}_*") \
					   output="${o}/${dire}_timeseries" \
					   fs=space \
					   nv=0
	
	# Separate coords and data
	awk '{print $1" "$2}' ${o}/${dire}_timeseries \
		> ${o}/${dire}_timeseries.coords
	echo "Created coordinate file: ${o}/${dire}_timeseries.coords"

	awk '{$1=$2=""}1' ${o}/${dire}_timeseries \
		> ${o}/${dire}_timeseries.tmp \
		&& mv ${o}/${dire}_timeseries.tmp ${o}/${dire}_timeseries
	echo "Created stack for interpolation: ${o}/${dire}_timeseries"

	# Remove from grass
	g.mremove -f rast="${dire}_*"

done
