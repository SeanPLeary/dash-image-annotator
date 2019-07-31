#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from app import app
from apps import annotator, uploader, config


app.layout = html.Div([
    dcc.Location(id='url-location', refresh=False, href='/apps/annotator'),
    dcc.Link(id='link', children='Navigate to uploader', href='/apps/uploader'),
    html.Br(),
    # content will be rendered in this element
    html.Div(id='page-content')
])


@app.callback([Output('page-content', 'children'),
               Output('link', 'children'),
               Output('link', 'href')],
              [Input('url-location', 'pathname')])
def display_page(pathname):
    if pathname == '/apps/annotator':
        return annotator.layout, 'Navigate to uploader', '/apps/uploader'
    if pathname == '/apps/uploader':
        return uploader.layout, 'Navigate to annotator', '/apps/annotator'
    return annotator.layout, 'Navigate to uploader', '/apps/uploader'


if __name__ == '__main__':
    app.run_server(host=config.HOST, port=config.PORT, debug=True)
    