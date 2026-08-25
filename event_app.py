from dash import Dash, html, dcc, callback, Output, Input, no_update, dash_table
import dash_bootstrap_components as dbc
import dash_daq as daq
import dash_ag_grid as dag
import plotly.express as px
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
sum_cols = ['period', 'Overlapping Events', 'Benzene Events', 'Naphthalene Events']



#%% ====================================================================
# 3. App layout
# ======================================================================

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
                columnDefs=[{"field": i} for i in sum_cols],
                rowData=pd.DataFrame().to_dict("records"), 
                columnSize="sizeToFit",
                dashGridOptions={"resizable": True, "sortable": True}
            ),
        ], width=6, className="shadow-sm p-3 mb-5 bg-white rounded"),
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
        ], width=6, className="shadow-sm p-3 mb-5 bg-white rounded"),
    ]),
    dbc.Row([
        dbc.Col([
            html.H5("Benzene Events"),
            dag.AgGrid(
                id="benz-table",
                columnDefs=[{"field": i} for i in benz_tbl_cols],
                rowData=pd.DataFrame().to_dict("records"), 
                columnSize="autoSize",
                dashGridOptions={"resizable": True, "sortable": True}
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
                dashGridOptions={"resizable": True, "sortable": True}
            ),
        ], width=12, className="shadow-sm p-3 mb-5 bg-white rounded"),
    ]),
], fluid=True)

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
)
def update_data(period, ben_detect, ben_strength, ben_int_time, ben_r_sq, ben_level_val, ben_span, naph_detect, naph_strength, naph_int_time, naph_r_sq, naph_level_val, naph_span, criteria_pref):

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

    n_benz_events = benz_events_summary.groupby('period')['benzene_criteria_block'].count().reset_index()
    n_naph_events = naph_events_summary.groupby('period')['naph_criteria_block'].count().reset_index()
    n_both_events = benz_events_summary.groupby('period')['meets_naph_criteria_and_span'].sum().reset_index()
    n_both_events.columns = ['_'.join(col) for col in n_both_events.columns.to_flat_index()]
    n_both_events.rename(columns={"period_":"period"}, inplace=True)

    summary_df = n_both_events.merge(n_benz_events, how='left', on='period')
    summary_df = summary_df.merge(n_naph_events, how='left', on='period')
    summary_df.rename(columns={"meets_naph_criteria_and_span_max":"Overlapping Events",
                                "benzene_criteria_block":"Benzene Events",
                                "naph_criteria_block":"Naphthalene Events"}, inplace=True)
    sum_data = summary_df.to_dict("records")

    
    ## - for line chart: show all events in time period
    max_y = max(df["ug/m3.benzene"].max(), df["ug/m3.naphthalene"].max()) + 100
    plot_df = df[df['period'] == period].copy().reset_index()
    fig = px.line(plot_df, x="datetime", y=["ug/m3.benzene", "ug/m3.naphthalene"], range_y=[0, max_y], labels={"value": "ug/m3"})
    fig.update_traces(name="Benzene", selector={"name": "ug/m3.benzene"})
    fig.update_traces(name="Naphthalene", selector={"name": "ug/m3.naphthalene"})
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

    ## - for event tables under line graph
    benz_events_summary.columns = ['_'.join(col) for col in benz_events_summary.columns.to_flat_index()]
    benz_summary = benz_events_summary[benz_events_summary['period_']==period].copy()
    benz_summary = benz_summary[list(benz_rename.keys())]
    benz_summary.rename(columns=benz_rename, inplace=True)
    benz_data = benz_summary.to_dict("records")
    naph_events_summary.columns = ['_'.join(col) for col in naph_events_summary.columns.to_flat_index()]
    naph_summary = naph_events_summary[naph_events_summary['period_']==period].copy()
    naph_summary = naph_summary[list(naph_rename.keys())]
    naph_summary.rename(columns=naph_rename, inplace=True)
    naph_data = naph_summary.to_dict("records")

    return sum_data, fig, benz_data, naph_data
    


if __name__ == '__main__':
    app.run(debug=True)

# %%
