# Tropical Phenology
Organized scripts commonly used during the tropical-phenology project

On Theseus:
```bash
# Create x number of Conda environments per GEE account
conda env create --name gee0 geemap, earthengine-api
conda env create --name gee1 geemap, earthengine-api
conda env create --name gee2 geemap, earthengine-api


# Authenticate each account if necessary
conda activate gee0
python
>>> ee.Authenticate()
exit
...
conda activate gee2
python
>>> ee.Authenticate()
exit


# Download GEE by country/state
screen -S download_amazonas_0-49 # Create screen session
conda activate gee0
python 1_export_sentinel_tiles.py
ctrl-A + D # Detach session
...
screen -S download_amazonas_100-149
conda activate gee2
ctrl-A + D


# Convert .tifs to one ASCII per tile
bash 2_create_ascii.sh
```

On Andes:
```bash
# Move data from theseus to Andes
scp  username@theseus.ornl.gov:/path/to/file `pwd`


# Edit slurm file, then submit .slurm to queue
vi 3_interp_ascii.slurm # Edit to run on 0-49 tiles
sbatch 3_interp_ascii.slurm

vi 3_interp_ascii.slurm # Edit to run on 50-99 tiles
sbatch 3_interp_ascii.slurm

vi 3_interp_ascii.slurm # Edit to run on 100-149 tiles
sbatch 3_interp_ascii.slurm
```

## Basic steps:
### On Theseus
1. Import GEE data 
  - requirements: ee, geemap, os, time, numpy
  - inputs: 
    - SITE (str),
    - STATE (str, -999),
    - GRIDSIZE (int),
    - IDX (int, -999),
    - STEP (int),
    - BIWEEKLY (0,1),
    - MONTHLY (0,1),
    - OUTPATH ( str path),
    - SDATE (int),
    - EDATE (int),
    - SCALE (int)
  - outputs:
    - `/path/to/directory/subdirectory/int.tif`
    
2. Create ASCII files and create missing .tifs
  - requirements: `GRASS 6.4.4` and `gdal_calc.py` (just download gdal for python)
  - inputs:
      - START (int),
      - END (int),
      - INPATH (path),
      - OUTPATH (path),
      - STEPS (int)
  - outputs:
    - `/path/to/directory/name_timeseries`
    - `/path/to/directory/name_timeseries.coords`
    
3. Move files to Andes

### On Andes
3. Interpolate and smooth data using parallel method and edit files as needed per submission
  - requirements: job.sh
  - inputs:
  - outputs:
