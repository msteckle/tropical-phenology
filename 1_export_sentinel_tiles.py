import ee, geemap, os, time
ee.Initialize()

# Line 97: change cloud filter parameters

# Set your stuff 
SITE='Brazil' #Country
STATE='Roraima' #State, -999
GRIDSIZE=40000 #km*1000
IDX=140 #-999 to skip this param
STEP=10
BIWEEKLY=1 
MONTHLY=0
OUTPATH='/mnt/locutus/remotesensing/6ru/sentinel_2/roraima' #Don't include final slash
SDATE=2017
EDATE=2020
SCALE=20

# Import admin data and select Amazonia to create grid around
if STATE != -999:
    br = (ee.FeatureCollection("FAO/GAUL/2015/level1")
            .filterMetadata('ADM0_NAME', 'equals', SITE)
            .filterMetadata('ADM1_NAME', 'equals', STATE)
      )
    print("Feature collection of {}, {}, loaded.".format(STATE, SITE))

else:
    br = (ee.FeatureCollection("FAO/GAUL/2015/level1")
            .filterMetadata('ADM0_NAME', 'equals', SITE))
    print("Feature collection of {} loaded.".format(SITE))

# Create grid
# https://developers.google.com/earth-engine/tutorials/community/drawing-tools
def make_grid(region, a_scale):
    """
    Creates a grid around a specified ROI.
    User inputs their reasonably small ROI.
    User inputs a scale where 100000 = 100km.
    """
    # Creates image with 2 bands ('longitude', 'latitude') in degrees
    lonLat = ee.Image.pixelLonLat()

    # Select bands, multiply times big number, and truncate
    lonGrid = (lonLat
               .select('latitude')
               .multiply(10000000)
               .toInt()
              )
    latGrid = (lonLat
              .select('longitude')
              .multiply(10000000)
              .toInt()
              )

    # Multiply lat and lon images and reduce to vectors
    grid = (lonGrid
            .multiply(latGrid)
            .reduceToVectors(
                geometry = region,
                scale = a_scale, # 100km-sized boxes needs 100,000
                geometryType = 'polygon')
           )
    
    return(grid)
    
    
# Make your grid superimposed over Amazonia and limit tiles to 100
grid_55km = make_grid(br, GRIDSIZE)

# Create dictionary of grid coordinates
grid_dict = grid_55km.getInfo()
feats = grid_dict['features']
coord_list = []
for d in feats:
    geom = d['geometry']
    coords = geom['coordinates']
    coord_list.append(coords)
    
    
# Create a list of several ee.Geometry.Polygons
polys = []
for coord in coord_list:
    poly = ee.Geometry.Polygon(coord)
    polys.append(poly)
length = len(polys)
print("{} squares created.".format(length))


# Make grid smaller if it's huge
if IDX != -999:
	nex = IDX + STEP
	idx = list(range(IDX, nex))
	polys = [ polys[i] for i in idx]
length = len(polys)
print("{} squares selected for export.".format(length))

# Make the whole grid a feature collection for export purposes
grid = ee.FeatureCollection(polys)
num_km = GRIDSIZE / 1000
print("{} km grid created around {}, {}.".format(num_km, STATE, SITE))


# Set variables for cloud mask
AOI = grid
START_DATE = '{}-01-31'.format(SDATE)
END_DATE = '{}-12-31'.format(EDATE)
CLOUD_FILTER = 60
CLD_PRB_THRESH = 50
NIR_DRK_THRESH = 0.15
CLD_PRJ_DIST = 1
BUFFER = 50


# Create cloud and shadow mask definitions 
def get_s2_sr_cld_col(aoi, start_date, end_date):
    """Get Sentinel-2 data and join s2cloudless collection
    with Sentinel TOA data."""
    # Import and filter S2 TOA.
    s2_sr_col = (ee.ImageCollection('COPERNICUS/S2')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER))
        .sort('CLOUDY_PIXEL_PERCENTAGE', False))

    # Import and filter s2cloudless.
    s2_cloudless_col = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
        .filterBounds(aoi)
        .filterDate(start_date, end_date))

    # Join the filtered s2cloudless collection to the SR collection by the 'system:index' property.
    return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
        'primary': s2_sr_col,
        'secondary': s2_cloudless_col,
        'condition': ee.Filter.equals(**{
            'leftField': 'system:index',
            'rightField': 'system:index'
        })
    }))


def add_cloud_bands(img):
    """Create and add cloud bands."""
    # Get s2cloudless image, subset the probability band.
    cld_prb = ee.Image(img.get('s2cloudless')).select('probability')

    # Condition s2cloudless by the probability threshold value.
    is_cloud = cld_prb.gt(CLD_PRB_THRESH).rename('clouds')

    # Add the cloud probability layer and cloud mask as image bands.
    return img.addBands(ee.Image([cld_prb, is_cloud]))


def add_shadow_bands(img):
    """Create and add cloud shadow bands."""
    # Identify water pixels from the SCL band.
    #not_water = img.select('SCL').neq(6) <- this is for SR, not TOA
    not_water = img.normalizedDifference(['B3', 'B8']).rename('NDWI')
    not_water = not_water.select('NDWI')

    # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
    SR_BAND_SCALE = 1e4
    dark_pixels = img.select('B8').lt(NIR_DRK_THRESH*SR_BAND_SCALE).rename('dark_pixels')

    # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')));

    # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
    cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, CLD_PRJ_DIST*10)
        .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
        .select('distance')
        .mask()
        .rename('cloud_transform'))

    # Identify the intersection of dark pixels with cloud shadow projection.
    shadows = cld_proj.multiply(dark_pixels).rename('shadows')

    # Add dark pixels, cloud projection, and identified shadows as image bands.
    return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))


def add_cld_shdw_mask(img):
    """Use cloud shadow and shadow bands to create masks."""
    # Add cloud component bands.
    img_cloud = add_cloud_bands(img)

    # Add cloud shadow component bands.
    img_cloud_shadow = add_shadow_bands(img_cloud)

    # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
    is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)

    # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
    # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
    is_cld_shdw = (is_cld_shdw.focal_min(2).focal_max(BUFFER*2/20)
        .reproject(**{'crs': img.select([0]).projection(), 'scale': 20})
        .rename('cloudmask'))

    # Add the final cloud-shadow mask to the image.
    return img_cloud_shadow.addBands(is_cld_shdw)


def apply_cld_shdw_mask(img):
    """Mask cloudy pixels."""
    # Subset the cloudmask band and invert it so clouds/shadow are 0, else 1.
    not_cld_shdw = img.select('cloudmask').Not()

    # Subset reflectance bands and update their masks, return the result.
    return img.select('B.*').updateMask(not_cld_shdw)
    

# Apply the cloud mask
s2_sr_cld_col = get_s2_sr_cld_col(AOI, START_DATE, END_DATE)
s2_sr = (s2_sr_cld_col
         .map(add_cld_shdw_mask)
         .map(apply_cld_shdw_mask))
print("Shadow mask applied to tiles.")
      

# Calculate NDRE
def ndre_band(img):
    """Function to calculate ndre for an image."""
    ndre = img.normalizedDifference(['B8', 'B5']).rename('NDRE')
    return img.addBands(ndre)


# Apply NDRE function and select only the NDRE band for export
mskd_col = s2_sr.select('B5', 'B8')
calc_ndre_mskd_imgs = mskd_col.map(ndre_band)
ndre_mskd_col = calc_ndre_mskd_imgs.select('NDRE')


# Clip NDRE images to grid squares
clipped_cols = []
for poly in polys:
    ndre_col = ndre_mskd_col
    clipped_col = ndre_col.map(lambda image: image.clip(poly))
    clipped_cols.append(clipped_col)
print("NDRE clipped to tiles.")
      

#Monthly step
#https://gis.stackexchange.com/questions/301165/how-to-get-monthly-averages-from-earth-engine-in-the-python-api
if MONTHLY == 1:
    months = ee.List.sequence(1, 12)
    years = ee.List.sequence(SDATE, EDATE)

    all_cols = []
    for a_col in clipped_cols:
        def byYear(y):
            def byMonth(m):
                return (a_col
                        .filter(ee.Filter.calendarRange(y, y, 'year'))
                        .filter(ee.Filter.calendarRange(m, m, 'month'))
                        .median() # Find max NDRE for a month
                        .set('month', m)
                        .set('year', y)
                       )
            return months.map(byMonth)

        col = ee.ImageCollection.fromImages(years.map(byYear).flatten())
        all_cols.append(col)
    print("Monthly step created.")
    choice = 'monthly'

if BIWEEKLY == 1:
    years = ee.List.sequence(SDATE, EDATE)
    step = ee.List.sequence(1, 365, 15)

    all_cols = []
    for a_col in clipped_cols:
        def byYear(y):
            y = ee.Number(y)
            def byStep(d):
                d = ee.Number(d)
                return (a_col
                        .filter(ee.Filter.calendarRange(y, y, 'year')) #yearly step
                        .filter(ee.Filter.calendarRange(d, d.add(14), 'day_of_year')) #15-day step
                        .max()
                        .set('step', [d, y])) #Add properties

            return step.map(byStep)

        col = ee.ImageCollection.fromImages(years.map(byYear).flatten())
        all_cols.append(col)
    print("Biweekly (15-day) step created.")
    choice = 'biweekly'  

# Make a list of file names
if STATE != -999:
    NOI = STATE
else:
	NOI = SITE

tiles = []
sitename = NOI.lower()
sitename = sitename.replace(" ", "_")
for num in range(IDX,nex):
    index = str(sitename + '_{}_{}'.format(choice, num))
    tiles.append(index)
print("Files to be created:\n" + str(tiles))
      
# Predict number of images in a timestep
if choice == 'biweekly':
	num_imgs = 25 * (EDATE - SDATE + 1)

if choice == 'monthly':
	num_imgs = 12 * (EDATE - SDATE + 1)

# Export images from a collection
tic1 = time.time()
for a_col, a_tile, poly in zip(all_cols, tiles, polys):
    ilist = a_col.toList(a_col.size())
    for i in range(0, num_imgs):
        filename = "{}/{}_{}/{}/{}.tif".format(
                OUTPATH, 
                sitename,
                choice, 
                a_tile,
                i)
        temp_dir = "{}/{}_{}/{}/".format(
                OUTPATH, 
                sitename, 
                choice, 
                a_tile)
        if not os.path.exists(temp_dir):
            os.mkdir(temp_dir)
        if os.path.exists(filename):
            print("Image {} already exists. Skipping...".format(i))
            continue
        try:
            tic = time.time()
            print("Exporting Image %d"%(i))
            geemap.ee_export_image(ee.Image(ilist.get(i)).select('NDRE'), 
                                   filename=filename, 
                                   scale=SCALE, 
                                   region=poly, 
                                   file_per_band=False)
            toc = time.time()
            hours, rem = divmod(toc-tic, 3600)
            mins, secs = divmod(rem, 60)
            print("Time elapsed: {:0>2}:{:0>2}:{:05.2f}"
                  .format(int(hours),int(mins),secs))
            
        except Exception:
            print("Error raised. Skipping image {}.".format(i))
            pass

toc1 = time.time()
hrs1, rem1 = divmod(toc1-tic1, 3600)
mins1, secs1 = divmod(rem1,  60)
print("Total time elapsed: {:0>2}:{:0>2}:{:05.2f}"
      .format(int(hrs1),int(mins1),secs1))
