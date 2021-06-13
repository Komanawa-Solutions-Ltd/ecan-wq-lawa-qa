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
import orjson

pd.options.display.max_columns = 10


###########################################################3
### Parameters

base_path = os.path.realpath(os.path.dirname(__file__))

with open(os.path.join(base_path, 'parameters.yml')) as param:
    param = yaml.safe_load(param)

datasets = param['source']['datasets']
base_url = param['source']['api_endpoint']
hts_list = param['source']['hts']

summ_cols = ['site name', 'measurement', 'total count', 'DTL count', 'start date', 'end date', 'min', 'median', 'mean', 'max', 'standard deviation']

## Dash parameters
server = flask.Flask(__name__)
app = dash.Dash(__name__, server=server,  url_base_pathname = '/')

ts_plot_height = 600
map_height = 700

lat1 = -43.45
lon1 = 171.9
zoom1 = 7

mapbox_access_token = "pk.eyJ1IjoibXVsbGVua2FtcDEiLCJhIjoiY2pudXE0bXlmMDc3cTNxbnZ0em4xN2M1ZCJ9.sIOtya_qe9RwkYXj5Du1yg"

map_layout = dict(mapbox = dict(layers = [], accesstoken = mapbox_access_token, style = "outdoors", center=dict(lat=lat1, lon=lon1), zoom=zoom1), margin = dict(r=0, l=0, t=0, b=0), autosize=True, hovermode='closest', height=map_height, showlegend = True, legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))

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


# def build_summ_table(site_summ):
#     """

#     """
#     table1 = [{'Station reference': s['ref'], 'Min Value': s['min'], 'Max Value': s['max'], 'Start Date': (s['from_date'] + pd.DateOffset(hours=12)).strftime('%Y-%m-%d'), 'End Date': (s['to_date'] + pd.DateOffset(hours=12)).strftime('%Y-%m-%d')} for i, s in site_summ.iterrows()]

#     return table1


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
    stats_df1 = pd.DataFrame([[ref, mtype, total_count, dtl_count, from_date, to_date, min1, median1, mean1, max1, std1]], columns=summ_cols)

    ### return
    return res2.reset_index(), dtl3, stats_df1


# res2, stats_df1 = get_results(base_url, hts, mtype, ref)
# res3 = res2.reset_index()
# fig = go.Figure(data=go.Violin(y=res3['Value'], box_visible=True,
#                                meanline_visible=True,
#                                name=stats_df1.index[0][0],
#                                opacity=1.0,
#                                x=res3['Site']))

# fig.show()



############################################
### The app


def serve_layout():
    ### Initialize base data
    # run_date = pd.Timestamp.now(tz='utc').round('s').tz_localize(None)
    # last_month = (run_date - pd.tseries.offsets.MonthEnd(1)).floor('D')
    # last_year = ((last_month - pd.DateOffset(years=1) - pd.DateOffset(days=2)) + pd.tseries.offsets.MonthEnd(1)) + pd.DateOffset(days=1)

    layout = html.Div(children=[
    html.Div([
        # html.P(children='Select hts:'),
        html.Label('hts file'),
        dcc.Dropdown(options=[{'label': d, 'value': d} for d in hts_list], value=None, id='hts', clearable=False),
        html.Label('Measurement'),
        dcc.Dropdown(options=[{'label': d, 'value': d} for d in datasets], value=None, id='parameters'),
        html.Label('Site name'),
        dcc.Dropdown(options=[], id='sites', optionHeight=40),
        dcc.Link(html.Img(src=app.get_asset_url('ecan.png'), height=100), href='https://www.ecan.govt.nz/')
        ],
    className='two columns', style={'margin': 20}),

    html.Div([
        html.P('Click on a site:', style={'display': 'inline-block'}),
        dcc.Graph(
            id = 'site-map',
            style={'height': map_height},
            figure=dict(data = [dict(
                                    type = 'scattermapbox',
                                    hoverinfo = 'text',
                                    marker = dict(
                                            size=8,
                                            color='black',
                                            opacity=1
                                            )
                                    )
                                ],
                        layout=map_layout),
            config={"displaylogo": False})


    ], className='three columns', style={'margin': 20}),
#
    html.Div([

        dcc.Tabs(id='plot_tabs', value='info_tab', children=[
            dcc.Tab(label='Info', value='info_tab'),
            dcc.Tab(label='Box plot', value='box_plot'),
            # dcc.Tab(label='Cumulative flow', value='cf_plot'),
            # dcc.Tab(label='Hydrograph', value='hydro_plot'),
            # dcc.Tab(label='Allocation', value='allo_plot'),
            ]
        ),
        html.Div(id='plots'),

    dash_table.DataTable(
        id='summ_table',
        columns=[{"name": v, "id": v, 'deletable': True} for v in summ_cols],
        data=[],
        sort_action="native",
        sort_mode="multi",
        style_cell={
            'minWidth': '80px', 'maxWidth': '200px',
            'whiteSpace': 'normal'
        }
        ),

    ], className='six columns', style={'margin': 10, 'height': 900}),
    dcc.Store(id='ts_data', data=None),
    dcc.Store(id='summ_data', data=None),
    dcc.Store(id='dtl_data', data=None),
    dcc.Store(id='site_data', data=None),
], style={'margin':0})

    return layout


app.layout = serve_layout

#########################################
### Callbacks


@app.callback(
    Output('sites', 'options'),
    [Input('site_data', 'data')])
def update_site_list(site_data_str):
    if site_data_str is None:
        print('No sites available')
        return []
    else:
        sites1 = decode_df(site_data_str)
        sites_options = [{'label': s, 'value': s} for s in sites1.ref.tolist()]

        return sites_options


@app.callback(
    Output('site_data', 'data'),
    [Input('hts', 'value'), Input('parameters', 'value')])
def update_site_data(hts, parameter):
    if (hts is None) or (parameter is None):
        print('No sites available')
        return None
    else:
        sites1 = get_stations(base_url, hts, parameter)
        # sites_options = [{'label': s['ref'], 'value': s['station_id']} for s in sites_summ1]

        return encode_df(sites1)


@app.callback(
    [Output('ts_data', 'data'), Output('summ_data', 'data'), Output('dtl_data', 'data')],
    [Input('hts', 'value'), Input('parameters', 'value'), Input('sites', 'value')])
def update_ts_data(hts, parameter, site):
    if (hts is None) or (parameter is None) or (site is None):
        print('No data available')
        return None, None, None
    else:
        res1, dtl, site_summ = get_results(base_url, hts, parameter, site)

        return encode_df(res1), encode_df(site_summ), encode_df(dtl)


@app.callback(
        Output('site-map', 'figure'),
        [Input('site_data', 'data')],
        [State('site-map', 'figure')])
def update_display_map(site_data_str, figure):
    if site_data_str is None:
        # print('Clear the sites')
        data1 = figure['data'][0]
        if 'hoverinfo' in data1:
            data1.pop('hoverinfo')
        data1.update(dict(size=8, color='black', opacity=0))
        fig = dict(data=[data1], layout=figure['layout'])
    else:
        sites1 = decode_df(site_data_str)

        lon1 = sites1.lon.tolist()
        lat1 =  sites1.lat.tolist()
        names1 = sites1.ref.tolist()

        data = [dict(
            lat = lat1,
            lon = lon1,
            text = names1,
            ids=names1,
            type = 'scattermapbox',
            hoverinfo = 'text',
            marker = dict(size=8, color='black', opacity=1)
        )]

        fig = dict(data=data, layout=figure['layout'])

    return fig


@app.callback(
        Output('sites', 'value'),
        [Input('site-map', 'selectedData'), Input('site-map', 'clickData')]
        )
def update_sites_values(selectedData, clickData):
    # print(clickData)
    # print(selectedData)
    if selectedData:
        sel1 = selectedData['points'][0]
        if 'id' in sel1:
            site1_id = sel1['id']
        else:
            site1_id = None
    elif clickData:
        sel1 = clickData['points'][0]
        if 'id' in sel1:
            site1_id = sel1['id']
        else:
            site1_id = None
    else:
        site1_id = None

    # print(sites1_id)

    return site1_id


@app.callback(
    Output('summ_table', 'data'),
    [Input('summ_data', 'data')],
    # [State('stn_dict', 'data'), State('method_dd', 'value'), State('active_select', 'value')]
    )
def update_summ_table(summ_data_str):
    if summ_data_str is not None:
        summ_data = decode_df(summ_data_str)
        summ_table = summ_data.to_dict('records')

        return summ_table
    else:
        return []


@app.callback(Output('plots', 'children'),
              [Input('plot_tabs', 'value'), Input('ts_data', 'data')],
              # [State('stn_dict', 'data'), State('method_dd', 'value'), State('active_select', 'value'), State('allo_ds_id', 'data'), State('flow_use_ds_id', 'data'), State('last_month', 'data'), State('last_year', 'data')]
              )
def render_plot(tab, ts_data_str):

    # print(flow_stn_id)

    info_str = """
            ### Intro
            This is the [Environment Southland](https://www.es.govt.nz/) streamflow naturalisation, surface water usage, and surface water allocation dashboard.

            ### Brief Guide
            #### Selecting datasets
            The datasets are broken into two groups: **Recorder** and **Gauging** data. Recorder data have been used directly, while gauging data have been correlated to recorder sites to simulate  recorder data. There is also an option to select only the active flow sites (those with data in the last year) and all flow sites.

            #### Map
            The map shows the available streamflow sites given the prior selection on the left. **Click on a site** and the map will show the upstream catchment and the associated water abstraction sites (WAPs) in black.

            #### Data tabs
            The other tabs have plots for various use cases.

            ##### Flow duration
            The **Flow duration** plot orders the entire record from highest to lowest to indicate how often a particular flow is exceeded. The measured and naturalised flows are plotted together for comparisons, although in many cases they are very similar.

            ##### Cumulative flow
            The **Cumulative flow** plot accumulates the flow for each year in the record to show how this year compares to previous years.

            ##### Hydrogrph
            The **Hydrograph** plot shows the entire record of a particular site.

            ##### Allocation
            The **Allocation** plot shows the current surface water allocation estimated by the upstream consents, the associated water usage, and the flow at 30% of the Q95 for that site. In many cases, the flow at 30% of the Q95 is the surface water allocation limit for rivers.

            ### Guaging correlations
            Naturalised streamflows have been estimated at all surface water recorder sites and gaugings sites with at least 12 gaugings. The gauging data has been automatically correlated to nearby recorder sites to generate continuous time series datasets. The correlation parameters and accuracies are shown below the site summaries below the plots. These include the normalised root mean square error (NRMSE), mean absolute error (MANE), adjusted R^2 (Adj R2), number of observations used in the correlation, the recorder sites used in the correlation, and the F value that was used to determine the appropriate recorder sites for the correlation.

            ### More info
            A more thorough description of the streamflow naturalisation method can be found [here](https://github.com/mullenkamp/nz-flow-naturalisation/blob/main/README.rst).
        """
    print(tab)

    if tab == 'info_tab':
        fig1 = info_str

    else:
        if ts_data_str is not None:
            ts_data = decode_df(ts_data_str)

            if tab == 'box_plot':
                fig1 = go.Figure(data=go.Box(y=ts_data['Value'],
                                boxmean=True,
                                name=ts_data.Site.iloc[0],
                                opacity=1.0,
                                x=ts_data['Site'],
                                boxpoints='all',
                                ),
                                 layout = dict(
                                                # title=stn_ref,
                                                # yaxis={'title': 'Flow rate (m3/s)'},
                                                # xaxis={'title': 'Date'},
                                                # dragmode='pan',
                                                font=dict(size=18),
                                                hovermode='x',
                                                paper_bgcolor = '#F4F4F8',
                                                plot_bgcolor = '#F4F4F8',
                                                height = ts_plot_height
                                                )
                                                                         )
        else:
            fig1 = info_str

    if isinstance(fig1, str):
        return dcc.Markdown(fig1)
    else:
        fig = dcc.Graph(
                # id = 'plots',
                figure = fig1,
                config={"displaylogo": False, 'scrollZoom': True, 'showLink': False}
                )

        return fig



# if __name__ == '__main__':
#     server.run(host='0.0.0.0', port=80)

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8080)











































