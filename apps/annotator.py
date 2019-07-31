#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import dash_daq as daq
import plotly.graph_objs as go
import visdcc

from apps import config
from app import app

layout = html.Div([
    html.Br(),
    html.Br(),
    html.Br(),
    html.Div(children='nothing here yet')
])
