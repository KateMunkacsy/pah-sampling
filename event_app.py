from dash import Dash, html, dcc, callback, Output, Input, no_update, dash_table
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

current_dir = os.path.dirname(__file__)
DIR = "/Users/KateMunkacsy/Desktop/CREATE/spectrometer_data/"

#%% ====================================================================
# 1. LOAD DATA
# ======================================================================

benz   = pd.read_excel(f"{DIR}/data/input/benzene results.xlsx")
naphth = pd.read_excel(f"{DIR}/data/input/naphthalene results.xlsx")



#%% ====================================================================
# 2. Prep Data
# ======================================================================

benz['datetime']   = pd.to_datetime(benz['date'].astype(str) + ' ' + benz['time'].astype(str))
naphth['datetime'] = pd.to_datetime(naphth['date'].astype(str) + ' ' + naphth['time'].astype(str))

## - combine datasets
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

## - categorize the readings into levels
cond = [merged_df['ug/m3.benzene'] < 50,
        merged_df['ug/m3.benzene'].between(50, 100),
        merged_df['ug/m3.benzene'].between(100, 200),
        merged_df['ug/m3.benzene'] > 200]
val = ['<50 ug/m3', '50-100 ug/m3', '100-200 ug/m3', '>200 ug/m3']
merged_df['benzene_level'] = np.select(cond, val, default=None)

cond = [merged_df['ug/m3.naphthalene'] < 20,
        merged_df['ug/m3.naphthalene'].between(20, 40),
        merged_df['ug/m3.naphthalene'].between(40, 60),
        merged_df['ug/m3.naphthalene'] > 60]
val = ['<20 ug/m3', '20-40 ug/m3', '40-60 ug/m3', '>60 ug/m3']
merged_df['naphthalene_level'] = np.select(cond, val, default=None)

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

PLACES = {
    "New York": {"lat": 40.7128, "lon": -74.0060},
    "London": {"lat": 51.5074, "lon": -0.1278},
    "Tokyo": {"lat": 35.6762, "lon": 139.6503},
    "Sydney": {"lat": -33.8688, "lon": 151.2093},
    "Cape Town": {"lat": -33.9249, "lon": 18.4241},
}



#%% ====================================================================
# 4. App layout
# ======================================================================
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

app = Dash(__name__, external_stylesheets=[dbc.themes.MORPH])
color_mode_switch =  html.Span(
    [
        dbc.Label(className="fa fa-moon", html_for="switch"),
        dbc.Switch( id="switch", value=True, className="d-inline-block ms-1", persistence=True),
        dbc.Label(className="fa fa-sun", html_for="switch"),
    ]
)

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Spectrometer Data - Event Exploration", className="text-center mt-2 mb-2"), width=12)
    ], style={"height": "8vh"}),
    dcc.Tabs([
        dcc.Tab(label='V1', style=tab_style, selected_style=tab_selected_style, children=[
            ## =========================== start of V1 tab content
            dbc.Row([
            # Menu of criteria controls
                dbc.Col([
                    html.H3("Benzene"),
                    dbc.Row([
                        dbc.Col([
                            html.Div('Detected'),
                            dcc.RadioItems(
                                options=[True, False],
                                value=True,
                                inline=True,
                                id='radio-benz-detect'
                            ),
                            html.Div('Minimum ug/m3 level'),
                            dcc.Input(id='benz-level', type="number", value=100, debounce=True),
                            html.Div('Span of time at target level (in minutes)'),
                            dcc.Input(id='benz-span', type="number", value=5, debounce=True),

                        ]),
                        dbc.Col([
                            html.Div('Strength Threshold'),
                            dcc.Slider(
                                merged_df['strength.benzene'].min(), merged_df['strength.benzene'].max(),
                                value=merged_df['strength.benzene'].min(),
                                id='benz-strength-slider'
                            ),
                            html.Div('Integration Time Threshold'),
                            dcc.Slider(
                                merged_df['integration time.benzene'].min(), merged_df['integration time.benzene'].max(),
                                value=merged_df['integration time.benzene'].min(),
                                id='benz-intg-slider'
                            ),
                            html.Div('R-squared Threshold'),
                            dcc.Slider(
                                merged_df['benzene.rsq'].min(), merged_df['benzene.rsq'].max(),
                                value=merged_df['benzene.rsq'].min(),
                                id='benz-rsq-slider'
                            ),
                        ]),
                    ]),
                ], width=5, className="shadow-sm p-3 mb-5 bg-white rounded"),
                dbc.Col([
                    html.H3("Naphthalene"),
                    dbc.Row([
                        dbc.Col([
                            html.Div('Detected'),
                            dcc.RadioItems(
                                options=[True, False],
                                value=True,
                                inline=True,
                                id='radio-naph-detect'
                            ),
                            html.Div('Minimum ug/m3 level'),
                            dcc.Input(id='naph-level', type="number", value=100, debounce=True),
                            html.Div('Span of time at target level (in minutes)'),
                            dcc.Input(id='naph-span', type="number", value=5, debounce=True),
                        ]),
                        dbc.Col([
                            html.Div('Strength Threshold'),
                            dcc.Slider(
                                merged_df['strength.naphthalene'].min(), merged_df['strength.naphthalene'].max(),
                                value=merged_df['strength.naphthalene'].min(),
                                id='naph-strength-slider'
                            ),
                            html.Div('Integration Time Threshold'),
                            dcc.Slider(
                                merged_df['integration time.naphthalene'].min(), merged_df['integration time.naphthalene'].max(),
                                value=merged_df['integration time.naphthalene'].min(),
                                id='naph-intg-slider'
                            ),
                            html.Div('R-Squared Threshold'),
                            dcc.Slider(
                                merged_df['naphthalene.rsq'].min(), merged_df['naphthalene.rsq'].max(),
                                value=merged_df['naphthalene.rsq'].min(),
                                id='naph-rsq-slider'
                            ),
                        ]),
                    ]),
                ], width=5, className="shadow-sm p-3 mb-5 bg-white rounded"),
                dbc.Col([
                    html.Div('Preferred level of criteria met'),
                    dcc.Dropdown(
                        id='criteria-preference',
                        options=["Both", "At least one", "At least Benzene", "At least Naphthalene"],
                        value="Both",
                        clearable=True,
                        multi=False
                    ),
                    html.Div('---'),
                    html.Div([
                        daq.ToggleSwitch(
                            id='sync-check',
                            value=False,
                            label='Sync naphthalene criteria with benzene criteria',
                            labelPosition='top',
                            size=40,
                            theme='dark'
                        ),
                            ]),
                ], width=2, className="shadow-sm p-3 mb-5 bg-white rounded"),
            ], className="g-3"),
            dbc.Row([
                dbc.Col([
                    html.H5("Number of Events by Time Period"),
                    dag.AgGrid(
                        id="sum-table",
                        columnDefs=sum_cols,
                        rowData=pd.DataFrame().to_dict("records"), 
                        columnSize="sizeToFit",
                        dashGridOptions={"resizable": True, "sortable": True}
                    ),
                ], width=12, className="shadow-sm p-3 mb-5 bg-white rounded"),
            ]),
            dbc.Row([
                dbc.Col([
                    html.H5("Select Time Period"),
                    dcc.Dropdown(
                        id='period-dropdown',
                        options=[{'label': prd, 'value': prd} for prd in merged_df['period'].unique()],
                        value=merged_df['period'].unique()[-1],
                        clearable=True,
                        multi=False
                    ),
                    dcc.Graph(id='reading-graph'),
                ], width=12, className="shadow-sm p-3 mb-5 bg-white rounded"),
            ]),
            dbc.Row([
                dbc.Col([
                    html.H5("Benzene Events"),
                    dag.AgGrid(
                        id="benz-table",
                        columnDefs=[{"field": i} for i in benz_tbl_cols],
                        rowData=pd.DataFrame().to_dict("records"), 
                        columnSize="autoSize",
                        dashGridOptions={"resizable": True, "sortable": True, "rowSelection": "single"}
                    ),
                ], width=12, className="shadow-sm p-3 mb-5 bg-white rounded"),
            ]),
            dbc.Row([
                dbc.Col([
                    html.H5("Naphthalene Events"),
                    dag.AgGrid(
                        id="naph-table",
                        columnDefs=[{"field": i} for i in naph_tbl_cols],
                        rowData=pd.DataFrame().to_dict("records"), 
                        columnSize="autoSize",
                        dashGridOptions={"resizable": True, "sortable": True, "rowSelection": "single"}
                    ),
                ], width=12, className="shadow-sm p-3 mb-5 bg-white rounded"),
            ]),
            ## =========================== end of V1 tab content
        ]),
        dcc.Tab(label='V2', style=tab_style, selected_style=tab_selected_style, children=[
            ## =========================== start of V2 tab content
            dbc.Row([
            # Menu of criteria controls
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            html.H5("Set Criteria"),
                            html.Div('Benzene: at least one detection >= ug/m3 level'),
                            dcc.Input(id='benz_lvl_thresh', type="number", value=100, debounce=True),
                            html.Div('Naphthalene: at least one detection >= ug/m3 level'),
                            dcc.Input(id='naph_lvl_thresh', type="number", value=100, debounce=True),
                            html.Div('---'),
                            html.Div([
                                daq.ToggleSwitch(
                                    id='sync-check-2',
                                    value=False,
                                    label='Sync naphthalene criteria with benzene criteria',
                                    labelPosition='top',
                                    size=40,
                                    theme='dark'
                                ),
                            ]),
                            html.Div('Criteria to prioritize'),
                            dcc.RadioItems(
                                options=["Either criteria", "At least benzene criteria", "At least naphthalene criteria", "Both criteria"],
                                value="Either criteria",
                                inline=True,
                                id='detect-preference'
                            ),
                        ]),
                    ]),
                ], width=4, className="shadow-sm p-3 mb-5 bg-white rounded"),
                dbc.Col([
                    html.H5("Number of Events by Time & Sampling Period"),
                    html.Div('Prior span of time without detection (in hours)'),
                    dcc.Input(id='no-detect-span', type="number", value=8, debounce=True),
                    html.Div(''),
                    dag.AgGrid(
                        id="detect-table",
                        columnDefs=detect_cols,
                        rowData=pd.DataFrame().to_dict("records"), 
                        columnSize="sizeToFit",
                        dashGridOptions={"resizable": True, "sortable": True}
                    ),
                ], width=8, className="shadow-sm p-3 mb-5 bg-white rounded"),
            ]),
            dbc.Row([
                html.H3("Event Details"),
                dbc.Row([
                    dbc.Col([
                        html.H5("Select Time Period"),
                        dcc.Dropdown(
                            id='period-dropdown-2',
                            options=[{'label': prd, 'value': prd} for prd in merged_df['period'].unique()],
                            value=merged_df['period'].unique()[-1],
                            clearable=True,
                            multi=False
                        ),
                    ]),
                dbc.Row([
                    dcc.Graph(id='reading-graph-2'),
                    html.Div('-'),
                    html.H5("Select Sampling Duration (in hours)"),
                    dcc.Dropdown(
                        id='sample-period-dropdown',
                        options=[{'label': prd, 'value': prd} for prd in [1, 2, 4, 8, 12, 24]],
                        value=1,
                        clearable=True,
                        multi=False
                    ),
                    html.Div('Click on a start date in table to jump to date in graph'),
                    dag.AgGrid(
                        id="event-table",
                        columnDefs=event_tbl_cols,
                        rowData=pd.DataFrame().to_dict("records"), 
                        columnSize="autoSize",
                        dashGridOptions={"resizable": True, "sortable": True, "rowSelection": "single"},
                    ),
                ]),
                ]),
            ]),
            ## =========================== end of V2 tab content
        ])
    ])
], fluid=True)

## === Callbacks & functions for tab V1 ===========================================
@callback(
    Output('radio-naph-detect', 'value'),
    Output('naph-strength-slider', 'value'),
    Output('naph-intg-slider', 'value'),
    Output('naph-rsq-slider', 'value'),
    Output('naph-level', 'value'),
    Output('naph-span', 'value'),
    Input('sync-check', 'value'),
    Input('radio-benz-detect', 'value'),
    Input('benz-strength-slider', 'value'),
    Input('benz-intg-slider', 'value'),
    Input('benz-rsq-slider', 'value'),
    Input('benz-level', 'value'),
    Input('benz-span', 'value'),
)
def sync_criteria(sync_check, radio_benz_detect, benz_strength_slider, benz_intg_slider, benz_rsq_slider, benz_level, benz_span):
    if sync_check:
        radio_naph_detect = radio_benz_detect
        naph_strength_slider = benz_strength_slider
        naph_intg_slider = benz_intg_slider
        naph_rsq_slider = benz_rsq_slider
        naph_level = benz_level
        naph_span = benz_span
        return radio_naph_detect, naph_strength_slider, naph_intg_slider, naph_rsq_slider, naph_level, naph_span
    return no_update

@callback(
    Output('sum-table', 'rowData'),
    Output('reading-graph', 'figure'),
    Output('benz-table', 'rowData'),
    Output('naph-table', 'rowData'),
    Input('period-dropdown', 'value'),
    Input('radio-benz-detect', 'value'),
    Input('benz-strength-slider', 'value'),
    Input('benz-intg-slider', 'value'),
    Input('benz-rsq-slider', 'value'),
    Input('benz-level', 'value'),
    Input('benz-span', 'value'),
    Input('radio-naph-detect', 'value'),
    Input('naph-strength-slider', 'value'),
    Input('naph-intg-slider', 'value'),
    Input('naph-rsq-slider', 'value'),
    Input('naph-level', 'value'),
    Input('naph-span', 'value'),
    Input('criteria-preference', 'value'),
    Input('benz-table', 'cellClicked'),
    Input('naph-table', 'cellClicked'),
)
def update_data(period, ben_detect, ben_strength, ben_int_time, ben_r_sq, ben_level_val, ben_span, naph_detect, naph_strength, naph_int_time, naph_r_sq, naph_level_val, naph_span, criteria_pref, benz_select, naph_select):

    df = merged_df.copy()

    ## - benzene criteria
    df['meets_benzene_criteria'] = ((df['detect.benzene'] == ben_detect) & 
                                    (df['strength.benzene'] >= ben_strength) & 
                                    (df['integration time.benzene'] >= ben_int_time) & 
                                    (df['benzene.rsq'] >= ben_r_sq) & 
                                    (df['ug/m3.benzene'] >= ben_level_val))
    df['benzene_criteria_block'] = (df["meets_benzene_criteria"] != df["meets_benzene_criteria"].shift()).cumsum()
    span_df = df.groupby(["benzene_criteria_block", "meets_benzene_criteria"])["datetime"].agg(benz_criteria_start="min", benz_criteria_end="max", benz_criteria_duration=lambda x: x.max() - x.min()).reset_index()
    span_df['benz_criteria_duration'] = (span_df['benz_criteria_duration'].dt.total_seconds() // 60).astype(int)
    span_df = span_df[span_df['meets_benzene_criteria']==True].copy()
    df = df.merge(span_df, how='left', on=['benzene_criteria_block','meets_benzene_criteria'])
    df['meets_benzene_criteria_and_span'] = (df['meets_benzene_criteria'] & (df['benz_criteria_duration'] >= ben_span))
    
    ## - naphthalene criteria
    df['meets_naph_criteria'] = ((df['detect.naphthalene'] == naph_detect) & 
                                 (df['strength.naphthalene'] >= naph_strength) & 
                                 (df['integration time.naphthalene'] >= naph_int_time) & 
                                 (df['naphthalene.rsq'] >= naph_r_sq) & 
                                 (df['ug/m3.naphthalene'] >= naph_level_val))
    df['naph_criteria_block'] = (df["meets_naph_criteria"] != df["meets_naph_criteria"].shift()).cumsum()
    span_df = df.groupby(["naph_criteria_block", "meets_naph_criteria"])["datetime"].agg(naph_criteria_start="min", naph_criteria_end="max", naph_criteria_duration=lambda x: x.max() - x.min()).reset_index()
    span_df['naph_criteria_duration'] = (span_df['naph_criteria_duration'].dt.total_seconds() // 60).astype(int)
    span_df = span_df[span_df['meets_naph_criteria']==True].copy()
    df = df.merge(span_df, how='left', on=['naph_criteria_block','meets_naph_criteria'])
    df['meets_naph_criteria_and_span'] = (df['meets_naph_criteria'] & (df['naph_criteria_duration'] >= naph_span))

    ## - indicate based on criteria meeting
    if criteria_pref == "Both":
        df['candidate_event'] = (df['meets_benzene_criteria_and_span'] & df['meets_naph_criteria_and_span'])
    elif criteria_pref == "At least one":
        df['candidate_event'] = (df['meets_benzene_criteria_and_span'] | df['meets_naph_criteria_and_span'])
    elif criteria_pref == "At least Benzene":
        df['candidate_event'] = (df['meets_benzene_criteria_and_span'])
    elif criteria_pref == "At least Naphthalene":
        df['candidate_event'] = (df['meets_naph_criteria_and_span'])


    ## - for summary of periods:
    benz_events_summary = df[df['meets_benzene_criteria_and_span']].copy()
    benz_events_summary = benz_events_summary.groupby(['period', 'benzene_criteria_block', 'benz_criteria_duration', 'benz_criteria_start', 'benz_criteria_end']).agg({
                                                    'ug/m3.benzene': ['count', 'min', 'max', 'mean'],
                                                    'ppb.benzene': ['count', 'min', 'max', 'mean'],
                                                    'strength.benzene': ['min', 'max', 'mean'],
                                                    'integration time.benzene': ['min', 'max', 'mean'], 
                                                    'benzene.rsq': ['min', 'max', 'mean'],
                                                    'meets_naph_criteria_and_span': ['max'],
                                                    'meets_naph_criteria': ['max'],
                                                    'ug/m3.naphthalene': ['count', 'min', 'max', 'mean'],
                                                    'ppb.naphthalene': ['count', 'min', 'max', 'mean'],
                                                    'strength.naphthalene': ['min', 'max', 'mean'],
                                                    'integration time.naphthalene': ['min', 'max', 'mean'], 
                                                    'naphthalene.rsq': ['min', 'max', 'mean'],
                                                    })
    benz_events_summary.reset_index(inplace=True)

    naph_events_summary = df[df['meets_naph_criteria_and_span']].copy()
    naph_events_summary = naph_events_summary.groupby(['period', 'naph_criteria_block', 'naph_criteria_duration', 'naph_criteria_start', 'naph_criteria_end']).agg({
                                                    'ug/m3.naphthalene': ['count', 'min', 'max', 'mean'],
                                                    'ppb.naphthalene': ['count', 'min', 'max', 'mean'],
                                                    'strength.naphthalene': ['min', 'max', 'mean'],
                                                    'integration time.naphthalene': ['min', 'max', 'mean'], 
                                                    'naphthalene.rsq': ['min', 'max', 'mean'],
                                                    'meets_benzene_criteria_and_span': ['max'],
                                                    'meets_benzene_criteria': ['max'],
                                                    'ug/m3.benzene': ['count', 'min', 'max', 'mean'],
                                                    'ppb.benzene': ['count', 'min', 'max', 'mean'],
                                                    'strength.benzene': ['min', 'max', 'mean'],
                                                    'integration time.benzene': ['min', 'max', 'mean'], 
                                                    'benzene.rsq': ['min', 'max', 'mean'],
                                                    })
    naph_events_summary.reset_index(inplace=True)

    n_benz_events = benz_events_summary.groupby('period').agg({('benzene_criteria_block', ''): ['count'], ('benz_criteria_duration', ''): ['mean', 'min', 'max']}).reset_index()
    n_benz_events.columns = ['_'.join(col) for col in n_benz_events.columns.to_flat_index()]
    n_benz_events.rename(columns={"period__":"period", "benzene_criteria_block__count":"benzene_criteria_block", "benz_criteria_duration__mean":"duration_mean", "benz_criteria_duration__min":"duration_min", "benz_criteria_duration__max":"duration_max"}, inplace=True)

    n_naph_events = naph_events_summary.groupby('period').agg({('naph_criteria_block', ''): ['count'], ('naph_criteria_duration', ''): ['mean', 'min', 'max']}).reset_index()
    n_naph_events.columns = ['_'.join(col) for col in n_naph_events.columns.to_flat_index()]
    n_naph_events.rename(columns={"period__":"period", "naph_criteria_block__count":"naph_criteria_block", "naph_criteria_duration__mean":"duration_mean", "naph_criteria_duration__min":"duration_min", "naph_criteria_duration__max":"duration_max"}, inplace=True)

    n_both_events = benz_events_summary[benz_events_summary[('meets_naph_criteria_and_span', 'max')]].groupby('period').agg({('meets_naph_criteria_and_span', 'max'): ['sum'], ('benz_criteria_duration', ''): ['mean', 'min', 'max']}).reset_index()
    n_both_events.columns = ['_'.join(col) for col in n_both_events.columns.to_flat_index()]
    n_both_events.rename(columns={"period__":"period", "meets_naph_criteria_and_span_max_sum":"meets_naph_criteria_and_span", "benz_criteria_duration__mean":"duration_mean", "benz_criteria_duration__min":"duration_min", "benz_criteria_duration__max":"duration_max"}, inplace=True)

    summary_df = n_both_events.merge(n_benz_events, how='left', on='period')
    summary_df = summary_df.merge(n_naph_events, how='left', on='period')
    summary_df.rename(columns={"meets_naph_criteria_and_span":"both_count",
                                    "benzene_criteria_block":"benz_count",
                                    "naph_criteria_block":"naph_count"}, inplace=True)
    summary_df = summary_df.round(1)
    sum_data = summary_df.to_dict("records")

    
    ## - for line chart: show all events in time period
    max_y = max(df["ug/m3.benzene"].max(), df["ug/m3.naphthalene"].max()) + 100
    plot_df = df[df['period'] == period].copy().reset_index()
    fig = px.line(plot_df, x="datetime", y=["ug/m3.benzene", "ug/m3.naphthalene"], range_y=[0, max_y], labels={"value": "ug/m3"})
    fig.update_traces(name="Benzene", selector={"name": "ug/m3.benzene"}, hovertemplate="%{x} | <b>%{y} ug/m3<b>")
    fig.update_traces(name="Naphthalene", selector={"name": "ug/m3.naphthalene"}, hovertemplate="%{x} | <b>%{y} ug/m3<b>")
    benz_events = plot_df[plot_df['meets_benzene_criteria_and_span']].copy()
    benz_events = benz_events[['benz_criteria_start', 'benz_criteria_end']].drop_duplicates()
    naph_events = plot_df[plot_df['meets_naph_criteria_and_span']].copy()
    naph_events = naph_events[['naph_criteria_start', 'naph_criteria_end']].drop_duplicates()
    for index, event in benz_events.iterrows():
        fig.add_vrect(
            x0=event["benz_criteria_start"], x1=event["benz_criteria_end"],
            fillcolor="blue", opacity=0.2,
            layer="below", line_width=0,
        )
    for index, event in naph_events.iterrows():
        fig.add_vrect(
            x0=event["naph_criteria_start"], x1=event["naph_criteria_end"],
            fillcolor="red", opacity=0.2,
            layer="below", line_width=0,
        )
    fig.update_layout(
        legend=dict(
            orientation="h",  # Make the legend horizontal
            yanchor="bottom",  # Anchor the bottom of the legend
            y=1.02,  # Position slightly above the top of the plot
            xanchor="center",  # Center the legend horizontally
            x=0.5,  # Place it in the middle of the x-axis
        )
    )
    if benz_select:
        # Extract the date value from the clicked row
        selected_date = pd.to_datetime(benz_select["value"])
        
        # Add a visual anchor (vertical dashed line) at the selected date
        fig.add_vline(x=selected_date, line_width=2, line_dash="dash", line_color="darkgray")
        
        # Center the x-axis view around the selected date (optional padding)
        fig.update_layout(
            xaxis_range=[
                pd.to_datetime(selected_date) - pd.Timedelta(hours=12),
                pd.to_datetime(selected_date) + pd.Timedelta(hours=12)
            ]
        )
    if naph_select:
        # Extract the date value from the clicked row
        selected_date = pd.to_datetime(naph_select["value"])
        
        # Add a visual anchor (vertical dashed line) at the selected date
        fig.add_vline(x=selected_date, line_width=2, line_dash="dash", line_color="darkgray")
        
        # Center the x-axis view around the selected date (optional padding)
        fig.update_layout(
            xaxis_range=[
                pd.to_datetime(selected_date) - pd.Timedelta(hours=12),
                pd.to_datetime(selected_date) + pd.Timedelta(hours=12)
            ]
        )

    ## - for event tables under line graph
    benz_events_summary.columns = ['_'.join(col) for col in benz_events_summary.columns.to_flat_index()]
    benz_summary = benz_events_summary[benz_events_summary['period_']==period].copy()
    benz_summary = benz_summary[list(benz_rename.keys())]
    benz_summary.rename(columns=benz_rename, inplace=True)
    benz_summary["Duration"] = benz_summary["Duration"] + 5
    benz_data = benz_summary.to_dict("records")
    naph_events_summary.columns = ['_'.join(col) for col in naph_events_summary.columns.to_flat_index()]
    naph_summary = naph_events_summary[naph_events_summary['period_']==period].copy()
    naph_summary = naph_summary[list(naph_rename.keys())]
    naph_summary.rename(columns=naph_rename, inplace=True)
    naph_summary["Duration"] = naph_summary["Duration"] + 5
    naph_data = naph_summary.to_dict("records")

    return sum_data, fig, benz_data, naph_data


## === Callbacks & functions for tab V2 ===========================================
@callback(
    Output('naph_lvl_thresh', 'value'),
    Input('sync-check-2', 'value'),
    Input('benz_lvl_thresh', 'value'),
)
def sync_criteria(sync_check, benz_lvl_thresh):
    if sync_check:
        return benz_lvl_thresh
    return no_update

@callback(
    Output('detect-table', 'rowData'),
    Output('event-table', 'rowData'),
    Input('detect-preference', 'value'),
    Input('no-detect-span', 'value'),
    Input('benz_lvl_thresh', 'value'),
    Input('naph_lvl_thresh', 'value'),
    Input('period-dropdown-2', 'value'),
    Input('sample-period-dropdown', 'value'),
)
def update_data(pref, no_span, benz_lvl, naph_lvl, period, sample_period):

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

    hr_periods = [1, 2, 4, 8, 12, 24]
    all_dfs = pd.DataFrame()
    for hr in hr_periods:
        agg_df = summarize_events(hr=hr, none_list=none_list, df=df, benz_lvl=benz_lvl, naph_lvl=naph_lvl)
        all_dfs = pd.concat([all_dfs, agg_df])

    if pref == "Either criteria":
        match_df = all_dfs[(all_dfs[f'benz_gt{benz_lvl}_sum'] >= 1) | (all_dfs[f'naph_gt{naph_lvl}_sum'] >= 1)].copy()
    elif pref == "At least benzene criteria":
        match_df = all_dfs[(all_dfs[f'benz_gt{benz_lvl}_sum'] >= 1)].copy()
    elif pref == "At least naphthalene criteria":
        match_df = all_dfs[(all_dfs[f'naph_gt{naph_lvl}_sum'] >= 1)].copy()
    elif pref == "Both criteria":
        match_df = all_dfs[(all_dfs[f'benz_gt{benz_lvl}_sum'] >= 1) & (all_dfs[f'naph_gt{naph_lvl}_sum'] >= 1)].copy()

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

@callback(
    Output('reading-graph-2', 'figure'),
    Input('event-table', 'cellClicked'),
    Input('period-dropdown-2', 'value'),
    Input('no-detect-span', 'value'),
    Input('sample-period-dropdown', 'value')
)
def update_graph(cell_clicked, period, pre_time, post_time):
    df = merged_df.copy()

    ## - for line chart: show all events in time period
    max_y = max(df["ug/m3.benzene"].max(), df["ug/m3.naphthalene"].max()) + 100
    plot_df = df[df['period'] == period].copy().reset_index()
    fig = px.line(plot_df, x="datetime", y=["ug/m3.benzene", "ug/m3.naphthalene"], range_y=[0, max_y], labels={"value": "ug/m3"})
    fig.update_traces(name="Benzene", selector={"name": "ug/m3.benzene"}, hovertemplate="%{x} | <b>%{y} ug/m3<b>")
    fig.update_traces(name="Naphthalene", selector={"name": "ug/m3.naphthalene"}, hovertemplate="%{x} | <b>%{y} ug/m3<b>")

    fig.update_layout(
        legend=dict(
            orientation="h",  # Make the legend horizontal
            yanchor="bottom",  # Anchor the bottom of the legend
            y=1.02,  # Position slightly above the top of the plot
            xanchor="center",  # Center the legend horizontally
            x=0.5,  # Place it in the middle of the x-axis
        )
    )
    
    # If a cell is clicked, focus the graph on that date
    if cell_clicked:
        # Extract the date value from the clicked row
        selected_date = pd.to_datetime(cell_clicked["value"])
        
        # Add a visual anchor (vertical dashed line) at the selected date
        fig.add_vline(x=selected_date, line_width=2, line_dash="dash", line_color="darkgray")
        
        # Center the x-axis view around the selected date (optional padding)
        fig.update_layout(
            xaxis_range=[
                pd.to_datetime(selected_date) - pd.Timedelta(hours=pre_time),
                pd.to_datetime(selected_date) + pd.Timedelta(hours=post_time)
            ]
        )
        
    return fig


if __name__ == '__main__':
    app.run(debug=True)

# %%
