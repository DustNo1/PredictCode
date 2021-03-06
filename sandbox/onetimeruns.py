# -*- coding: utf-8 -*-
"""
Created on Fri Sep 27 15:25:58 2019

@author: lawdfo

onetimeruns.py

Purpose:
    Saving off one-time-use code in the event that it needs to be run again
    or possibly tweaked in the future, though this is currently unlikely.


"""

import os, sys, csv
import numpy as np
import open_cp
import open_cp.geometry
import open_cp.plot
import open_cp.sources.chicago as chicago
from crimeRiskTimeTools import getSixDigitDate


# Originally in genericDisplayData.py
def onetimeConfirmSameData(datadir, points_crime, crime_type_set):
    
    
    import os
    
    # This code just confirmed that the new method gets same data as the old
    chicago_file_name = "chi_all_s_BURGLARY_RES_010101_190101.csv"
    chicago_file_path = os.path.join(datadir, chicago_file_name)
    import open_cp.sources.chicago as chicago
    points_crime_chiorig = chicago.load(chicago_file_path, crime_type_set, 
                                type="all")
    pc_t = points_crime.timestamps
    pc_co_t = points_crime_chiorig.timestamps
    print(len(pc_t))
    print(len(pc_co_t))
    print(all(pc_t==pc_co_t))
    
    pc_x = points_crime.xcoords
    pc_y = points_crime.ycoords
    pc_co_x = points_crime_chiorig.xcoords
    pc_co_y = points_crime_chiorig.ycoords
    x_diff = []
    y_diff = []
    for i in range(len(pc_t)):
        x_diff.append(abs(pc_x[i]-pc_co_x[i]))
        y_diff.append(abs(pc_y[i]-pc_co_y[i]))
    x_diff = sorted(x_diff)
    y_diff = sorted(y_diff)
    print(x_diff[:10])
    print(x_diff[-10:])
    print(sum(x_diff)/len(pc_t))
    print(y_diff[:10])
    print(y_diff[-10:])
    print(sum(y_diff)/len(pc_t))
    



# Originally in genericDisplayData.py
def onetimeGeojsonManipulation(datadir):
    
    
    
    ###
    # Here's how a Chicago polygon was acquired:
    
    # Obtain polygon shapely object for South side
    #ss_polygon = chicago.get_side("South")
    
    
    
    import os
    import geopandas as gpd
    
    geojson_file_name = "durham.geojson"
    geojson_full_path = os.path.join(datadir, geojson_file_name)
    geo_frame_dur = gpd.read_file(geojson_full_path)
    
    
    geo_frame_chi = gpd.read_file(geojson_full_path)
    chicago_side_mapping = {
        "Far North" : [1,2,3,4,9,10,11,12,13,14,76,77],
        "Northwest" : [15,16,17,18,19,20],
        "North" : [5,6,7,21,22],
        "West" : list(range(23, 32)),
        "Central" : [8,32,33],
        "South" : list(range(34,44)) + [60, 69],
        "Southwest" : [56,57,58,59] + list(range(61,69)),
        "Far Southwest" : list(range(70,76)),
        "Far Southeast" : list(range(44,56))
    }
    geo_frame_chi["side"] = geo_frame_chi.area_numbe.map(lambda x : next(key
         for key, item in chicago_side_mapping.items() if int(x) in item) )
    _sides = geo_frame_chi.drop(["area", "area_num_1", "comarea", "comarea_id",
                        "perimeter", "shape_area", "shape_len"], axis=1)
    _sides.crs = {"init": "epsg:4326"} # global coordinate system
    _sides = _sides.to_crs({"init": "epsg:2790"}) # East Illinois-specifc
    
    ss_polygon = _sides[_sides.side == "South"].unary_union
    type(ss_polygon)
    
    
    
    
    # Obtain GeoDataFrame with polygon's geometry
    #  and with CRS epsg:2790
    ss_frame = gpd.GeoDataFrame({"name":["South Side"]})
    ss_frame.geometry = [ss_polygon]
    ss_frame.crs = {"init":"epsg:2790"}
    
    
    geojson_sschi_file_name = "Chicago_South_Side_2790.geojson"
    geojson_sschi_full_path = os.path.join(datadir, geojson_sschi_file_name)
    ss_frame.to_file(geojson_sschi_full_path, driver="GeoJSON")
    
    
    
    
    # Open GeoJSON file
    geojson_dur_file_name = "durham.geojson"
    geojson_dur_full_path = os.path.join(datadir, geojson_dur_file_name)
    geo_frame_dur = gpd.read_file(geojson_dur_full_path)
    
    # Remove unnecessary "Description" column
    geo_frame_dur_nodesc = geo_frame_dur.drop(["Description"], axis=1)
    # Set the name (we might not really need to do this)
    geo_frame_dur_nodesc.iloc[0]["Name"] = "Durham"
    # Transform data to UK-specific EPSG of 27700
    geo_frame_dur_nodesc = geo_frame_dur_nodesc.to_crs({"init": "epsg:27700"})
    
    # Save off new version of geodataframe into GeoJSON file
    geojson_dur_27_file_name = "Durham_27700.geojson"
    geojson_dur_27_full_path = os.path.join(datadir, geojson_dur_27_file_name)
    geo_frame_dur_nodesc.to_file(geojson_dur_27_full_path, driver="GeoJSON")
    
    
    
    """
    Given original file:
        Use ogr2ogr to convert to geojson if necessary
            For example, given durham.kml, use this command:
            > ogr2ogr -f GeoJSON durham.geojson durham.kml
        Use some code from above to read that geojson,
            form the union of certain subsets, if necessary
            convert from EPSG 4326 to a local EPSG (like 2790 or 27700)
            save it to a new geojson
        
    """


"""
Given original file:
    Use ogr2ogr to convert to geojson if necessary
        For example, given durham.kml, use this command:
        > ogr2ogr -f GeoJSON durham.geojson durham.kml
    Use the following function to read that geojson,
        form the union of certain subsets, if necessary
        convert from EPSG 4326 to a local EPSG (like 2790 or 27700)
        save it to a new geojson
    
"""
def convertGeojsonUKCounty(orig_geojson_path, 
                           county_name, 
                           new_geojson_path
                           ):
    
    #county_name = "Durham"
    
    
    import geopandas as gpd
    
    # Open GeoJSON file
    #geojson_file_name = "durham.geojson"
    #geojson_full_path = os.path.join(datadir, geojson_file_name)
    geo_frame = gpd.read_file(orig_geojson_path)
    
    # Remove unnecessary "Description" column
    geo_frame_nodesc = geo_frame.drop(["Description"], axis=1)
    # Set the name (this *might* not be required)
    geo_frame_nodesc.iloc[0]["Name"] = county_name
    # Transform data to UK-specific EPSG of 27700
    geo_frame_nodesc = geo_frame_nodesc.to_crs({"init": "epsg:27700"})
    
    # Save off new version of geodataframe into GeoJSON file
    #geojson_27_file_name = f"{county_name}_27700.geojson"
    #geojson_27_full_path = os.path.join(datadir, geojson_dur_27_file_name)
    geo_frame_nodesc.to_file(new_geojson_path, driver="GeoJSON")
    
    return






def saveCrimeSubsetCsv(infile, start_time, end_time, crime_list, loc_list=None, outfile=None, nrec=None, chicago_side=None):
    
    
    datadir = os.path.join("..", "..", "Data")
    chicago.set_data_directory(datadir)
    
    
    outdir = os.path.dirname(infile)
    if outfile == None:
        crime_str = "-".join(crime_list)
        if loc_list != None:
            crime_str += "_RES"
        chicago_side_short = "a"
        if chicago_side.upper() == "SOUTH":
            chicago_side_short = "s"
        outfilebase = "_".join(["chi", "all", chicago_side_short, crime_str, getSixDigitDate(start_time), getSixDigitDate(end_time)])
        if nrec != None:
            outfilebase += "_" + str(nrec)
        outfilebase += ".csv"
        outfile = os.path.join(outdir, outfilebase)
    print(outfile)
    row_ctr = 0
    with open(outfile, "w") as outf:
        outf_writer = csv.writer(outf, lineterminator='\n')
        
        
        
        # Obtain data as TimedPoints object, and corresponding csv rows
        points_crime, csv_rows, csv_header = chicago.load(infile, crime_list, type="all", withcsvrows=True)
        outf_writer.writerow(csv_header)
        points_csv_dict = dict(zip([tuple(p) for p in points_crime], csv_rows))
        
        # If a region of Chicago has been specified ("South"), do that here
        points_crime_region = points_crime
        if chicago_side != None:
            region_polygon = chicago.get_side(chicago_side)
            points_crime_region = open_cp.geometry.intersect_timed_points(points_crime, region_polygon)
        csv_rows_region = [points_csv_dict[tuple(p)] for p in points_crime_region]
        
        
        for row in csv_rows_region:
            if row[5] not in crime_list:
                print("Wait how'd that happen?")
                print(row)
                print(row[5])
                print(crime_list)
                sys.exit(1)
            
            if loc_list==None or row[7] in loc_list:
                
                
                row_m, row_d, row_y = row[2].split()[0].split("/")
                row_date = np.datetime64("-".join([row_y, row_m, row_d]))
                if start_time <= row_date and row_date < end_time:
                    outf_writer.writerow(row)
                    row_ctr += 1
                    if nrec != None and row_ctr >= nrec:
                        break
    print(f"Wrote header and {row_ctr} rows to {outfile}")
    return

def onetimemake2yrburglaryfile():
    datadir = os.path.join("..", "..", "Data")
    chicago_file_name = "chicago_all_old.csv"
    chicago_file_path = os.path.join(datadir, chicago_file_name)
    saveCrimeSubsetCsv(chicago_file_path, np.datetime64("2016-01-01"), np.datetime64("2018-01-01"), ["BURGLARY"])
    return

def onetimemakeburglaryfilenrecords(nrec):
    datadir = os.path.join("..", "..", "Data")
    chicago_file_name = "chicago_all_old.csv"
    chicago_file_path = os.path.join(datadir, chicago_file_name)
    saveCrimeSubsetCsv(chicago_file_path, np.datetime64("2016-01-01"), np.datetime64("2018-01-01"), ["BURGLARY"], nrec=nrec)
    return

def makeBurgSSXfile(dstart="2016-01-01", dend="2016-02-01", nrec=None):
    datadir = os.path.join("..", "..", "Data")
    chicago_file_name = "chicago_all_old.csv"
    chicago_file_path = os.path.join(datadir, chicago_file_name)
    saveCrimeSubsetCsv(chicago_file_path, np.datetime64(dstart), np.datetime64(dend), ["BURGLARY"], nrec=nrec, chicago_side="South")
    return

def makeBurgResSSXfile(dstart="2016-01-01", dend="2016-02-01", nrec=None):
    datadir = os.path.join("..", "..", "Data")
    chicago_file_name = "chicago_all_old.csv"
    chicago_file_path = os.path.join(datadir, chicago_file_name)
    saveCrimeSubsetCsv(chicago_file_path, np.datetime64(dstart), np.datetime64(dend), ["BURGLARY"], loc_list=["APARTMENT", "RESIDENCE", "RESIDENCE-GARAGE", "CHA APARTMENT"], nrec=nrec, chicago_side="South")
    return
