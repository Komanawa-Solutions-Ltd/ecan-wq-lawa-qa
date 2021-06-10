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

pd.options.display.max_columns = 10


###########################################################3
### Parameters

base_path = os.path.realpath(os.path.dirname(__file__))

with open(os.path.join(base_path, 'parameters.yml')) as param:
    param = yaml.safe_load(param)

datasets = param['source']['datasets']
base_url = param['source']['api_endpoint']
hts = param['source']['hts']

###########################################################
### Helper functions

mtype = datasets[0]


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

    ### Run stats
    dtl_count = len(dtl3)
    data_count = len(res2)
    total_count = dtl_count + data_count





























































