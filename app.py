from dash import Dash, html, dcc, callback, Output, Input, no_update, dash_table, clientside_callback
import dash_bootstrap_components as dbc
import dash_daq as daq
import dash_ag_grid as dag
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import requests
import re
import os
from datetime import datetime, timedelta
import textwrap

#%% ====================================================================
# 1. LOAD DATA
# ======================================================================

benz   = pd.read_excel("data/benzene results.xlsx")
naphth = pd.read_excel("data/naphthalene results.xlsx")


#%% ====================================================================
# 2. PREP DATA
# ======================================================================

## - combine datasets
benz['datetime']   = pd.to_datetime(benz['date'].astype(str) + ' ' + benz['time'].astype(str))
naphth['datetime'] = pd.to_datetime(naphth['date'].astype(str) + ' ' + naphth['time'].astype(str))
merged_df = benz.merge(naphth, how='outer', on=['datetime', 'date', 'time'], suffixes=('.benzene', '.naphthalene'))

## - construct time variables
merged_df['year']  = merged_df['datetime'].dt.year
merged_df['month'] = merged_df['datetime'].dt.month
merged_df['day']   = merged_df['datetime'].dt.day
merged_df['month_year'] = merged_df['year'].astype(str) + "-" + merged_df['month'].astype(str)
merged_df['month_day_time'] = merged_df['month'].astype(str) + "-" + merged_df['day'].astype(str) + "-" + merged_df['time'].astype(str)

## - construct time periods
cond = [merged_df['date'].between('2021-11-01', '2022-10-31'),
        merged_df['date'].between('2022-11-01', '2023-10-31'),
        merged_df['date'].between('2023-11-01', '2024-10-31'),
        merged_df['date'].between('2024-11-01', '2025-10-31'),
        merged_df['date'].between('2025-11-01', '2026-10-31')]
val = ["Nov 2021 - Oct 2022", 
       "Nov 2022 - Oct 2023",
       "Nov 2023 - Oct 2024",
       "Nov 2024 - Oct 2025",
       "Nov 2025 - May 2026"]
merged_df['period'] = np.select(cond, val, default="July 2021 - Oct 2021")

## - variable renaming dictionaries for clearer naming in tables
benz_rename = {'benz_criteria_start_':'Start', 'benz_criteria_end_':'End', 'benz_criteria_duration_':'Duration',
                'ug/m3.benzene_count':'Number of benzene readings',
                'ug/m3.benzene_min': 'Min benzene level (ug/m3)', 
                'ug/m3.benzene_max': 'Max benzene level (ug/m3)', 
                'ug/m3.benzene_mean': 'Mean benzene level (ug/m3)',
                'strength.benzene_min': 'Min strength', 
                'strength.benzene_max': 'Max strength',
                'strength.benzene_mean': 'Mean strength', 
                'integration time.benzene_min': 'Min integration time',
                'integration time.benzene_max': 'Max integration time', 
                'integration time.benzene_mean': 'Mean integration time',
                'benzene.rsq_min': 'Min R-sq', 
                'benzene.rsq_max': 'Max R-sq', 
                'benzene.rsq_mean': 'Mean R-sq',
                'meets_naph_criteria_and_span_max': 'Naphthalene event', 
                'meets_naph_criteria_max': 'Almost naphthalene event'}
naph_rename = {'naph_criteria_start_':'Start', 'naph_criteria_end_':'End', 'naph_criteria_duration_':'Duration',
                'ug/m3.naphthalene_count':'Number of naphthalene readings',
                'ug/m3.naphthalene_min': 'Min naphthalene level (ug/m3)', 
                'ug/m3.naphthalene_max': 'Max naphthalene level (ug/m3)', 
                'ug/m3.naphthalene_mean': 'Mean naphthalene level (ug/m3)',
                'strength.naphthalene_min': 'Min strength', 
                'strength.naphthalene_max': 'Max strength',
                'strength.naphthalene_mean': 'Mean strength', 
                'integration time.naphthalene_min': 'Min integration time',
                'integration time.naphthalene_max': 'Max integration time', 
                'integration time.naphthalene_mean': 'Mean integration time',
                'naphthalene.rsq_min': 'Min R-sq', 
                'naphthalene.rsq_max': 'Max R-sq', 
                'naphthalene.rsq_mean': 'Mean R-sq',
                'meets_benzene_criteria_and_span_max': 'Benzene event', 
                'meets_benzene_criteria_max': 'Almost benzene event'}

## - table column names
benz_tbl_cols = list(benz_rename.values())
naph_tbl_cols = list(naph_rename.values())
sum_cols = [
    {
        "field": "period", "headerName": "Period"
    },
    {
        "headerName": "Overlapping Events",
        "marryChildren": True,
        "children": [                     
            {"field": "both_count", "headerName": "#"},
            {"field": "duration_mean_x", "headerName": "Avg Dur."},
            {"field": "duration_min_x", "headerName": "Min Dur."},
            {"field": "duration_max_x", "headerName": "Max Dur."},
        ],
    },
    {
        "headerName": "Benzene Events",
        "marryChildren": True, 
        "children": [                     
            {"field": "benz_count", "headerName": "#"},
            {"field": "duration_mean_y", "headerName": "Avg Dur."},
            {"field": "duration_min_y", "headerName": "Min Dur."},
            {"field": "duration_max_y", "headerName": "Max Dur."},
        ],
    },
    {
        "headerName": "Naphthalene Events", 
        "marryChildren": True,
        "children": [                     
            {"field": "naph_count", "headerName": "#"},
            {"field": "duration_mean", "headerName": "Avg Dur."},
            {"field": "duration_min", "headerName": "Min Dur."},
            {"field": "duration_max", "headerName": "Max Dur."},
        ],
    },
]
detect_cols = [
    {
        "field": "period", "headerName": "Period"
    },
    {
        "headerName": "Sampling Period", 
        "marryChildren": True,
        "children": [                     
            {"field": "1", "headerName": "1 hour"},
            {"field": "2", "headerName": "2 hours"},
            {"field": "4", "headerName": "4 hours"},
            {"field": "8", "headerName": "8 hours"},
            {"field": "12", "headerName": "12 hours"},
            {"field": "24", "headerName": "24 hours"},
        ],
    },
]
event_tbl_cols = [
    {
        "headerName": "Time Frame",
        "marryChildren": True,
        "children": [                     
            {"field": "datetime_min", "headerName": "Start"},
            {"field": "datetime_max", "headerName": "End"},
        ],
    },
    {
        "headerName": "Benzene Detections",
        "marryChildren": True, 
        "children": [                     
            {"field": "detect_benzene_sum", "headerName": "#"},
            {"field": "pct_benz_detect", "headerName": "%"},
            {"field": "pct_benz_thresh", "headerName": "% above thresh"},
            {"field": "ug/m3_benzene_mean", "headerName": "Mean ug/m3"},
            {"field": "ug/m3_benzene_min", "headerName": "Min ug/m3"},
            {"field": "ug/m3_benzene_max", "headerName": "Max ug/m3"},
        ],
    },
    {
        "headerName": "Naphthalene Detections", 
        "marryChildren": True,
        "children": [                     
            {"field": "detect_naphthalene_sum", "headerName": "#"},
            {"field": "pct_naph_detect", "headerName": "%"},
            {"field": "pct_naph_thresh", "headerName": "% above thresh"},
            {"field": "ug/m3_naphthalene_mean", "headerName": "Mean ug/m3"},
            {"field": "ug/m3_naphthalene_min", "headerName": "Min ug/m3"},
            {"field": "ug/m3_naphthalene_max", "headerName": "Max ug/m3"},
        ],
    },
]

## - sampling period options (hours)
sample_periods = [1, 2, 4, 8, 12, 24]

## - function for summarizing event details based on sampling period
def summarize_events(hr, none_list, df, benz_lvl, naph_lvl):
    target_dts = list(none_list)
    df = df.sort_values('datetime')
    targets_df = pd.DataFrame({'target': pd.to_datetime(target_dts)}).sort_values('target')

    detected_df = pd.merge_asof(
        df, 
        targets_df, 
        left_on='datetime', 
        right_on='target', 
        direction='backward', 
        tolerance=pd.Timedelta(hours=hr)
    )
    detected_df = detected_df[detected_df['target'].notna()].copy()
    detected_df[f'benz_gt{benz_lvl}'] = (detected_df['ug/m3.benzene'] >= benz_lvl)
    detected_df[f'naph_gt{naph_lvl}'] = (detected_df['ug/m3.naphthalene'] >= naph_lvl)
    agg_detect = detected_df.groupby(['period', 'target']).agg({
        'datetime': ['min', 'max'],
        'detect.benzene': ['sum'],
        'detect.naphthalene': ['sum'],
        'ug/m3.benzene': ['mean', 'min', 'max'],
        'ug/m3.naphthalene': ['mean', 'min', 'max'],
        'strength.benzene': ['min'], 
        'strength.naphthalene': ['min'], 
        'integration time.benzene': ['min', 'max'], 
        'integration time.naphthalene': ['min', 'max'], 
        'benzene.rsq': ['min'], 
        'naphthalene.rsq': ['min'], 
        f'benz_gt{benz_lvl}': ['sum'],
        f'naph_gt{naph_lvl}': ['sum']})
    agg_detect.columns = ['_'.join(col) for col in agg_detect.columns.to_flat_index()]
    agg_detect.reset_index(inplace=True)
    agg_detect['timeframe'] = hr
    agg_detect['pct_benz_detect'] = 100*(agg_detect['detect.benzene_sum']*5)/(hr*60)
    agg_detect['pct_naph_detect'] = 100*(agg_detect['detect.naphthalene_sum']*5)/(hr*60)
    agg_detect[f'pct_benz_gt{benz_lvl}'] = 100*(agg_detect[f'benz_gt{benz_lvl}_sum']*5)/(hr*60)
    agg_detect[f'pct_naph_gt{naph_lvl}'] = 100*(agg_detect[f'naph_gt{naph_lvl}_sum']*5)/(hr*60)

    return agg_detect


#%% ====================================================================
# 3. APP LAYOUT
# ======================================================================

## - Styling for tabs in app
tabs_styles = {
    'height': '44px'
}
tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '6px',
    'fontWeight': 'bold'
}

tab_selected_style = {
    'borderTop': '1px solid #d6d6d6',
    'borderBottom': '1px solid #d6d6d6',
    'backgroundColor': "#3D27CC",
    'color': 'white',
    'padding': '6px'
}

## - Initialize app
app = Dash(__name__, external_stylesheets=[dbc.themes.MORPH])
server = app.server
color_mode_switch =  html.Span(
    [
        dbc.Label(className="fa fa-moon", html_for="switch"),
        dbc.Switch( id="switch", value=True, className="d-inline-block ms-1", persistence=True),
        dbc.Label(className="fa fa-sun", html_for="switch"),
    ]
)

## - Design app layout components
app.layout = dbc.Container([
    ## - Header -----------------------------------------------------------------------------------------------
    dbc.Row([
        dbc.Col(html.H1("Spectrometer Data - Event Exploration", className="text-center mt-2 mb-2"), width=12)
    ], style={"height": "8vh"}),

    dcc.Tabs([

        ## ----------------------------------------------------------------------------------- start of V2 tab content
        dcc.Tab(label='V2', style=tab_style, selected_style=tab_selected_style, children=[
            dbc.Row([

                ## - Menu of criteria controls ----------------------------------------------
                dbc.Col([
                    html.H4("Criteria Settings"),

                    ## - Benzene criteria ---------------------------------------------------
                    dbc.Row([
                        html.H5("Benzene"),
                        dbc.Col([
                            html.Div(
                                children=[
                                    html.Label("At least one detection >= ", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                    dcc.Input(id='benz_lvl_thresh', type="number", value=100, debounce=True, style={'width':'75px'}),
                                    html.Label(" ug/m3", style={'fontWeight': 'bold', 'marginLeft': '10px'}),
                                ],
                                style={'display': 'flex', 'alignItems': 'baseline'}
                            ),
                            html.Div(
                                children=[
                                    html.Label("Integration Time: ", style={'fontWeight': 'bold', 'marginRight': '5px'}),
                                    html.Div(
                                        dcc.RangeSlider(
                                            id='benz-intg-slider-2',
                                            min=merged_df['integration time.benzene'].min(),
                                            max=merged_df['integration time.benzene'].max(),
                                            value=[merged_df['integration time.benzene'].min(), merged_df['integration time.benzene'].max()],
                                            marks=None,
                                            tooltip={"placement": "bottom", "always_visible": False} 
                                        ),
                                        style={'width': '66%', 'marginLeft': 'auto',}
                                    ),
                                ],
                                style={'display': 'flex', 'alignItems': 'baseline'}
                            ),
                        ]),
                        dbc.Col([
                            html.Div(
                                children=[
                                    html.Label("Strength: ", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                    html.Div(
                                        dcc.Slider(
                                            merged_df['strength.benzene'].min(), merged_df['strength.benzene'].max(),
                                            value=merged_df['strength.benzene'].min(),
                                            id='benz-strength-slider-2'
                                        ),
                                        style={'width': '80%', 'marginLeft': 'auto'}
                                    )
                                ],
                                style={'display': 'flex', 'alignItems': 'baseline'}
                            ),
                            html.Div(
                                children=[
                                    html.Label("R-Sq: ", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                    html.Div(
                                        dcc.Slider(
                                            merged_df['benzene.rsq'].min(), merged_df['benzene.rsq'].max(),
                                            value=merged_df['benzene.rsq'].min(),
                                            id='benz-rsq-slider-2'
                                        ),
                                        style={'width': '80%', 'marginLeft': 'auto'}
                                    ),
                                ],
                                style={'display': 'flex', 'alignItems': 'baseline'}
                            ),
                        ]),
                    ], className="mb-4", style={"padding-left": "30px", "padding-right": "30px"}),
                    ## - Naphthalene criteria ---------------------------------------------------
                    dbc.Row([
                        html.H5("Naphthalene"),
                        dbc.Col([
                            html.Div(
                                children=[
                                    html.Label("At least one detection >= ", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                    dcc.Input(id='naph_lvl_thresh', type="number", value=100, debounce=True, style={'width':'75px'}),
                                    html.Label(" ug/m3", style={'fontWeight': 'bold', 'marginLeft': '10px'}),
                                ],
                                style={'display': 'flex', 'alignItems': 'baseline'}
                            ),
                            html.Div(
                                children=[
                                    html.Label("Integration Time: ", style={'fontWeight': 'bold', 'marginRight': '5px'}),
                                    html.Div(
                                        dcc.RangeSlider(
                                            id='naph-intg-slider-2',
                                            min=merged_df['integration time.naphthalene'].min(),
                                            max=merged_df['integration time.naphthalene'].max(),
                                            value=[merged_df['integration time.naphthalene'].min(), merged_df['integration time.naphthalene'].max()],
                                            marks=None,
                                            tooltip={"placement": "bottom", "always_visible": False} ,
                                        ),
                                    style={'width': '66%', 'marginLeft': 'auto',}
                                    ),
                                ],
                                style={'display': 'flex', 'alignItems': 'baseline'}
                            ),
                        ]),
                        dbc.Col([
                            html.Div(
                                children=[
                                    html.Label("Strength: ", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                    html.Div(
                                        dcc.Slider(
                                            merged_df['strength.naphthalene'].min(), merged_df['strength.naphthalene'].max(),
                                            value=merged_df['strength.naphthalene'].min(),
                                            id='naph-strength-slider-2',
                                        ),
                                        style={'width': '80%', 'marginLeft': 'auto'}
                                    ),
                                ],
                                style={'display': 'flex', 'alignItems': 'baseline'}
                            ),
                            html.Div(
                                children=[
                                    html.Label("R-Sq: ", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                    html.Div(
                                        dcc.Slider(
                                            merged_df['naphthalene.rsq'].min(), merged_df['naphthalene.rsq'].max(),
                                            value=merged_df['naphthalene.rsq'].min(),
                                            id='naph-rsq-slider-2'
                                        ),
                                        style={'width': '80%', 'marginLeft': 'auto'}
                                    ),
                                ],
                                style={'display': 'flex', 'alignItems': 'baseline'}
                            ),
                        ]),
                    ], className="mb-5", style={"padding-left": "30px", "padding-right": "30px"}),
                    dbc.Row([], className="mb-5"),
                    ## - Combined settings ---------------------------------------------------
                    dbc.Row([
                        dbc.Col([
                            html.Div(
                                children=[
                                    html.Label("Sync naphthalene criteria with benzene criteria ", style={'fontWeight': 'bold', 'marginRight': '5px'}),
                                    daq.ToggleSwitch(
                                        id='sync-check-2',
                                        value=False,
                                        size=40,
                                        theme='dark'
                                    ),
                                ],
                                style={'display': 'flex', 'flexDirection': 'row', 'justifyContent': 'flex-start', 'gap':'10px'}
                            ),
                        ]),
                        dbc.Col([
                            html.Div(
                                children=[
                                    html.Label('Criteria to prioritize', style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                    dcc.RadioItems(
                                        options=["Either criteria", "Both criteria", "At least benzene criteria", "At least naphthalene criteria"],
                                        value="Either criteria",
                                        inline=True,
                                        id='detect-preference'
                                    ),
                                ],
                                style={'display': 'flex', 'alignItems': 'baseline'}
                            ),
                        ]),
                    ], style={"padding-left": "30px", "padding-right": "50px"}),
                ], width=6, className="shadow-sm p-3 mb-5 bg-white rounded"),

                ## - Summary table of events by time period --------------------------------
                dbc.Col([
                    html.H4("Number of Events by Time & Sampling Period"),
                    html.Div(
                        children=[
                            html.Label("Prior span of time without detection:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                            dcc.Input(id='no-detect-span', type="number", value=8, debounce=True, style={"width": "50px"}),
                            html.Label(" hour(s)", style={'fontWeight': 'bold', 'marginLeft': '10px'}),
                        ],
                        style={'display': 'flex', 'alignItems': 'center'} # Aligns label and dropdown vertically
                    ),
                    dag.AgGrid(
                        id="detect-table",
                        columnDefs=detect_cols,
                        rowData=pd.DataFrame().to_dict("records"), 
                        columnSize="sizeToFit",
                        dashGridOptions={"resizable": True, "sortable": True}
                    ),
                ], width=6, className="shadow-sm p-3 mb-5 bg-white rounded", style={"padding-left": "50px", "padding-right": "50px"}),
            ], className="mb-3"),
            
            ## - Event details section ---------------------------------------------------
            dbc.Row([
                html.H4("Reviewing Event Details"),
                dbc.Row([

                    ## - Graph of readings for time period --------------------------------
                    dbc.Col([
                        dbc.Row([
                            html.Div(
                                children=[
                                    html.Label("Select Time Period: ", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                    dcc.Dropdown(
                                        id='period-dropdown-2',
                                        options=[{'label': prd, 'value': prd} for prd in merged_df['period'].unique()],
                                        value=merged_df['period'].unique()[-1],
                                        clearable=True,
                                        multi=False
                                    ),
                                ],
                                style={'display': 'flex', 'alignItems': 'center'}
                            ),
                        ]),
                        dcc.Graph(id='reading-graph-2'),
                    ], width=6, className="shadow-sm p-3 mb-5 bg-white rounded"),

                    ## - Table of events for time period --------------------------------
                    dbc.Col([
                        dbc.Row([
                                html.Div(
                                    children=[
                                        html.Label("Select Sampling Duration: ", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                        dcc.Dropdown(
                                            id='sample-period-dropdown',
                                            options=[{'label': prd, 'value': prd} for prd in sample_periods],
                                            value=1,
                                            clearable=True,
                                            multi=False,
                                            style={"width": "100px"}
                                        ),
                                        html.Label(" hour(s)", style={'fontWeight': 'bold', 'marginLeft': '10px'})
                                    ],
                                    style={'display': 'flex', 'alignItems': 'center'}
                                ),
                        ]),
                        dbc.Row([]),
                        dbc.Row([
                            dbc.Col([html.Div('Click on a start date in table to jump to date in graph')]),
                            dbc.Col([html.Button("Export data to csv", id="btn-export", n_clicks=0)], width=2),
                        ]),
                        dag.AgGrid(
                            id="event-table",
                            columnDefs=event_tbl_cols,
                            rowData=pd.DataFrame().to_dict("records"), 
                            columnSize="autoSize",
                            dashGridOptions={"resizable": True, "sortable": True, "rowSelection": "single"},
                            csvExportParams={"fileName": "events.csv"}
                        ),
                    ], width=6, className="shadow-sm p-3 mb-5 bg-white rounded"),
                ]),
            ]),
            ## ----------------------------------------------------------------------------------- end of V2 tab content
        ])
    ])
], fluid=True)


#%% ====================================================================
# 4. APP FUNCTIONALITY
# ======================================================================

## === Callbacks & functions for tab V2 ===========================================

### - sync naphthalene criteria with benzene criteria
@callback(
    Output('naph_lvl_thresh', 'value'),
    Output('naph-strength-slider-2', 'value'),
    Output('naph-intg-slider-2', 'value'),
    Output('naph-rsq-slider-2', 'value'),
    Input('sync-check-2', 'value'),
    Input('benz_lvl_thresh', 'value'),
    Input('benz-strength-slider-2', 'value'),
    Input('benz-intg-slider-2', 'value'),
    Input('benz-rsq-slider-2', 'value'),
)
def sync_criteria(sync_check, benz_lvl_thresh, benz_str, benz_intg, benz_rsq):
    if sync_check:
        naph_lvl_thresh = benz_lvl_thresh
        naph_str = benz_str
        naph_intg = benz_intg
        naph_rsq = benz_rsq
        return naph_lvl_thresh, naph_str, naph_intg, naph_rsq
    return no_update

### - update summary table & event table based on criteria selections
@callback(
    Output('detect-table', 'rowData'),
    Output('event-table', 'rowData'),
    Input('detect-preference', 'value'),
    Input('no-detect-span', 'value'),
    Input('benz_lvl_thresh', 'value'),
    Input('benz-strength-slider-2', 'value'),
    Input('benz-intg-slider-2', 'value'),
    Input('benz-rsq-slider-2', 'value'),
    Input('naph_lvl_thresh', 'value'),
    Input('naph-strength-slider-2', 'value'),
    Input('naph-intg-slider-2', 'value'),
    Input('naph-rsq-slider-2', 'value'),
    Input('period-dropdown-2', 'value'),
    Input('sample-period-dropdown', 'value'),
)
def update_data(pref, no_span, benz_lvl, benz_str, benz_int, benz_rsq, naph_lvl, naph_str, naph_int, naph_rsq, period, sample_period):

    df = merged_df.copy()
    df['benz_detection_block'] = (df["detect.benzene"] != df["detect.benzene"].shift()).cumsum()
    df['naph_detection_block'] = (df["detect.naphthalene"] != df["detect.naphthalene"].shift()).cumsum()
    df['either_detection_block'] = (df[["detect.benzene", "detect.naphthalene"]].max(axis=1) != df[["detect.benzene", "detect.naphthalene"]].shift().max(axis=1)).cumsum()
    detect_distr = df[['datetime', "detect.benzene", "detect.naphthalene", 'benz_detection_block', 'naph_detection_block', 'either_detection_block']].copy()
    either_duration_distr = detect_distr.groupby(["either_detection_block", "detect.benzene", "detect.naphthalene"])["datetime"].agg(start="min", end="max", duration=lambda x: x.max() - x.min()).reset_index()
    either_duration_distr['detect.either'] = either_duration_distr[["detect.benzene", "detect.naphthalene"]].max(axis=1)
    either_duration_distr['detect.both'] = ((either_duration_distr["detect.benzene"]==True) & (either_duration_distr["detect.naphthalene"]==True))

    if pref == "Either criteria":
        none_list = either_duration_distr[(either_duration_distr['detect.either']==False) & 
                                          (either_duration_distr['duration'] >= timedelta(hours=no_span))]['end']
    elif pref == "At least benzene criteria":
        none_list = either_duration_distr[(either_duration_distr['detect.benzene']==False) & 
                                          (either_duration_distr['duration'] >= timedelta(hours=no_span))]['end']
    elif pref == "At least naphthalene criteria":
        none_list = either_duration_distr[(either_duration_distr['detect.naphthalene']==False) & 
                                          (either_duration_distr['duration'] >= timedelta(hours=no_span))]['end']
    elif pref == "Both criteria":
        none_list = either_duration_distr[(either_duration_distr['detect.both']==False) & 
                                          (either_duration_distr['duration'] >= timedelta(hours=no_span))]['end']

    hr_periods = sample_periods ## - defined in PREP DATA section of script
    all_dfs = pd.DataFrame()
    for hr in hr_periods:
        agg_df = summarize_events(hr=hr, none_list=none_list, df=df, benz_lvl=benz_lvl, naph_lvl=naph_lvl)
        all_dfs = pd.concat([all_dfs, agg_df])

    if pref == "Either criteria": 
        match_df = all_dfs[((all_dfs[f'benz_gt{benz_lvl}_sum'] >= 1) & 
                            (all_dfs['strength.benzene_min'] >= benz_str) & 
                            ((all_dfs['integration time.benzene_min'] >= benz_int[0]) & (all_dfs['integration time.benzene_max'] <= benz_int[1])) & 
                            (all_dfs['benzene.rsq_min'] >= benz_rsq)) | 
                            ((all_dfs[f'naph_gt{naph_lvl}_sum'] >= 1) & 
                             (all_dfs['strength.naphthalene_min'] >= naph_str) & 
                             ((all_dfs['integration time.naphthalene_min'] >= naph_int[0]) & (all_dfs['integration time.naphthalene_max'] <= naph_int[1])) & 
                             (all_dfs['naphthalene.rsq_min'] >= naph_rsq))
                        ].copy()
        
    elif pref == "At least benzene criteria":
        match_df = all_dfs[((all_dfs[f'benz_gt{benz_lvl}_sum'] >= 1) & 
                            (all_dfs['strength.benzene_min'] >= benz_str) & 
                            ((all_dfs['integration time.benzene_min'] >= benz_int[0]) & (all_dfs['integration time.benzene_max'] <= benz_int[1])) & 
                            (all_dfs['benzene.rsq_min'] >= benz_rsq))].copy()
        
    elif pref == "At least naphthalene criteria":
        match_df = all_dfs[((all_dfs[f'naph_gt{naph_lvl}_sum'] >= 1) & 
                             (all_dfs['strength.naphthalene_min'] >= naph_str) & 
                             ((all_dfs['integration time.naphthalene_min'] >= naph_int[0]) & (all_dfs['integration time.naphthalene_max'] <= naph_int[1])) & 
                             (all_dfs['naphthalene.rsq_min'] >= naph_rsq))].copy()
        
    elif pref == "Both criteria":
        match_df = all_dfs[((all_dfs[f'benz_gt{benz_lvl}_sum'] >= 1) & 
                                    (all_dfs['strength.benzene_min'] >= benz_str) & 
                                    ((all_dfs['integration time.benzene_min'] >= benz_int[0]) & (all_dfs['integration time.benzene_max'] <= benz_int[1])) & 
                                    (all_dfs['benzene.rsq_min'] >= benz_rsq)) & 
                                    ((all_dfs[f'naph_gt{naph_lvl}_sum'] >= 1) & 
                                     (all_dfs['strength.naphthalene_min'] >= naph_str) & 
                                     ((all_dfs['integration time.naphthalene_min'] >= naph_int[0]) & (all_dfs['integration time.naphthalene_max'] <= naph_int[1])) & 
                                     (all_dfs['naphthalene.rsq_min'] >= naph_rsq))
                                ].copy()

    period_n_cnt = match_df.groupby(['period', 'timeframe'])['datetime_min'].count()
    period_n_cnt = pd.DataFrame(period_n_cnt).reset_index()
    period_n_cnt = period_n_cnt.pivot(index="period", columns="timeframe", values="datetime_min").reset_index()

    period_df = match_df[match_df['period'] == period].copy()
    period_df['pct_benz_thresh'] = period_df[f'pct_benz_gt{benz_lvl}']
    period_df['pct_naph_thresh'] = period_df[f'pct_naph_gt{naph_lvl}']
    df_1 = period_df[period_df['timeframe']==sample_period].copy()
    df_1.columns = df_1.columns.str.replace('.', '_', regex=False)
    df_1 = df_1.round(1)

    return period_n_cnt.to_dict("records"), df_1.to_dict("records")

### - update line graph based on selections
@callback(
    Output('reading-graph-2', 'figure'),
    Input('event-table', 'cellClicked'),
    Input('period-dropdown-2', 'value'),
    Input('no-detect-span', 'value'),
    Input('sample-period-dropdown', 'value')
)
def update_graph(cell_clicked, period, pre_time, post_time):
    
    ## - for line chart: show all events in time period
    df = merged_df.copy()
    max_y = max(df["ug/m3.benzene"].max(), df["ug/m3.naphthalene"].max()) + 100
    plot_df = df[df['period'] == period].copy().reset_index()
    avg_benz = plot_df["ug/m3.benzene"].fillna(0).mean()
    avg_naph = plot_df["ug/m3.naphthalene"].fillna(0).mean()

    fig = px.line(plot_df, x="datetime", y=["ug/m3.benzene", "ug/m3.naphthalene"], range_y=[0, max_y], labels={"value": "ug/m3"})
    fig.update_traces(name="Benzene", selector={"name": "ug/m3.benzene"}, hovertemplate="%{x} | <b>%{y} ug/m3<b>")
    fig.update_traces(name="Naphthalene", selector={"name": "ug/m3.naphthalene"}, hovertemplate="%{x} | <b>%{y} ug/m3<b>")

    fig.add_hline(
        y=avg_benz,
        line_dash="dash",
        line_color="rgba(0, 0, 255, 0.75)",
        #annotation_text=f"Benzene avg: {avg_benz:.2f}",
        #annotation_position="top right",
    )
    fig.add_hline(
        y=avg_naph,
        line_dash="dash",
        line_color="rgba(255, 0, 0, 0.75)",
        #annotation_text=f"Naphthalene avg: {avg_naph:.2f}",
        #annotation_position="top right",
    )
    
    fig.update_layout(
        legend=dict(
            orientation="h",  
            yanchor="bottom", 
            y=1.02, 
            xanchor="center", 
            x=0.5, 
        )
    )
    
    ## - if cell in event table is clicked, focus the graph on that date
    if cell_clicked:
        selected_date = pd.to_datetime(cell_clicked["value"])
        fig.add_vline(x=selected_date, line_width=2, line_dash="dash", line_color="darkgray")
        fig.update_layout(
            xaxis_range=[
                pd.to_datetime(selected_date) - pd.Timedelta(hours=pre_time),
                pd.to_datetime(selected_date) + pd.Timedelta(hours=post_time)
            ]
        )
        
    return fig

### - export event table data as CSV file 
@callback(
    Output("event-table", "exportDataAsCsv"),
    Input("btn-export", "n_clicks"),
    prevent_initial_call=True
)
def export(n):
    if n > 0:
        return True
    return False



if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=True)
    #app.run(host="0.0.0.0", port=port, debug=False)

# %%
