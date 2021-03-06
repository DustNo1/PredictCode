# -*- coding: utf-8 -*-
"""
Created on Thu Mar 14 14:37:28 2019

@author: Dustin
"""

# Some fairly standard modules
import os, csv, lzma
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import descartes
from itertools import product
from collections import Counter
import random
import time

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



from crimeRiskTimeTools import generateDateRange, \
                                generateLaterDate, \
                                generateEarlierDate, \
                                getTimedPointsInTimeRange




# Given a TimedPoints object and a Grid (MaskedGrid?) object,
#  return a Counter object that is a mapping from the grid cell
#  coordinates to the number of points within the cell.
#  Note that "grid cell coordinates" refers to which row of cells
#  and which column of cells it's located at, NOT spatial coords.
def countPointsPerCell(points, grid):
    # Get xy coords from TimedPoints
    xcoords, ycoords = points.xcoords, points.ycoords
    # Convert coords to cellcoords
    xgridinds = np.floor((xcoords - grid.xoffset) / grid.xsize).astype(np.int)
    ygridinds = np.floor((ycoords - grid.yoffset) / grid.ysize).astype(np.int)
    # Count the number of crimes per cell
    # NOTE: We do (y,x) instead of (x,y) because cells are (row,col)!!!
    return Counter(zip(ygridinds, xgridinds))


# Given a sorted list of cells, and a mapping from cells to number of events
#  in those cells, return a list of numbers, of length equal to the given
#  list of cells, representing the running total of number of events in all
#  cells up to that point in the list.
def getHitRateList(sorted_cells, cell_hit_map):
    running_total = 0
    hit_rate_list = []
    for cell in sorted_cells:
        running_total += cell_hit_map[cell]
        hit_rate_list.append(running_total)
    return hit_rate_list


def sortCellsByRiskMatrix(cells, risk_matrix):
    # For each cellcoord, get its risk from the risk matrix
    cellcoord_risk_dict = dict()
    for cc in cells:
        cellcoord_risk_dict[cc] = risk_matrix[cc[0]][cc[1]]
    
    # Sort cellcoords by risk, highest risk first
    cells_risksort = sorted(cells, key=lambda x:cellcoord_risk_dict[x], 
                            reverse=True)
    return cells_risksort



def getRegionCells(grid):
    # Make sure to do yextent then xextent, because cellcoords
    #  correspond to (row,col) in grid
    all_cells = product(range(grid.yextent), range(grid.xextent))
    return tuple(cc for cc in all_cells 
                 if not grid.mask[cc[0]][cc[1]])



# Construct a "random" model by simply randomly sorting the cells
def RandomlySortCells(cells, seed=None):
    if seed != None:
        random.seed(seed)
    cell_list = list(cells)
    random.shuffle(cell_list)
    return cell_list



def runRhsModel(training_data, grid, bandwidth=250, rand_seed=None):
    # Set RNG seed if given
    if rand_seed != None:
        np.random.seed(rand_seed)
    
    grid_cells = getRegionCells(grid)
    
    # Obtain model and prediction on grid cells
    rhs_pred = retro.RetroHotSpot()
    rhs_pred.data = training_data
    rhs_pred.weight = retro.Quartic(bandwidth = bandwidth)
    rhs_risk = rhs_pred.predict()
    rhs_grid_risk = open_cp.predictors.grid_prediction(rhs_risk, grid)
    rhs_grid_risk_matrix = rhs_grid_risk.intensity_matrix
    
    
    #print("rhs_risk")
    #print(type(rhs_risk))
    #print("grid")
    #print(type(grid))
    #print("rhs_grid_risk")
    #print(type(rhs_grid_risk))
    
    
    
    
    
    # Sort cellcoords by risk in intensity matrix, highest risk first
    return sortCellsByRiskMatrix(grid_cells, rhs_grid_risk_matrix)
    

def averageRhsModels(training_data, grid, bandwidth=250, num_runs=1, \
                     rand_seed_list = None):
    
    # 
    
    if rand_seed_list == None:
        rand_seed_list = range(num_runs)
    else:
        num_runs = len(rand_seed_list)
    
    
    grid_cells = getRegionCells(grid)
    
    
    
    
    # Obtain model and prediction on grid cells
    rhs_pred = retro.RetroHotSpot()
    rhs_pred.data = training_data
    rhs_pred.weight = retro.Quartic(bandwidth = bandwidth)
    
    
    rhs_risk = rhs_pred.predict()
    
    matrix_collection = []
    for rand_seed in rand_seed_list:
        np.random.seed(rand_seed)
        rhs_grid_risk = open_cp.predictors.grid_prediction(rhs_risk, grid)
        rhs_grid_risk_matrix = rhs_grid_risk.intensity_matrix
        matrix_collection.append(rhs_grid_risk_matrix)
    
    master_matrix = sum(matrix_collection)
    
    for m in matrix_collection:
        print(m[12:20,12:20])
    print(master_matrix[12:20,12:20])
    
    for m in matrix_collection:
        print(sortCellsByRiskMatrix(grid_cells, m)[:8])
    print(sortCellsByRiskMatrix(grid_cells, master_matrix)[:8])
    sys.exit(0)
    
    # Sort cellcoords by risk in intensity matrix, highest risk first
    return sortCellsByRiskMatrix(grid_cells, master_matrix)



















def knox_ratio(statistic, distribution):
    # From "Examples/Chicago Case Study/Knox Statistics" notebook
    # Compute the ratio of the statistic to the 
    #  median of the values in the distribution
    d = np.array(distribution)
    d.sort()
    return statistic / d[len(d)//2]



def all_knox_ratios(result):
    for i, space_bin in enumerate(result.space_bins):
        for j, time_bin in enumerate(result.time_bins):
            yield knox_ratio(result.statistic(i,j), result.distribution(i,j))









def runPhsModel(training_data, grid, time_unit, dist_unit, time_bandwidth, dist_bandwidth, epsilon=0.1):
    
    
    
    
    
    grid_cells = getRegionCells(grid=grid)
    
    # Obtain model and prediction on grid cells
    phs_predictor = phs.ProspectiveHotSpot(grid=grid)
    phs_predictor.data = training_data
    
    dist_band_in_units = dist_bandwidth/dist_unit
    time_band_in_units = time_bandwidth/time_unit
    
    phs_predictor.weight = phs.ClassicWeightNormalised(space_bandwidth=dist_band_in_units, time_bandwidth=time_band_in_units)
    #phs_predictor.weight = phs.ClassicWeightNormalised(space_bandwidth=dist_band_in_units, time_bandwidth=time_band_in_units, epsilon=epsilon)
    
    phs_predictor.time_unit = time_unit
    phs_predictor.grid = dist_unit
    
    cutoff_time = sorted(training_data.timestamps)[-1] + _day
    
    phs_grid_risk = phs_predictor.predict(cutoff_time, cutoff_time)
    
    
    #print("phs_risk")
    #print(type(phs_risk))
    #print("grid")
    #print(type(grid))
    
    #sys.exit(0)
    
    
    
    #phs_grid_risk = open_cp.predictors.grid_prediction(phs_risk, grid)
    phs_grid_risk_matrix = phs_grid_risk.intensity_matrix
    
    # Sort cellcoords by risk in intensity matrix, highest risk first
    return sortCellsByRiskMatrix(grid_cells, phs_grid_risk_matrix)
    












def runNaiveCount_model(data_points, grid):
    crime_ctr = countPointsPerCell(data_points, grid)
    grid_cells = getRegionCells(grid)
    return sorted(grid_cells, key=lambda x:crime_ctr[x], reverse=True)




# Given a model name and relevant arguments,
#  return a sorted list of cells
def runModelAndSortCells(model_name, model_args):
    
    rec_models = ["ideal","random","naivecount","rhs","phs"]
    if model_name not in rec_models:
        print("Unrecognized model name: {}".format(model_name))
        sys.exit(1)
    
    
    
    if model_name=="ideal":
        # We need these variables:
        #   cellcoordlist_region
        #   cells_testcrime_ctr
        
        cellcoordlist_region, cells_testcrime_ctr = model_args
        
        return sorted(cellcoordlist_region, 
                                         key=lambda x:cells_testcrime_ctr[x], 
                                         reverse=True)
        
    if model_name=="random":
        # We need these variables:
        #   cellcoordlist_region
        #   plot_random_seed
        
        cellcoordlist_region, plot_random_seed = model_args
        
        return RandomlySortCells(cellcoordlist_region, seed=plot_random_seed)
        
        
    
    points_crime_region_train = model_args[0]
    masked_grid_region = model_args[1]
    other_model_args = model_args[2:]
    
    if model_name=="naivecount":
        # We need these variables:
        #   points_crime_region_train
        #   masked_grid_region
        
        return runNaiveCount_model(points_crime_region_train, masked_grid_region)
        
    
    
    if model_name=="rhs":
        # We need these variables:
        #   points_crime_region_train
        #   masked_grid_region
        #   rhs_bandwidth
        #   rhs_random_seed
        
        rhs_bandwidth, rhs_random_seed = other_model_args
        
        return runRhsModel(points_crime_region_train,
                                                   masked_grid_region, 
                                                   bandwidth = rhs_bandwidth, 
                                                   rand_seed=rhs_random_seed)
    
    if model_name=="phs":
        # We need these variables:
        #   points_crime_region_train
        #   masked_grid_region
        #   time_unit
        #   time_bandwidth
        #   dist_unit
        #   dist_bandwidth
        #   epsilon # or option to choose Linear vs Classic?
        
        time_unit, time_bandwidth, dist_unit, dist_bandwidth, epsilon = other_model_args
        
        
        #time_unit = np.timedelta64(1, "W")
        #time_bandwidth = np.timedelta64(4, "W")
        #dist_unit = 100
        #dist_bandwidth = 500
        #epsilon = 0.1
        
        
        return runPhsModel(
                training_data = points_crime_region_train, 
                grid = masked_grid_region, 
                time_unit = time_unit, 
                dist_unit = dist_unit, 
                time_bandwidth = time_bandwidth, 
                dist_bandwidth = dist_bandwidth, 
                epsilon = epsilon)
        
        
        
    
    
    
    









# START TIMER
init_start_time = time.time()



# PARAMETERS

# Data parameters
print("Declaring parameters...")
datadir = os.path.join("..", "..", "Data")
chicago_file_name = "chicago_all_old.csv"
chicago_side = "South"
crime_type_set = {"BURGLARY"}
chicago_load_type = "snapshot"
if "all" in chicago_file_name:
    chicago_load_type = "all"
chicago_file_path = os.path.join(datadir, chicago_file_name)
# Chicago module requires this line to access some data
chicago.set_data_directory(datadir)



# Time parameters

#start_train = np.datetime64("2018-03-01")
#end_train = np.datetime64("2018-06-01")
#start_test = np.datetime64("2018-06-01")
#end_test = np.datetime64("2018-08-01")

#start_train = np.datetime64("2011-03-01")
#end_train = np.datetime64("2012-01-07")
#start_test = np.datetime64("2012-02-01")
#end_test = np.datetime64("2012-03-01")


# Spatial model parameters
cell_width = 250
cell_height = cell_width
cell_sampling = 15 #!!! need to find where to use this
rhs_bandwidth = 300 # 1000 is in Matt's code; in practice, smaller works better


# Choice of models to plot
plot_expected_random = False
plot_ideal = True
plot_random = True
plot_naive_count = True
plot_rhs = True
plot_rhs_avg = False
rhs_num = 1
rhs_band_step = cell_width
plot_phs = True

plot_random_seed = 1

# Knox statistic parameters
knox_space_bin_size = 100
knox_space_bin_count = 5
knox_space_bins = [(i*knox_space_bin_size,(i+1)*knox_space_bin_size) \
                   for i in range(knox_space_bin_count)]
#print(knox_space_bins)
knox_time_bin_size = 3
knox_time_bin_count = 7
knox_time_bins = [(i*knox_time_bin_size,(i+1)*knox_time_bin_size) \
                  for i in range(knox_time_bin_count)]
#print(knox_time_bins)


print("...declared parameters.")









### OBTAIN FULL DATA
print("Obtaining full data...")
obtain_data_start_time = time.time()
points_crime = chicago.load(chicago_file_path, crime_type_set, 
                            type=chicago_load_type)
obtain_data_end_time = time.time()
print("...obtained full data.")
print("Time: {}".format(obtain_data_end_time - obtain_data_start_time))




### OBTAIN GRIDDED REGION
print("Obtaining region...")
obtain_reg_start_time = time.time()

# Obtain polygon shapely object for region of interest
region_polygon = chicago.get_side(chicago_side)

# Obtain data set within relevant region
points_crime_region = open_cp.geometry.intersect_timed_points(points_crime, 
                                                              region_polygon)

# Obtain grid with cells only overlaid on relevant region
masked_grid_region = open_cp.geometry.mask_grid_by_intersection(region_polygon, open_cp.data.Grid(xsize=cell_width, ysize=cell_height, xoffset=0, yoffset=0))

# Get a list/tuple of all cellcoords in the region
cellcoordlist_region = getRegionCells(masked_grid_region)

# Obtain number of cells in the grid that contain relevant geometry
# (i.e., not the full rectangular grid, only relevant cells)
num_cells_region = len(cellcoordlist_region)

obtain_reg_end_time = time.time()
print("...obtained region.")
print("Time: {}".format(obtain_reg_end_time - obtain_reg_start_time))












train_len = "4W"
test_len = "1D"

all_exp_results = []
test_data_counts = []
test_data_dates = []
exp_times = []


start_test_list = generateDateRange("2018-01-01", "2018-02-01", "1D")


total_num_exp = len(start_test_list)
for exp_index, start_test in enumerate(start_test_list):
    
    exp_start_time = time.time()
    
    if exp_index % 10 == 0:
        print("Running experiment {}/{}...".format(exp_index, total_num_exp))
    
    # Declare time ranges of training and testing data
    end_train = start_test
    start_train = generateEarlierDate(end_train, train_len)
    end_test = generateLaterDate(start_test, test_len)
    
    test_data_dates.append(start_test)
    
    
    #print(start_train, end_train, start_test, end_test)
    
    
    
    
    ### SELECT TRAINING DATA
    
    # Get subset of data for training
    points_crime_region_train = getTimedPointsInTimeRange(points_crime_region, 
                                                          start_train, 
                                                          end_train)
    
    #print(len(points_crime_region_train.timestamps))
    
    
    
    training_data=points_crime_region_train
    print(type(training_data))
    print(type(training_data.timestamps))
    print(len(training_data.timestamps))
    sd = sorted(training_data.timestamps)
    print(sd[0])
    print(sd[-1])
    #sys.exit(0)
    
    
    
    
    
    
    
    ### TESTING DATA, USED FOR EVALUATION
    
    # Obtain selection of data for testing
    points_crime_region_test = getTimedPointsInTimeRange(points_crime_region, 
                                                          start_test, 
                                                          end_test)
    # Count how many crimes there were in this test data set
    num_crimes_test = len(points_crime_region_test.timestamps)
    #print(num_crimes_test)
    
    # Count the number of crimes per cell
    cells_testcrime_ctr = countPointsPerCell(points_crime_region_test, 
                                             masked_grid_region)
    
    
    test_data_counts.append(num_crimes_test)
    
    
    
    
    #print(start_train, end_train, start_test, end_test, num_crimes_test)
    
    
    
    # Instantiate the list of sorted lists of cells based on different models
    cells_sorted_models = []
    
    
    ### IDEAL MODEL, CHEAT BY LOOKING AT TEST DATA AND CHOOSING BEST CELLS
    # Sort cellcoords by crimes in test data, most crimes first
    # This is the best possible order a model could choose, aka "oracle"
    if plot_ideal:
        cellcoordlist_sort_test = sorted(cellcoordlist_region, 
                                         key=lambda x:cells_testcrime_ctr[x], 
                                         reverse=True)
        cells_sorted_models.append((cellcoordlist_sort_test, "Ideal"))
    
    
    
    
    ### UNINTELLIGENT MODEL, JUST SORT CELLS COMPLETELY RANDOMLY
    if plot_random:
        cells_sorted_models.append(tuple( \
            [RandomlySortCells(cellcoordlist_region, seed=plot_random_seed), 
             "Random"] ))
    
    
    ### MOST BASIC MODEL, JUST COUNT CRIMES IN TRAINING DATA
    if plot_naive_count:
        cellcoordlist_sort_naive = runNaiveCount_model(points_crime_region_train,
                                                       masked_grid_region)
        cells_sorted_models.append(tuple([cellcoordlist_sort_naive, 
                                          "NaiveCount"]))
    
    
    
    
    
    
    
    ### CREATE RHS MODEL, RANK CELLS
    
    
    if plot_rhs:
        if rhs_num==None or rhs_num<1:
            rhs_num = 1
        for i in range(rhs_num):
            
            cellcoordlist_sort_rhs = runRhsModel(points_crime_region_train,
                                                   masked_grid_region, 
                                                   #bandwidth = (i+1)*rhs_band_step, 
                                                   bandwidth = rhs_bandwidth, 
                                                   rand_seed=i)
            
            cells_sorted_models.append(tuple([cellcoordlist_sort_rhs, 
                                             "RHS-seed{}".format(i)]))
    
    if plot_rhs_avg:
        
        cellcoordlist_sort_rhs = averageRhsModels(points_crime_region_train,
                                               masked_grid_region, 
                                               #bandwidth = (i+1)*rhs_band_step, 
                                               bandwidth = rhs_bandwidth, 
                                               num_runs = rhs_num)
        
        cells_sorted_models.append(tuple([cellcoordlist_sort_rhs, 
                                         "RHS-avg"]))
    
    
    
    ### CREATE PHS MODEL AROUND HERE
    
    
    if plot_phs:
        
        time_unit = np.timedelta64(1, "W")
        time_bandwidth = np.timedelta64(4, "W")
        
        dist_unit = 100
        dist_bandwidth = 500
        
        
        
        cellcoordlist_sort_phs = runPhsModel(
                training_data = points_crime_region_train, 
                grid = masked_grid_region, 
                time_unit = time_unit, 
                dist_unit = dist_unit, 
                time_bandwidth = time_bandwidth, 
                dist_bandwidth = dist_bandwidth, 
                epsilon = 0.1)
        
        cells_sorted_models.append(tuple([cellcoordlist_sort_phs, 
                                          "PHS_d{}-{}_t{}-{}".format(
                                                  dist_unit, 
                                                  dist_bandwidth, 
                                                  int(time_unit/_day), 
                                                  int(time_bandwidth/_day) )]))
        
        
    
    
    
    
    
    
    
    
    
    
    
    
    # Get hit rates based on cell sorts
    hit_rates_for_models = []
    for (cells_sorted, model_name) in cells_sorted_models:
        hit_rates_for_models.append( \
            [getHitRateList(cells_sorted, cells_testcrime_ctr), model_name] )
    
    # Save off hit rate results
    
    all_exp_results.append(hit_rates_for_models)
    
    
    exp_times.append(time.time() - exp_start_time)
    
    

exp_times_sorted = sorted(exp_times)
exp_times_total = sum(exp_times)
print("Total experiment time: {}".format(exp_times_total))
print("Average experiment time: {}".format(exp_times_total/len(exp_times)))
print("Min experiment time: {}".format(exp_times_sorted[0]))
print("Max experiment time: {}".format(exp_times_sorted[-1]))






if False:
    # Printing some bits of results, just to check what they look like
    #  and what data types they are
    print(len(all_exp_results))
    for i, exp in enumerate(all_exp_results):
        print(i)
        print(len(exp))
        for model_result in exp:
            print(model_result[1])
            print(len(model_result[0]))
            print(model_result[0][:20])
            print(np.array(model_result[0][:20])/test_data_counts[i])
        print("---")







### DECLARE FIGURE FOR HITRATE/COVERAGE

# !!! I should add an option for the x-axis of the figure!!!


results_count_offset = .025
results_rate_offset = .005
results_count_offset = 0
results_rate_offset = 0

# Declare figure
print("Declaring figure...")
fig, ax = plt.subplots(figsize=(12,6))


names_for_legend = []


#xcoords = test_data_dates

coverage_rate = 0.10
coverage_cell_index = int(num_cells_region * coverage_rate)-1
print("reg {}".format(num_cells_region))
print("cov {}".format(coverage_rate))
print("cci {}".format(coverage_cell_index))


result_matrix = np.zeros((len(all_exp_results[0]), len(all_exp_results)))
for exp_num, exp in enumerate(all_exp_results):
    for model_num, model_result in enumerate(exp):
        result_matrix[model_num, exp_num] = model_result[0][coverage_cell_index]

for row_num, row in enumerate(result_matrix):
    ax.plot(test_data_dates, row + (results_count_offset * row_num) )
    names_for_legend.append(all_exp_results[0][row_num][1])


#ax.legend(names_for_legend)
ax.tick_params(axis='x', rotation=90)






# Declare figure
print("Declaring figure...")
fig, ax = plt.subplots(figsize=(12,6))


names_for_legend = []


#xcoords = test_data_dates

coverage_rate = 0.10
coverage_cell_index = int(num_cells_region * coverage_rate)-1
print("reg {}".format(num_cells_region))
print("cov {}".format(coverage_rate))
print("cci {}".format(coverage_cell_index))

result_matrix = np.zeros((len(all_exp_results[0]), len(all_exp_results)))
for exp_num, exp in enumerate(all_exp_results):
    if test_data_counts[exp_num] == 0:
        continue
    for model_num, model_result in enumerate(exp):
        result_matrix[model_num, exp_num] = \
            model_result[0][coverage_cell_index]/test_data_counts[exp_num]

for row_num, row in enumerate(result_matrix):
    ax.plot(test_data_dates, row + (results_rate_offset * row_num) )
    names_for_legend.append(all_exp_results[0][row_num][1])


#ax.legend(names_for_legend)
ax.tick_params(axis='x', rotation=90)











print("Exiting here")
sys.exit(0)



### MORE ABOUT THE LINE GRAPHS

# Create list of x-coordinates that will be used by all models
coverage_xcoords = np.asarray(range(num_cells_region))/num_cells_region

# Plot a line equivalent to average expected amount of crime ecountered
#  when selecting cells randomly. This will just be a straight line
#  going from 0% at 0% coverage to 100% at 100% coverage



if plot_expected_random:
    ax.plot(coverage_xcoords, coverage_xcoords)
    names_for_legend.append("Expected random")


#cells_sorted_models = [cellcoordlist_sort_test, cellcoordlist_sort_rhs, cellcoordlist_sort_rand, cellcoordlist_sort_naive]
#cells_sorted_models = [cellcoordlist_sort_naive, *rhs_sorts]

for (cells_sorted, model_name) in cells_sorted_models:
    hit_rates = getHitRateList(cells_sorted, cells_testcrime_ctr)
    print("{}:\t{}".format(model_name,hit_rates[:10]))
    ax.plot(coverage_xcoords, np.asarray(hit_rates)/num_crimes_test)
    names_for_legend.append(model_name)

ax.legend(names_for_legend)







