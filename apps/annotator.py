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
            dcc.Store(id='store-shapes'),

            dcc.Store(id='polygon-data'),

            visdcc.Run_js(id='javascript-ctrl-click', run="$('#graph-image').Graph()"),
            visdcc.Run_js(id='javascript-ctrl-keyup', run="$('#graph-image').Graph()"),
            visdcc.Run_js(id='javascript-drag-color', run="$('#graph-image').Graph()"),

            html.Br(),

            html.Div([
                html.Button(
                    id='button-rect',
                    n_clicks=0,
                    title='rectangle marquee tool',
                    style={
                        'background-image': 'url(../assets/rect.png)',
                        'background-repeat': 'no-repeat',
                        'background-size': 'contain',
                        'background-position': 'center',
                        'height': '50px',
                        'width': '50px'
                    }
                ),
                html.Button(
                    id='button-lasso',
                    n_clicks=0,
                    title='lasso tool',
                    style={
                        'background-image': 'url(../assets/lasso.png)',
                        'background-repeat': 'no-repeat',
                        'background-size': 'contain',
                        'background-position': 'center',
                        'height': '50px',
                        'width': '50px'
                    }
                ),
                html.Button(
                    id='button-lasso-polygon',
                    n_clicks=0,
                    title='lasso-polygon tool (Ctrl+Click)',
                    style={
                        'background-image': 'url(../assets/lasso-polygon.png)',
                        'background-repeat': 'no-repeat',
                        'background-size': 'contain',
                        'background-position': 'center',
                        'height': '50px',
                        'width': '50px'
                    }
                ),
                html.Div([
                    html.Div(
                        id='booleanswitch-lasso-output',
                        children='Close lasso',
                        style={'textAlign':'center'}
                    ),
                    daq.BooleanSwitch(
                        id='daq-booleanswitch-lasso',
                        on=False
                    ),
                    html.Div(
                        id='booleanswitch-edit-output',
                        children='Edit off',
                        style={'textAlign':'center'}
                    ),
                    daq.BooleanSwitch(
                        id='daq-booleanswitch-edit',
                        on=False
                    )
                ], style={'position':'relative', 'float':'right'}),
            ], style={'display':'inline-block'}),


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
            html.Button(
                children='Remove Hidden Traces',
                id='button-remove-traces',
                title='remove hidden traces',
                n_clicks=0
            ),
            html.Button(
                children='Save',
                id='button-save',
                title='save meta-data to database',
                n_clicks=0
            ),
            html.Div(id='report-save', children=''),

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
            ], style={'maxHeight': '200', 'overflowY': 'scroll', 'overflowX': 'scroll'}),

            html.Br(),
            html.Br(),

            html.Button(
                children='Connect MLflow',
                id='button-mlflow-connect',
                title='connect to MLflow',
                n_clicks=0
            ),
            html.Div(children='select experiment'),
            dcc.Dropdown(
                id='dropdown-select-exp'
            ),

            html.Div(children='select run'),
            dcc.Dropdown(
                id='dropdown-select-run',
                style={'font-size': '13px'}
            ),

            html.Button(
                children='Batch Model',
                id='button-mlflow-batch',
                title='Batch Model',
                n_clicks=0
            ),
            html.Button(
                children='Single Selection Model',
                id='button-mlflow-single',
                title='Batch Model',
                n_clicks=0
            ),
            html.Div(id='report-model', children=''),

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
    [Output('graph-image', 'figure'),
     Output('booleanswitch-edit-output', 'children'),
     Output('polygon-data', 'data')],
    [Input('datatable-filenames', 'selected_rows'),
     Input('graph-image', 'selectedData'),
     Input('datatable-labels', 'selected_rows'),
     Input('daq-booleanswitch-edit', 'on'),
     Input('button-rect', 'n_clicks'),
     Input('button-lasso', 'n_clicks'),
     Input('javascript-ctrl-click', 'event'),
     Input('javascript-ctrl-keyup', 'event'),
     Input('button-mlflow-single', 'n_clicks'),
     Input('button-remove-traces', 'n_clicks')],
    [State('dropdown-select-run', 'value'),
     State('datatable-filenames', 'data'),
     State('datatable-labels', 'data'),
     State('daq-booleanswitch-edit', 'on'),
     State('daq-booleanswitch-lasso', 'on'),
     State('store-shapes', 'data'),
     State('polygon-data', 'data'),
     State('input-annotation-labels', 'value'),
     State('graph-image', 'figure')])
def display_update_image(
        filename_row_index,
        selectedData,
        label_row_index,
        edit_switch_bool,
        rect_nclicks,
        lasso_nclicks,
        js_ctrlclick_evt,
        js_ctrlkeyup_evt,
        mlflow_nclicks,
        remove_traces_nclicks,
        dropdwn_run_id,
        file_data,
        label_data,
        edit_boxes,
        lasso_open,
        shape_data,
        polygon_data,
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

    elif trig_id == 'graph-image.selectedData':
        # user just drew a box or lasso
        df_labels = pd.DataFrame(label_data)
        # get the labelname from the table
        labelname = df_labels.loc[label_row_index[0], 'labels']
        # get the labelcolor from the table
        labelcolor = df_labels.loc[label_row_index[0], 'colors']
         # check selection type: Box or Lasso
        if 'range' in list(selectedData.keys()):
            x = selectedData['range']['x']
            x = [x[0], x[1], x[1], x[0], x[0]]
            y = selectedData['range']['y']
            y = [y[0], y[0], y[1], y[1], y[0]]
            showlegend = True
            name = labelname + ' -box'
            shape_type = 'box'
        elif 'lassoPoints' in list(selectedData.keys()):
            x = selectedData['lassoPoints']['x']
            y = selectedData['lassoPoints']['y']
            if lasso_open:
                name = labelname + ' -line'
                shape_type = 'line'
            else:
                x.append(x[0])
                y.append(y[0])
                name = labelname + ' -polygon'
                shape_type = 'polygon'
            showlegend = True

        for trace_dict in fig['data']:
            if 'selectedpoints' in trace_dict:
                del trace_dict['selectedpoints']

        data = fig['data'] + [{
            'x': x,
            'y': y,
            'mode': 'markers+lines',
            'marker': {'opacity': 1, 'color': labelcolor},
            'showlegend': True,
            'name': name,
            'customdata': [{'shape_type': shape_type}],
            'hoverinfo': 'name',
            'visible': True,
            'line': {'color': labelcolor},
            'type': 'scattergl'
        }]

        layout_ = fig['layout']

    if trig_id == 'daq-booleanswitch-edit.on':
        if edit_boxes:
            index_shapes = 0
            for index, data_item in enumerate(data):
                if (data_item['customdata'][0]['shape_type'] == 'box') \
                    and (len(data_item['x']) == 5):
                    if  index_shapes != 0:
                        layout_['shapes'] = layout_['shapes'] + [
                            {
                                'type': 'rect',
                                'xref': 'x',
                                'yref': 'y',
                                'x0': data_item['x'][0],
                                'y0': data_item['y'][0],
                                'x1': data_item['x'][1],
                                'y1': data_item['y'][2],
                                'line': {
                                    'color': data_item['line']['color'],
                                    'dash': 'dot'
                                }
                            }
                        ]
                    else:
                        layout_['shapes'] = [
                            {
                                'type': 'rect',
                                'xref': 'x',
                                'yref': 'y',
                                'x0': data_item['x'][0],
                                'y0': data_item['y'][0],
                                'x1': data_item['x'][1],
                                'y1': data_item['y'][2],
                                'line': {
                                    'color': data_item['line']['color'],
                                    'dash': 'dot'
                                }
                            }
                        ]
                    index_shapes = index_shapes + 1
                    data[index]['visible'] = 'legendonly'
        else:
            index_shapes = 0
            for index, data_item in enumerate(data):
                if (data_item['customdata'][0]['shape_type'] == 'box') \
                    and (len(data_item['x']) == 5):
                    if shape_data is None:
                        data[index]['visible'] = True
                    else:
                        keys = [
                            f'shapes[{index_shapes}].x0',
                            f'shapes[{index_shapes}].y0',
                            f'shapes[{index_shapes}].x1',
                            f'shapes[{index_shapes}].y1'
                        ]
                        if keys[0] in shape_data:
                            data_item['x'][0] = shape_data[keys[0]]
                            data_item['y'][0] = shape_data[keys[1]]
                            data_item['x'][1] = shape_data[keys[2]]
                            data_item['y'][2] = shape_data[keys[3]]
                            data_item['x'][2] = data_item['x'][1]
                            data_item['x'][3] = data_item['x'][0]
                            data_item['x'][4] = data_item['x'][0]
                            data_item['y'][1] = data_item['y'][0]
                            data_item['y'][3] = data_item['y'][2]
                            data_item['y'][4] = data_item['y'][0]
                        index_shapes = index_shapes + 1
                        data[index]['visible'] = True
            try:
                del layout_['shapes']
            except KeyError:
                print("Key 'shape' not found")


    if trig_id == 'button-rect.n_clicks':
        layout_ = fig['layout']
        layout_['dragmode'] = 'select'
    elif trig_id == 'button-lasso.n_clicks':
        layout_ = fig['layout']
        layout_['dragmode'] = 'lasso'

    if trig_id == 'javascript-ctrl-click.event':
        df_labels = pd.DataFrame(label_data)
        # get the labelname from the table
        labelname = df_labels.loc[label_row_index[0], 'labels']
        # get the labelcolor from the table
        labelcolor = df_labels.loc[label_row_index[0], 'colors']
        name = labelname + ' -polygon'
        if lasso_open:
            name = labelname +' -line'
            shape_type = 'line'
        else:
            name = labelname + ' -polygon'
            shape_type = 'polygon'
        data_store = [{
            'x': [ctx.inputs['javascript-ctrl-click.event']['x']],
            'y': [ctx.inputs['javascript-ctrl-click.event']['y']],
            'mode': 'markers+lines',
            'marker': {'opacity': 1, 'color': labelcolor},
            'showlegend': True,
            'name': name,
            'customdata': [{'shape_type': shape_type}],
            'hoverinfo': 'name',
            'visible': True,
            'line': {'color': labelcolor},
            'type': 'scattergl'
        }]
        if ctx.states['polygon-data.data'] is None:
            if lasso_open:
                data = fig['data'] + data_store
            else:
                data_store[0]['x'] = data_store[0]['x'] + data_store[0]['x']
                data_store[0]['y'] = data_store[0]['y'] + data_store[0]['y']
                data = fig['data'] + data_store
        else:
            if lasso_open:
                data_store[0]['x'] = ctx.states['polygon-data.data'][0]['x'] \
                    + data_store[0]['x']
                data_store[0]['y'] = ctx.states['polygon-data.data'][0]['y'] \
                    + data_store[0]['y']
            else:
                data_store[0]['x'] = ctx.states['polygon-data.data'][0]['x'][:-1] \
                    + data_store[0]['x'] + [ctx.states['polygon-data.data'][0]['x'][0]]
                data_store[0]['y'] = ctx.states['polygon-data.data'][0]['y'][:-1] \
                    + data_store[0]['y'] + [ctx.states['polygon-data.data'][0]['y'][0]]

            data = fig['data'][:-1] + data_store

    else:
        data_store = None

    if trig_id == 'button-mlflow-single.n_clicks':
        # Load the model in 'python_function' format
        if mlflow_nclicks > 0:
            artifacts = mlflow.tracking.MlflowClient().list_artifacts(run_id=dropdwn_run_id)
            path = [artifact.path for artifact in artifacts if 'pyfunc' in artifact.path][0]
            df_select = pd.DataFrame(file_data)
            loaded_model = mlflow.pyfunc.load_model(
                model_uri=f'runs:/{dropdwn_run_id}/{path}'
            )
            # Evaluate the model
            filename = df_select.loc[filename_row_index[0], 'filename']
            up = urllib.parse.urlparse(layout_['images'][0]['source'])
            img_head, img_data = up.path.split(',', 1)
            img = PImage.open(BytesIO(base64.b64decode(img_data)))
            img_width, img_height = img.size
            df_img = pd.DataFrame(
                data=[base64.encodebytes(base64.b64decode(img_data))],
                columns=['image']
            )
            predictions = loaded_model.predict(df_img)
            # predictions_sampled = predictions[::10]
            df_labels = pd.DataFrame(label_data)
            labelcolor = df_labels.loc[label_row_index[0], 'colors']
            run_dict = mlflow.tracking.MlflowClient().get_run(run_id=dropdwn_run_id).to_dictionary()
            name = run_dict['data']['tags']['mlflow.runName'] + ' -model'
            shape_type = 'model'
            model_trace = go.Scattergl(
                x=predictions['x'],
                y=img_height-predictions['y'],
                mode='markers',
                marker={'opacity': 1, 'color': labelcolor},
                showlegend=True,
                name=name,
                customdata=[
                    {
                        'shape_type': shape_type,
                        'mlflow_path': path,
                        'mlflow_run_id': dropdwn_run_id
                    }
                ],
                hoverinfo='name',
                visible=True
            )
            data = fig['data'] + [model_trace]

    if (trig_id == 'button-remove-traces.n_clicks') and (remove_traces_nclicks > 0):
        data = fig['data']
        checklist_dict = {'visible': 'legendonly', 'showlegend': False}
        indices = []
        for index, data_item in enumerate(data):
            data_item_dict = {k: data_item.get(k, None) for k in checklist_dict}
            intersect_dict = set(checklist_dict.items()).intersection(set(data_item_dict.items()))
            if intersect_dict:
                indices = indices + [index]
        data = np.delete(data, indices).tolist()

    return go.Figure(data, layout_), f'Edit boxes {edit_boxes}', data_store


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


@app.callback(
    Output('report-model', 'children'),
    [Input('button-mlflow-batch', 'n_clicks')],
    [State('datatable-filenames', 'data'),
     State('datatable-labels', 'data'),
     State('datatable-labels', 'selected_rows'),
     State('dropdown-select-run', 'value')])
def mlflow_batch(n_clicks, file_data, label_data, label_row_index, dropdwn_run_id):
    '''Apply MLflow model to all files in datatable.'''
    if (n_clicks > 0) and (config.MLFLOW_URI is not None):
        df_select = pd.DataFrame(file_data)
        artifacts = mlflow.tracking.MlflowClient().list_artifacts(run_id=dropdwn_run_id)
        path = [artifact.path for artifact in artifacts if 'pyfunc' in artifact.path][0]
        df_labels = pd.DataFrame(label_data)
        labelcolor = df_labels.loc[label_row_index[0], 'colors']
        for index, row in df_select.iterrows():
            # Evaluate the model
            filename = row['filename']
            result = fs.get_last_version(filename)
            result_id = result._id
            # check if metadata model annotation already exists
            search_request = {
                '$and':
                    [
                        {'_id': result_id},
                        {'metadata.dash_img_annotation.customdata.mlflow_run_id': dropdwn_run_id}
                    ]
            }
            if not fs.exists(search_request):
                result_read = result.read()
                img = PImage.open(BytesIO(result_read))
                img_width, img_height = img.size
                df_img = pd.DataFrame(data=[base64.encodebytes(result_read)], columns=['image'])
                loaded_model = mlflow.pyfunc.load_model(
                    model_uri=f'runs:/{dropdwn_run_id}/{path}'
                )
                predictions = loaded_model.predict(df_img)
                run_dict = mlflow.tracking.MlflowClient().get_run(
                    run_id=dropdwn_run_id).to_dictionary()
                name = run_dict['data']['tags']['mlflow.runName'] + ' -model'
                shape_type = 'model'
                model_trace = {
                    'x': predictions['x'].tolist(),
                    'y': (img_height-predictions['y']).tolist(),
                    'mode': 'markers',
                    'marker': {'opacity': 1, 'color': labelcolor},
                    'showlegend': True,
                    'name': name,
                    'customdata': [
                        {
                            'shape_type': shape_type,
                            'mlflow_path': path,
                            'mlflow_run_id': dropdwn_run_id
                        }
                    ],
                    'hoverinfo': 'name',
                    'visible': True,
                    'type': 'scattergl'
                }

                if 'dash_img_annotation' in result.metadata:
                    data = result.metadata['dash_img_annotation'] + [model_trace]
                else:
                    data = [model_trace]

                db.fs.files.update_one(
                    {'_id': result_id}, {'$set': {'metadata.dash_img_annotation': data}}
                )
        return 'batch model completed'
    return ''


@app.callback(
    Output('dropdown-select-exp', 'options'),
    [Input('button-mlflow-connect', 'n_clicks')])
def mflow_connect(n_clicks):
    '''Display list of MLflow experiments in datatable.'''
    if (n_clicks > 0) and (config.MLFLOW_URI is not None):
        mlflow_experiments = mlflow.tracking.MlflowClient().list_experiments()
        return [{'label': ex.name, 'value': ex.name} for ex in mlflow_experiments]
    return []


@app.callback(
    [Output('dropdown-select-run', 'options'),
     Output('dropdown-select-run', 'value')],
    [Input('dropdown-select-exp', 'value')],
    [State('graph-image', 'figure')])
def dropdwn_exp(exp_name, fig):
    '''MLflow experiments drop-down menu.'''
    if (exp_name is not None) and ('images' in list(fig['layout'].keys())):
        exp = mlflow.tracking.MlflowClient().get_experiment_by_name(name=exp_name)
        runs = mlflow.tracking.MlflowClient().list_run_infos(experiment_id=exp.experiment_id)
        mlflow_run_opts = []
        for run in runs:
            tags = mlflow.tracking.MlflowClient().get_run(run.run_uuid).data.tags
            mlflow_run_opts = mlflow_run_opts + [
                {'label': tags['mlflow.runName'], 'value': run.run_uuid}
            ]
        return mlflow_run_opts, mlflow_run_opts[0]['value']
    return [], 'None'


@app.callback(
    Output('report-save', 'children'),
    [Input('button-save', 'n_clicks')],
    [State('datatable-filenames', 'data'),
     State('datatable-filenames', 'selected_rows'),
     State('graph-image', 'figure')])
def save_metadata(n_clicks, file_data, filename_row_index, fig):
    '''Save annotation metadata to MongoDB.'''
    save_stmt = ''
    if (n_clicks > 0) and filename_row_index:
        df_select = pd.DataFrame(file_data)
        filename = df_select.loc[filename_row_index[0], 'filename']
        id_ = df_select.loc[filename_row_index[0], '_id']
        comments = df_select.loc[filename_row_index[0], 'comments']
        data = fig['data']
        metadata = {}
        #metadata['saved_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        metadata['comments'] = comments
        metadata['dash_img_annotation'] = data
        db.fs.files.update_one({'_id': ObjectId(id_)}, {'$set': {'metadata':metadata}})
        save_stmt = 'saved metadata: ' + filename

    return save_stmt
