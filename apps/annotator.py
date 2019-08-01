#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import base64
import datetime
import urllib.parse
from io import BytesIO, StringIO
import pandas as pd
import numpy as np
from PIL import Image as PImage
from nested_lookup import nested_lookup

from pymongo import MongoClient
from bson.objectid import ObjectId
import gridfs

import mlflow.pyfunc
import mlflow

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


client = MongoClient(config.MONGODB_CONNECT_STRING)
db = client[config.MONGODB_DATABASE]
fs = gridfs.GridFS(db)


if config.MLFLOW_URI is not None:
    mlflow.tracking.set_tracking_uri(config.MLFLOW_URI)


df_select_init = pd.DataFrame()
df_select_init['filename'] = [[]] * 1
df_select_init['_id'] = [[]] * 1
df_select_init['content_type'] = [[]] * 1
df_select_init['comments'] = [[]] * 1
df_labels_init = pd.DataFrame(config.DEFAULT_LABELS)


layout = html.Div([
    html.Div([
        html.Div([
            html.Div('Select Images', style={'color': 'blue', 'fontSize': 14}),
            html.Div([
                dash_table.DataTable(
                    id='datatable-filenames',
                    columns=[{'name': i, 'id': i} for i in df_select_init.columns[0:-1]],
                    style_cell={'textAlign': 'left'},
                    fill_width=True,
                    data=df_select_init.to_dict('records'),
                    editable=True,
                    sort_action='native',
                    sort_mode='multi',
                    row_selectable='single',
                    row_deletable=False,
                    selected_rows=[],
                    page_action='native',
                    page_current=0,
                    page_size=10
                )
            ], style={'overflowX': 'scroll'}),

            html.Br(),
            html.Div('Select/Edit Labels', style={'color': 'blue', 'fontSize': 14}),
            html.Div([
                dash_table.DataTable(
                    id='datatable-labels',
                    columns=[
                        {'name': i, 'id': i, 'deletable': False} for i in df_labels_init.columns
                    ],
                    style_header={
                        'backgroundColor': 'white',
                        'fontWeight': 'bold'
                    },
                    style_cell={'textAlign': 'left'},
                    fill_width=True,
                    data=df_labels_init.to_dict('records'),
                    editable=True,
                    sort_action='native',
                    sort_mode='multi',
                    row_selectable='single',
                    row_deletable=False,
                    selected_rows=[0]
                )
            ], style={'maxHeight': '200', 'overflowY': 'scroll','overflowX': 'scroll'}),

            html.Br(),
            html.Br(),
            html.Br(),

            html.Div(
                id='div-meta-download',
                children='Download Metadata from Database',
                style={'color': 'black', 'fontSize': 16}
            ),

            html.Div(children='select annotation_label_name'),
            dcc.Input(id='input-annotation-labels', type='text', value=''),

            html.Div(children='select number of images'),
            dcc.Input(id='input-num-imgs', type='number', value=1, min=1),

            html.Button(
                children='Download',
                id='button-download-meta',
                title='download images from db',
                n_clicks=0
            ),

            html.Div(children='select csv file with filenames'),
            html.Div(id='output-data-upload'),
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select File')
                ]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px'
                },

                multiple=True
            ),
        ], className='three columns'),

        html.Div([
            dcc.Graph(
                id='graph-image',
                config={
                    'editable': True,
                    'displayModeBar': True,
                    'showLink': False,
                    'displaylogo': False,
                    'edits': {'legendText':True, 'legendPosition':True},
                    'modeBarButtonsToRemove': [
                        'resetScale2d'
                    ]
                },
                figure={
                    'data': [{'x':[], 'y':[], 'type':'scattergl'}],
                    'layout':{
                        'xaxis':{
                            'visible': False,
                            'range': [0, config.IMG_DISPLAY_HEIGHT]
                        },
                        'yaxis':{
                            'visible': False,
                            'range': [0, config.IMG_DISPLAY_HEIGHT],
                            'scaleanchor': 'x'
                        },
                        'width': config.IMG_DISPLAY_HEIGHT,
                        'height': config.IMG_DISPLAY_HEIGHT,
                        'margin': {'l': 0, 'r': 0, 't': 0, 'b': 0},
                        'clickmode': 'event',
                        'legend': {'x': 0, 'y': 1, 'font': {'size': 22}},
                    }
                }
            )
        ], className='three columns')
    ], className='rows'),
])


@app.callback(
    [Output('datatable-filenames', 'data'),
     Output('datatable-filenames', 'columns')],
    [Input('button-download-meta', 'n_clicks')],
    [State('input-num-imgs', 'value'),
     State('input-annotation-labels', 'value'),
     State('output-data-upload', 'children')])
def query_db(n_clicks, num_imgs, filter_label, csv_data):
    '''Query mongodb database and fill datatable with filenames.'''
    df_select = pd.DataFrame()
    search_list = []
    if n_clicks > 0:
        if csv_data:
            df_filenames = pd.DataFrame(nested_lookup('data', csv_data)[0])
            filenames = df_filenames[df_filenames.columns[0]].tolist()
            num_imgs = len(filenames)
            search_list.append({"filename": {"$in": filenames}})

        if filter_label:
            if filter_label[0] == '!':
                regx = {"$not":re.compile(filter_label[1:], re.IGNORECASE)}
            else:
                regx = re.compile(filter_label, re.IGNORECASE)
            search_list.append({'metadata.dash_img_annotation.name': regx})

        if csv_data or filter_label:
            search_request = {'$and': search_list}
            result = fs.find(search_request).sort('uploadDate', -1).limit(num_imgs)
        else:
            result = fs.find().sort('uploadDate', -1).limit(num_imgs)

        filename = []
        id_ = []
        content_type = []
        comments = []
        for item in result:
            filename.append(item.filename)
            id_.append(str(item._id))
            content_type.append(item.content_type)
            comments.append(item.metadata['comments'])

        df_select['filename'] = filename
        df_select['content-type'] = content_type
        df_select['comments'] = comments
        df_select['_id'] = id_
    else:
        df_select['filename'] = [[]] * 1
        df_select['content_type'] = [[]] * 1
        df_select['comments'] = [[]] * 1
        df_select['_id'] = [[]] * 1

    return df_select.to_dict('records'), [{'name': i, 'id': i} for i in df_select.columns[0:-1]]


@app.callback(
    Output('datatable-filenames', 'style_data_conditional'),
    [Input('datatable-filenames', 'selected_rows')])
def highlight_rows_filenames(row_index):
    '''Filenames-datatable row is highlighted on user selection.'''
    if row_index:
        return [{
            'if': {'row_index': row_index[0]},
            'backgroundColor': '#808080',
            'color': 'white'
            }]
    return [{
        'backgroundColor': 'white',
        'color': 'black'
    }]


@app.callback(
    Output('datatable-labels', 'style_data_conditional'),
    [Input('datatable-labels', 'selected_rows')])
def highlight_rows_labels(row_index):
    '''Labels-datatable row is highlighted on user selection.'''
    return [{
        'if': {'row_index': row_index[0]},
        'backgroundColor': '#808080',
        'color': 'white'
    }]


@app.callback(
    Output('graph-image', 'figure'),
    [Input('datatable-filenames', 'selected_rows'),
     Input('datatable-labels', 'selected_rows')],
    [State('datatable-filenames', 'data'),
     State('datatable-labels', 'data'),
     State('input-annotation-labels', 'value'),
     State('graph-image', 'figure')])
def display_update_image(
        filename_row_index,
        label_row_index,
        file_data,
        label_data,
        filter_label,
        fig
):
    '''Display and update image w/ annotations.'''
    data = fig['data']
    layout_ = fig['layout']
    ctx = dash.callback_context
    trig_id = ctx.triggered[0]['prop_id']

    if trig_id == 'datatable-filenames.selected_rows':
        if filename_row_index:
            df_select = pd.DataFrame(file_data)
            id_ = df_select.loc[filename_row_index[0], '_id']
            out = fs.find_one({'_id':ObjectId(id_)})
            img = PImage.open(BytesIO(out.read()))
            img_width, img_height = img.size
            scale_factor = (config.IMG_DISPLAY_HEIGHT)/img_height
            data = [{
                'x': [0, img_width],
                'y': [0, img_height],
                'mode': 'markers+lines',
                'marker': {'opacity': 0, 'color': 'rgba(0,255,0,0)'},
                'showlegend': False,
                'name': 'dummy',
                'customdata': [{'shape_type':''}],
                'type':'scattergl'
            }]

            if type(out.metadata) == dict:
                if 'dash_img_annotation' in out.metadata.keys():
                    data_list = out.metadata['dash_img_annotation']
                    if filter_label:
                        for index, data_item in enumerate(data_list):
                            if re.search(filter_label, data_item['name'], re.IGNORECASE):
                                data_list[index]['visible'] = True
                            else:
                                data_list[index]['visible'] = 'legendonly'
                    data = data + data_list

            images = [go.layout.Image(
                x=0,
                sizex=img_width,
                y=img_height,
                sizey=img_height,
                xref='x',
                yref='y',
                opacity=1.0,
                layer='below',
                sizing='stretch',
                source=img
            )]
            layout_['images'] = images
            layout_['width'] = img_width*scale_factor
            layout_['height'] = img_height*scale_factor
            layout_['xaxis']['range'] = [0, img_width]
            layout_['yaxis']['range'] = [0, img_height]
            layout_['xaxis']['visible'] = False
            layout_['yaxis']['visible'] = False
            layout_['yaxis']['scaleanchor'] = 'x'
            layout_['margin'] = {'l': 0, 'r': 0, 't': 0, 'b': 0}
            layout_['clickmode'] = 'event'

    return go.Figure(data, layout_)


@app.callback(
    Output('booleanswitch-lasso-output', 'children'),
    [Input('daq-booleanswitch-lasso', 'on')])
def lasso_boolen_switch(on):
    '''Reports if user selected closed/open lasso (closed lasso connects 1st, last pts).'''
    if on:
        switch = 'Open lasso'
    else:
        switch = 'Close lasso'
    return switch


@app.callback(
    Output('store-shapes', 'data'),
    [Input('graph-image', 'relayoutData')],
    [State('store-shapes', 'data')])
def store_shapes(relayoutData, stored_data):
    '''Temporary storage of user annotions in the browser.'''
    if stored_data is None:
        stored_data = {}
    if relayoutData is not None:
        if any('shapes' in key for key in list(relayoutData.keys())):
            layout_data = relayoutData
            for key in layout_data:
                stored_data[key] = layout_data[key]

    return stored_data


@app.callback(
    [Output('javascript-ctrl-keyup', 'run'),
     Output('javascript-ctrl-click', 'run')],
    [Input('button-lasso-polygon', 'n_clicks')])
def javascript_event_listeners(n_clicks):
    '''Javascript event listeners for Ctrl+MouseClick and Ctrl+Keyup.'''
    if n_clicks < 1: return '', ''
    return '''
    var target = document
    target.addEventListener('keyup', function(evt) {
        if (evt.key == 'Control') { 
            setProps({ 
                'event': {'x':-999999, 
                          'y':-999999 }
            })
            console.log(evt)
        }
    })
    console.log(this)
    ''', '''
    var target = $('#graph-image')[0]
    target.addEventListener('click', function(evt) {
        if (evt.ctrlKey) {
            var xaxis = target._fullLayout.xaxis;
            var yaxis = target._fullLayout.yaxis;
            var l = target._fullLayout.margin.l;
            var t = target._fullLayout.margin.t; 
            var offl = target.offsetLeft;
            var offt = target.offsetTop;
            var xInDataCoord = xaxis.p2c(evt.x - offl);
            var yInDataCoord = yaxis.p2c(evt.y - offt);  
            setProps({ 
                'event': {'x':xInDataCoord, 
                          'y':yInDataCoord }
            })
            console.log(evt)
        }
    })
    console.log(this)
    '''


@app.callback(
    Output('javascript-drag-color', 'run'),
    [Input('button-lasso', 'n_clicks'),
     Input('button-rect', 'n_clicks'),
     Input('datatable-labels', 'selected_rows')],
    [State('datatable-labels', 'data')])
def drag_color(n_clicks_lasso, n_clicks_rect, label_row_index, label_data):
    '''Javascript to maintain label color while drawing box and lasso.'''
    df_labels = pd.DataFrame(label_data)
    labelcolor = df_labels.loc[label_row_index[0], 'colors']
    s = '''
    var target = $('#graph-image')[0] 
    target.on('plotly_selecting', function(eventData){{ 
        Plotly.d3.selectAll('.select-line,.select-outline-1,.select-outline-2')
            .style('stroke', '{color}'); 
        console.log(eventData);
    }});

    console.log(this)
    '''
    return s.format(color=labelcolor)


def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df_input = pd.read_csv(
                StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df_input = pd.read_excel(BytesIO(decoded))
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])
    return html.Div([
        html.H5(filename),
        html.H6(datetime.datetime.fromtimestamp(date)),
        dash_table.DataTable(
            data=df_input.to_dict('records'),
            #columns=[{'name': i, 'id': i} for i in df_input.columns],
            columns=[]
        ),
        html.Hr(),
    ])


@app.callback(Output('output-data-upload', 'children'),
              [Input('upload-data', 'contents')],
              [State('upload-data', 'filename'),
               State('upload-data', 'last_modified')])
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [
            parse_contents(c, n, d) for c, n, d in
            zip(list_of_contents, list_of_names, list_of_dates)]
        return children
    return []

