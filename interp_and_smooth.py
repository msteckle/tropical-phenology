import numpy as np
from scipy.signal import savgol_filter
import matplotlib.pyplot as plt
import csv
import matplotlib.dates as mdates
import datetime as dt
import matplotlib
import argparse
import math
import scipy.stats as stats

# Set backend
#matplotlib.use("Agg")

# Load ndres values
def readNDRE(pathfile):
	all_lines = []
	with open(pathfile, 'r', newline='\n') as txtfile:
		reader = csv.reader(txtfile, delimiter=' ')
		for row in reader:
			all_lines.append(row[2:])
	return list(all_lines)
	print("NDRE values read.")


def readCoords(cpathfile):
	all_coords = []
	with open(cpathfile, 'r', newline='\n') as coordfile:
		reader = csv.reader(coordfile, delimiter=' ')
		for row in reader:
			all_coords.append(row)
	return list(all_coords)
	print("Coordinate values read.")


# Determine if nan array and array are equal
def nan_equal(a,b):
	try:
		np.testing.assert_equal(a,b)
	except AssertionError:
		return False
	return True


# Not sure what this does
def nan_helper(y):
	return np.isnan(y), lambda z: z.nonzero()[0]


# Function to interpolate the time series
def interpolate_timeseries(infile, outfile, cfile, syear, eyear,
		percentile, step):
	""" 
	Function accepts in/out path(str), start/end years(int),
	percentile(int), and step=(biweekly or monthly) 
	Sets zeroes and outliers to nan
	Interpolates nans using np.interp()
	"""
	# Load dates
	start = str(syear) + "-01"
	end = str(eyear) + "-01"
	dates = np.arange(start, end, dtype='datetime64[M]')
	print("Dates created.")

	# Open files and create arrays
	ndre_2016to2019 = np.array(readNDRE(infile))
	print("Array length: " + str(len(ndre_2016to2019[0])))
	print(ndre_2016to2019[0])

	# Find 0 and set to np.nan
	ndre_2016to2019 = np.where(
		    ndre_2016to2019=='NA', 
			np.nan,
			ndre_2016to2019)
	ndre_2016to2019 = ndre_2016to2019.astype(np.float64)
	ndre_2016to2019 = np.where(
			ndre_2016to2019==0, 
			np.nan,
			ndre_2016to2019)
	print("Zeros set to np.nan")
	print("Array 1 with zeros to nan:\n" + str(ndre_2016to2019[0]))
		
	# Find outliers and set to np.nan
	p = percentile # Set bottom percentile
	out = outfile + ".orig"
	np.savetxt(out, ndre_2016to2019, delimiter=" ")	
	pc = np.nanpercentile(ndre_2016to2019, p, keepdims=True)
	ndre_2016to2019 = np.where(
			ndre_2016to2019 < pc, 
			np.nan, 
			ndre_2016to2019)
	print("Outliers set to np.nan.")
	print("Array 1 with outliers to nan:\n" + str(ndre_2016to2019[0]))

	# Add three values to front and back of arrays
	empty_list = []
	for lst in ndre_2016to2019:
		first3 = lst[:2]
		last3 = lst[-3:]
		n_lst = np.insert(lst, [0,1,2], last3)
		nn_lst = np.append(n_lst, first3)
		empty_list.append(nn_lst)
	ndre_2016to2019 = np.array(empty_list)
	print(len(ndre_2016to2019[0]))

	# Create nan array
	nan_array = np.empty(len(ndre_2016to2019[0]))
	nan_array.fill(np.nan)
	nan_array = np.array(nan_array)
	
	# Import coordinates
	coords = np.array(readCoords(cfile))
	print("Coordinates read")
	print(coords[0])

	# (1) Interpolate zeros and outliers
	new_array = []
	coord_array = []
	for obj,coord in zip(ndre_2016to2019, coords):
		equal_arrays = nan_equal(obj, nan_array)
		if equal_arrays == True:
			continue
		else:
			nans, x = nan_helper(obj)
			obj[nans] = np.interp(x(nans), x(~nans), obj[~nans])
			new_array.append(obj)
			coord_array.append(coord)

	coord_array = np.array(coord_array)

	# Remove first and last three values
	final_list = []
	for lst in new_array: 
		end = len(lst) - 2
		new_lst = lst[3:end]
		final_list.append(new_lst)
	print(len(final_list[0]))
	print("Final list: " + str(final_list[0]))     

	# Create annual baseline
	if step == 'biweekly':
		n = 25
	if step == 'monthly':
		n = 12
	temp = []
	for lst in final_list:
		annual = [lst[i:i+n] for i in range(0,len(lst),n)]
		annual = np.array(annual)
		an_med = (np.nanmedian(annual, axis=0)).tolist()
		temp.append(an_med)
	print("Baselines created.")
	print("Baseline 1:")
	print(temp[0])

	# Create annual baseline * 5
	t2 = []
	if step == 'biweekly':
		x = len(final_list[0]) // 25
		print(x)
	if step == 'monthly':
		x = len(final_list[0]) // 12
	for t in temp:
		t_full = t * x
		t2.append(t_full)

	# Check for outliers using z scores and replace
	z_arr = []
	for lst in final_list:
		z = stats.zscore(lst, nan_policy='omit')
		z_arr.append(z)

	final_arr = []
	for (zl, ol, ml) in zip(z_arr, final_list, t2):
		new_arr = []
		for i in range(0,len(zl)):
			if zl[i] > 0:
				ol[i] = ml[i]
				new_arr.append(ol[i])
			else:
				ol[i] = ol[i]
				new_arr.append(ol[i])
		final_arr.append(new_arr)
	new_arr = np.array(final_arr)
	new_arr[np.isnan(new_arr)] = 0

	out = outfile + ".interp"
	with open(out, "w", newline='\n') as of:
		writer = csv.writer(of, delimiter=' ')	
		writer.writerows(new_arr)
	print("New interpolated array:\n" + str(new_arr[0]))

	c_out = outfile + ".coords.1"
	with open(c_out, "w", newline='\n') as cf:
		writer = csv.writer(cf, delimiter=' ')
		writer.writerows(coord_array)
	print("New coordinate file exported.")

	# Close python
	# quit()	

def smooth_timeseries(infile, outfile, syear, eyear):
	print("Applying Savitsky-Golay Smoothing")
	# Load dates
	start = str(syear) + "-01"
	end = str(eyear) + "-12"
	dates = np.arange(start, end, dtype='datetime64[M]')

	# read interpolated data line by line and apply smoothing
	out = outfile + ".smooth"
	with open(out, "w") as smoothfile:
		swriter = csv.writer(smoothfile, delimiter=' ')
		with open(infile, "r") as interpfile:
			reader = csv.reader(interpfile, delimiter=' ')
			for row in reader:
				data = np.array(row, dtype=float)
				intdata = savgol_filter(data, 9, 3, mode='wrap')
				# window size 51, polynomial order 3
				swriter.writerow(intdata)

	# Exit python
	# quit()
	
###########################################################################################################
###########################################################################################################
if __name__ == "__main__":

	desc = """ Routine to fill/interpolate and smooth missing data in time series."""

	# parse args 
	parser = argparse.ArgumentParser(description=desc)
	parser.add_argument('-f', '--fill', dest="fill_ts", default=False,
		action='store_true', help='fill missing values in the time series with an interpolated value.')
	parser.add_argument('-s', '--smooth', dest="smooth_ts", default=False,
		action='store_true', help='apply Savitky-Golay filter to smooth the interpolated time series.')
	parser.add_argument('--infile', dest="infile",
		type=str, action='store', help='path to ascii data for interpolation.')
	parser.add_argument('--outfile', dest="outfile", 
		type=str, action='store', help='output path and name.')
	parser.add_argument('--cfile', dest="cfile", 
		type=str, action='store', help='path to corresponding ascii coordinates.')
	parser.add_argument('--syear', dest="syear", default=2017,
		type=int, action='store', help='start year [default=2016].')
	parser.add_argument('--eyear', dest="eyear", default=2021,
		type=int, action='store', help='end year [default=2019].')
	parser.add_argument('--percentile', dest="percentile", 
		type=int, action='store', help='percentile for removing outliers.')
	parser.add_argument('--step', dest="step", default="biweekly", 
		type=str, action='store', help='is data type biweekly or monthly.')

	# Execute the parse_args() method
	args = parser.parse_args()
	
	# Fill/Interpolate
	if args.fill_ts == True:
		interpolate_timeseries(args.infile, args.outfile, args.cfile,
			args.syear, args.eyear, args.percentile, args.step)
	
	# Apply Savitsky-Golay smoothing
	if args.smooth_ts == True:
		smooth_timeseries(args.infile, args.outfile, args.syear, args.eyear)	

