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
import requests
from hilltoppy import web_service as ws
import codecs
import pickle
import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
from flask_caching import Cache
import base64
import flask

pd.options.display.max_columns = 10


###########################################################3
### Parameters

base_path = os.path.realpath(os.path.dirname(__file__))

with open(os.path.join(base_path, 'parameters.yml')) as param:
    param = yaml.safe_load(param)

datasets = param['source']['datasets']
base_url = param['source']['api_endpoint']
hts_list = param['source']['hts']

###########################################################
### Helper functions

mtype = datasets[0]
hts = hts_list[0]
ref = 'SQ10005'


def encode_df(df):
    """

    """
    p1 = codecs.encode(pickle.dumps(df), "base64").decode()

    return p1


def decode_df(str_encode):
    """

    """
    p1 = pickle.loads(codecs.decode(str_encode.encode(), "base64"))

    return p1


def get_stations(base_url, hts, mtype):
    """

    """
    stns1 = ws.site_list(base_url, hts, location='LatLong') # There's a problem with Hilltop that requires running the site list without a measurement first...
    stns1 = ws.site_list(base_url, hts, location='LatLong', measurement=mtype)
    stns2 = stns1[(stns1.lat > -47.5) & (stns1.lat < -34) & (stns1.lon > 166) & (stns1.lon < 179)].dropna().copy()
    stns2.rename(columns={'SiteName': 'ref'}, inplace=True)

    return stns2


def get_results(base_url, hts, mtype, ref):
    """

    """
    ### Get data
    res1 = ws.get_data(base_url, hts, ref, mtype).Value

    ### Process DTLs
    dtl1 = res1[res1.str.contains('<')]
    dtl1 = pd.to_numeric(dtl1.str.replace('<', ''))
    dtl2 = res1[res1.str.contains('>')]
    dtl2 = pd.to_numeric(dtl2.str.replace('<', ''))
    dtl3 = pd.concat([dtl1, dtl2])

    ### Remove DTLs from results
    res2 = res1.loc[~res1.index.isin(dtl3.index)]
    res2 = pd.to_numeric(res2, errors='coerce').dropna()

    ### Run stats
    dtl_count = len(dtl3)
    data_count = len(res2)
    total_count = dtl_count + data_count
    mean1 = round(res2.mean(), 3)
    median1 = round(res2.median(), 3)
    max1 = round(res2.max(), 3)
    min1 = round(res2.min(), 3)
    std1 = round(res2.std(), 3)
    dates1 = res2.reset_index()['DateTime']
    from_date = dates1.min()
    to_date = dates1.max()

    ### Make stats df
    stats_df1 = pd.DataFrame([[total_count, dtl_count, from_date, to_date, min1, median1, mean1, max1, std1]], columns=['total count', 'DTL count', 'start date', 'end date', 'min', 'median', 'mean', 'max', 'standard deviation'])
    stats_df1['site_name'] = ref
    stats_df1['measurement'] = mtype
    stats_df1.set_index(['site_name', 'measurement'], inplace=True)

    ### return
    return res2, stats_df1


res2, stats_df1 = get_results(base_url, hts, mtype, ref)
res3 = res2.reset_index()
fig = go.Figure(data=go.Violin(y=res3['Value'], box_visible=True, line_color='black',
                               meanline_visible=True, fillcolor='lightseagreen',
                               name=stats_df1.index[0][0],
                               opacity=0.6,
                               x=res3['Site']))

# fig.update_layout(yaxis_zeroline=False)
fig.show()

























































