# -*- coding: utf-8 -*-
"""
Created on Tue Mar 26 16:26:19 2019

@author: Dustin
"""

# JUST KNOX STUFF




# Some fairly standard modules
import os, csv, lzma
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import descartes
from itertools import product
from collections import Counter
import random

# The geopandas module does not come standard with anaconda,
# so you'll need to run the anaconda prompt as an administrator
# and install it via "conda install -c conda-forge geopandas".
# That installation will include pyproj and shapely automatically.
# These are useful modules for plotting geospatial data.
import geopandas as gpd
import pyproj
import shapely.geometry

# These modules are useful for tracking where modules are
# imported from, e.g., to check we're using our local edited
# versions of open_cp scripts.
import sys
import inspect
import importlib

# In order to use our local edited versions of open_cp
# scripts, we insert the parent directory of the current
# file ("..") at the start of our sys.path here.
sys.path.insert(0, os.path.abspath(".."))

# Elements from PredictCode's custom "open_cp" package
import open_cp
import open_cp.geometry
import open_cp.plot
import open_cp.sources.chicago as chicago
import open_cp.retrohotspot as retro
import open_cp.prohotspot as phs
import open_cp.knox






# Given a TimedPoints object that contains spatial coordinates paired
#  with timestamps, return a similar object that only contains the
#  data whose timestamps are within the given range
def getTimedPointsInTimeRange(points, start_time, end_time):
    return points[(points.timestamps >= start_time)
                  & (points.timestamps <= end_time)]



def getRegionCells(grid):
    # Make sure to do yextent then xextent, because cellcoords
    #  correspond to (row,col) in grid
    all_cells = product(range(grid.yextent), range(grid.xextent))
    return tuple(cc for cc in all_cells 
                 if not grid.mask[cc[0]][cc[1]])





def knox_ratio(statistic, distribution):
    """As in the paper, compute the ratio of the statistic to the median
    of the values in the distribution"""
    d = np.array(distribution)
    d.sort()
    return statistic / d[len(d)//2]




def all_ratios(result):
    for i, space_bin in enumerate(result.space_bins):
        for j, time_bin in enumerate(result.time_bins):
            yield knox_ratio(result.statistic(i,j), result.distribution(i,j))
            






"""
bin size
p value
diff btw time windows


"""


#Constants

# Heat-like color mapping
_cdict = {'red':   [(0.0,  1.0, 1.0),
                   (1.0,  1.0, 1.0)],
         'green': [(0.0,  1.0, 1.0),
                   (1.0,  0.0, 0.0)],
         'blue':  [(0.0,  0.2, 0.2),
                   (1.0,  0.2, 0.2)]}

yellow_to_red = matplotlib.colors.LinearSegmentedColormap("yellow_to_red", _cdict)


_day = np.timedelta64(1,"D")











num_knox_iterations = 100

datadir = os.path.join("..", "..", "Data")
chicago_file_name = "chicago_all_old.csv"
chicago_side = "South"
#crime_type_set = {"THEFT"}
crime_type_set = {"BURGLARY"}
chicago_file_path = os.path.join(datadir, chicago_file_name)
chicago.set_data_directory(datadir)





#start_train = np.datetime64("2018-03-01")
#end_train = np.datetime64("2018-06-01")

#start_train = np.datetime64("2011-03-01")
#end_train = np.datetime64("2012-01-07")
#start_test = np.datetime64("2012-02-01")
#end_test = np.datetime64("2012-03-01")



cell_width = 250
cell_height = cell_width



#points_crime = chicago.load(chicago_file_path, crime_type_set)
points_crime = chicago.load(chicago_file_path, crime_type_set, type="all")



### OBTAIN GRIDDED REGION

# Obtain polygon shapely object for region of interest
region_polygon = chicago.get_side(chicago_side)

# Obtain data set
points_crime_region = open_cp.geometry.intersect_timed_points(points_crime, region_polygon)

# Obtain grid with cells only overlaid on relevant region
masked_grid_region = open_cp.geometry.mask_grid_by_intersection(region_polygon, open_cp.data.Grid(xsize=cell_width, ysize=cell_height, xoffset=0, yoffset=0))

# Get a list/tuple of all cellcoords in the region
cellcoordlist_region = getRegionCells(masked_grid_region)

# Obtain number of cells in the grid that contain relevant geometry
# (i.e., not the full rectangular grid, only relevant cells)
num_cells_region = len(cellcoordlist_region)











time_windows = []
for start_year in range(2001,2018):
    start_jan = np.datetime64("{}-01-01".format(start_year))
    end_jan = np.datetime64("{}-01-01".format(start_year+1))
    start_jun = np.datetime64("{}-06-01".format(start_year))
    end_jun = np.datetime64("{}-06-01".format(start_year+1))
    time_windows.append((start_jan, end_jan))
    time_windows.append((start_jun, end_jun))

for time_window in time_windows:
    print(time_window)
    
    
    
    
    ### SELECT TRAINING DATA
    
    
    # Get subset of data for training
    points_crime_region_train = getTimedPointsInTimeRange(points_crime_region, 
                                                      time_window[0], 
                                                      time_window[1])
    
    
    
    
    
    print("Number of events: {}".format(len(points_crime_region_train.timestamps)))
    #sys.exit(0)
    
    
    
    knox = open_cp.knox.Knox()
    knox.set_time_bins([(i*7,i*7+7) for i in range(10)], unit="days")
    knox.space_bins = list( (i*100,i*100+100) for i in range(20) )
    knox.data = points_crime_region_train
    result = knox.calculate(iterations=num_knox_iterations)
    
    
    
    
    
    
    
    
    
    outfilebase = "knox_sschi_burg_cell{}_sbin{}_tbin{}_iter{}.txt".format(cell_width, 100, 7, num_knox_iterations)
    outfilename = os.path.join(datadir, outfilebase)
    
    with open(outfilename,"a") as fout:
        fout.write("\n")
        fout.write(str(time_window[0]))
        fout.write("\n")
        fout.write(str(time_window[1]))
        fout.write("\n")
        fout.write(str(len(points_crime_region_train.timestamps)))
        fout.write("\n")
        fout.write("p values\n")
        for i in range(len(result.space_bins)):
            fout.write(" ".join([str(result.pvalue(i,j)) for j in range(len(result.time_bins))]))
            fout.write("\n")
        fout.write("statistics\n")
        for i in range(len(result.space_bins)):
            fout.write(" ".join([str(result.statistic(i,j)) for j in range(len(result.time_bins))]))
            fout.write("\n")
        fout.write("distribution\n")
        for i in range(len(result.space_bins)):
            fout.write(" ".join([str(result.distribution(i,j)) for j in range(len(result.time_bins))]))
            fout.write("\n")
        fout.write("\n")
    
    
    
    
    
    
    
    
    """
    
    
    mappable = plt.cm.ScalarMappable(cmap=yellow_to_red)
    
    mappable.set_array(list(all_ratios(result)))
    mappable.autoscale()
    
    
    
    
    
    
    p_thresh_list = [0.10, 0.05, 0.01]
    
    for p_thresh in p_thresh_list:
        
        
        # !!! Add display of pvalues in a grid. Only need 1 grid per dataset,
        #  i.e., 1 per trio of p-thresholds
        
        
        
        fig, ax = plt.subplots(figsize=(16,4))
        
        xmin = min(x for x,y in result.space_bins)
        xmax = max(y for x,y in result.space_bins)
        ax.set(xlim=(xmin, xmax), xlabel="Distance in metres")
        
        _day = np.timedelta64(1,"D")
        ymin = min(t / _day for t,s in result.time_bins)
        ymax = max(s / _day for t,s in result.time_bins)
        ax.set(ylim=(ymin, ymax), ylabel="Time in days")
        
        
        ax.set_title("Knox, {} events from {} to {}, p={}".format(len(points_crime_region_train.timestamps), time_window[0], time_window[1], p_thresh))
        
        
        
        for i, space_bin in enumerate(result.space_bins):
            for j, time_bin in enumerate(result.time_bins):
                if result.pvalue(i,j) >= p_thresh:
                    continue
                ratio = knox_ratio(result.statistic(i,j), result.distribution(i,j))
                x, y = space_bin[0], time_bin[0] / _day
                width = space_bin[1] - space_bin[0]
                height = (time_bin[1] - time_bin[0]) / _day
                p = matplotlib.patches.Rectangle((x,y), width, height, fc=mappable.to_rgba(ratio))
                ax.add_patch(p)
                
        cbar = fig.colorbar(mappable, orientation="vertical")
        cbar.set_label("Knox ratio")
        
    """