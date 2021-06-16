#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  9 16:26:30 2021

@author: mike
"""
import os
import yaml
import numpy as np
import pandas as pd
from hilltoppy import web_service as ws
import requests
from time import sleep
# from sklearn.neighbors import LocalOutlierFactor

pd.options.display.max_columns = 10


###########################################################3
### Parameters

base_path = os.path.realpath(os.path.dirname(__file__))

with open(os.path.join(base_path, 'parameters.yml')) as param:
    param = yaml.safe_load(param)

mtypes = param['source']['mtypes']
base_url = param['source']['api_endpoint']
hts = param['source']['hts']
std_factor = param['source']['std_factor']
iqr_factor = param['source']['iqr_factor']

date1 = pd.Timestamp.now().round('s').isoformat()

stats_csv = 'summary_stats_{date}.csv'.format(date=date1)
std_csv = 'std_outliers_{date}.csv'.format(date=date1)
iqr_csv = 'iqr_outliers_{date}.csv'.format(date=date1)
dtl_csv = 'detection_limit_outliers_{date}.csv'.format(date=date1)
min_max_csv = 'min_max_outliers_{date}.csv'.format(date=date1)


###########################################################
### Helper functions


def get_stations(base_url, hts, mtype):
    """
    Function to get the stations/sites associated with a particular measurement type.

    Parameters
    ----------
    base_url : str
        The endpoint url for the Hilltop server.
    hts : str
        The hts "file" that is added to the end of the base_url.
    mtype : str
        The measurement type to query.

    Returns
    -------
    DataFrame

    """
    stns1 = ws.site_list(base_url, hts, location='LatLong') # There's a problem with Hilltop that requires running the site list without a measurement first...
    stns1 = ws.site_list(base_url, hts, location='LatLong', measurement=mtype)
    stns2 = stns1[(stns1.lat > -47.5) & (stns1.lat < -34) & (stns1.lon > 166) & (stns1.lon < 179)].dropna().copy()
    stns2.rename(columns={'SiteName': 'ref'}, inplace=True)

    return stns2


def get_results(base_url, hts, mtype, ref):
    """
    Function to get the time series results and associated stats from one or many sites associated with a particular measurement type.

    Parameters
    ----------
    base_url : str
        The endpoint url for the Hilltop server.
    hts : str
        The hts "file" that is added to the end of the base_url.
    mtype : str
        The measurement type to query.
    ref : str
        The reference id of the site.

    Returns
    -------
    Three DataFrames
        results, detection limits, and stats
    """
    ### Get data
    res_list = []
    for s in ref:
        timer = 5
        while timer > 0:
            try:
                res = ws.get_data(base_url, hts, s, mtype).Value
                break
            except requests.exceptions.ConnectionError as err:
                print(s + ' and ' + mtype + ' error: ' + str(err))
                timer = timer - 1
                sleep(30)
            except ValueError as err:
                print(s + ' and ' + mtype + ' error: ' + str(err))
                break
            except Exception as err:
                print(str(err))
                timer = timer - 1
                sleep(30)

            if timer == 0:
                raise ValueError('The Hilltop request tried too many times...the server is probably down')
        res_list.append(res)

    res1 = pd.concat(res_list)

    ### Process DTLs
    dtl1 = res1[res1.str.contains('<')]
    dtl1 = pd.to_numeric(dtl1.str.replace('<', '')).to_frame()
    dtl1['censored'] = '<'

    dtl2 = res1[res1.str.contains('>')]
    dtl2 = pd.to_numeric(dtl2.str.replace('>', '')).to_frame()
    dtl2['censored'] = '>'

    dtl3 = pd.concat([dtl1, dtl2])

    ### Remove DTLs from results
    res2 = res1.loc[~res1.index.isin(dtl3.index)]
    res2 = pd.to_numeric(res2, errors='coerce').dropna()

    ### Run stats
    grp1 = res2.reset_index().groupby(['Site', 'Measurement'])
    dtl_count = dtl3.reset_index().groupby(['Site', 'Measurement']).Value.count()
    dtl_count.name = 'DTL count'
    data_count = grp1.Value.count()
    total_count = data_count.add(dtl_count, fill_value=0).astype(int)
    total_count.name = 'total count'
    mean1 = grp1.Value.mean().round(3)
    mean1.name = 'mean'
    median1 = grp1.Value.median().round(3)
    median1.name = 'median'
    max1 = grp1.Value.max().round(3)
    max1.name = 'max'
    min1 = grp1.Value.min().round(3)
    min1.name = 'min'
    q1 = grp1.Value.quantile(0.25).round(3)
    q1.name = 'Q1'
    q3 = grp1.Value.quantile(0.75).round(3)
    q3.name = 'Q3'
    std1 = grp1.Value.std().round(3)
    std1.name = 'standard deviation'
    from_date = grp1['DateTime'].min()
    from_date.name = 'start date'
    to_date = grp1['DateTime'].max()
    to_date.name = 'end date'

    ### Make stats df
    stats_df1 = pd.concat([total_count, dtl_count, from_date, to_date, min1, q1, median1, mean1, q3, max1, std1], axis=1)

    ### return
    return res2, dtl3, stats_df1


def std_outliers(res, stats, factor):
    """
    Function to assess outliers according to the number of standard deviations from the mean.

    Parameters
    ----------
    res : DataFrame
        the time series results from the get_results function.
    stats : DataFrame
        the stats results from the get_results function.
    factor : int, float
        The number of standard deviations to use.

    Returns
    -------
    DataFrame

    """
    col_name1 = 'mean + std*' + str(factor)
    std1 = (stats['mean'] + (stats['standard deviation']*factor))
    std1.name = col_name1

    col_name2 = 'mean - std*' + str(factor)
    std2 = (stats['mean'] - (stats['standard deviation']*factor))
    std2.name = col_name2

    std2.loc[std2 < 0] = 0

    std = pd.concat([std1, std2], axis=1)

    data1 = pd.merge(res.reset_index(), std.reset_index(), on=['Site', 'Measurement'])
    data2 = data1[data1['Value'] > data1[col_name1]]
    data3 = data1[data1['Value'] < data1[col_name2]]

    data4 = pd.concat([data2, data3])

    return data4


def iqr_outliers(res, stats, factor):
    """
    Function to assess outliers according to the number of interquartile ranges (IQR) from the 3rd quartile.

    Parameters
    ----------
    res : DataFrame
        the time series results from the get_results function.
    stats : DataFrame
        the stats results from the get_results function.
    factor : int, float
        The number of IQRs to use.

    Returns
    -------
    DataFrame
    """
    col_name1 = 'Q3 + IQR*' + str(factor)
    std1 = (stats['Q3'] + (stats['Q3'] - stats['Q1'])*factor)
    std1.name = col_name1

    col_name2 = 'Q3 - IQR*' + str(factor)
    std2 = (stats['Q3'] - (stats['Q3'] - stats['Q1'])*factor)
    std2.name = col_name2

    std2.loc[std2 < 0] = 0

    std = pd.concat([std1, std2], axis=1)

    data1 = pd.merge(res.reset_index(), std.reset_index(), on=['Site', 'Measurement'])
    data2 = data1[data1['Value'] > data1[col_name1]]
    data3 = data1[data1['Value'] < data1[col_name2]]

    data4 = pd.concat([data2, data3])

    return data4


def dtl_outliers(res, dtl):
    """
    Function to assess outliers according using the logged detection limits from the samples.

    Parameters
    ----------
    res : DataFrame
        the time series results from the get_results function.
    dtl : DataFrame
        the dtl results from the get_results function.

    Returns
    -------
    DataFrame
    """
    col_name = 'detection limit'
    lt1 = dtl[dtl['censored'] == '<'].Value
    lt1.name = col_name
    lt1a = lt1.reset_index().groupby(['Site', 'Measurement'])[col_name].min()
    lt2 = pd.merge(res.reset_index(), lt1a.reset_index(), on=['Site', 'Measurement'])
    lt3 = lt2[lt2['Value'] < lt2[col_name]].copy()
    lt3['censored'] = '<'

    gt1 = dtl[dtl['censored'] == '>'].Value
    gt1.name = col_name
    gt1a = gt1.reset_index().groupby(['Site', 'Measurement'])[col_name].max()
    gt2 = pd.merge(res.reset_index(), gt1a.reset_index(), on=['Site', 'Measurement'])
    gt3 = gt2[gt2['Value'] > gt2[col_name]].copy()
    gt3['censored'] = '>'

    dtl2 = pd.concat([lt3, gt3])

    return dtl2


def min_max_outliers(res, min=None, max=None):
    """
    Function to assess outliers according global minimum and maximum values.

    Parameters
    ----------
    res : DataFrame
        the time series results from the get_results function.
    min : int, float
        The minimum value.
    max : int, float
        The maximum value.

    Returns
    -------
    DataFrame
    """
    min_max_list = []
    if isinstance(min, (int, float)):
        data1 = res[res < min].reset_index()
        data1['limit type'] = 'minimum'
        data1['limit'] = min
        min_max_list.append(data1)
    if isinstance(max, (int, float)):
        data1 = res[res > max].reset_index()
        data1['limit type'] = 'maximum'
        data1['limit'] = max
        min_max_list.append(data1)

    min_max1 = pd.concat(min_max_list)

    return min_max1



############################################
### The processing

std_list = []
iqr_list = []
dtl_list = []
min_max_list = []
stats_list = []

for mtype, limits in mtypes.items():
    print(mtype)

    ## Get the sites
    sites1 = get_stations(base_url, hts, mtype)

    ## Get the results
    res1, dtl1, stats1 = get_results(base_url, hts, mtype, sites1.ref.tolist())

    ## std
    std_out1 = std_outliers(res1, stats1, std_factor)

    ## STD
    iqr_out1 = iqr_outliers(res1, stats1, iqr_factor)

    ## DTL
    dtl_out1 = dtl_outliers(res1, dtl1)

    ## min/max
    min_max_out1 = min_max_outliers(res1, **limits)

    ## Package up results
    stats_list.append(stats1)
    std_list.append(std_out1)
    iqr_list.append(iqr_out1)
    dtl_list.append(dtl_out1)
    min_max_list.append(min_max_out1)


### Combine all results
stats = pd.concat(stats_list)
std_out = pd.concat(std_list)
iqr_out = pd.concat(iqr_list)
dtl_out = pd.concat(dtl_list)
min_max_out = pd.concat(min_max_list)

#############################################################
### Save results

print('Saving results...')

if not os.path.exists(os.path.join(base_path, 'results')):
    os.mkdir(os.path.join(base_path, 'results'))

stats.to_csv(os.path.join(base_path, 'results', stats_csv))
std_out.to_csv(os.path.join(base_path, 'results', std_csv))
iqr_out.to_csv(os.path.join(base_path, 'results', iqr_csv))
dtl_out.to_csv(os.path.join(base_path, 'results', dtl_csv))
min_max_out.to_csv(os.path.join(base_path, 'results', min_max_csv))
















































