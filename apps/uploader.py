#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
from io import BytesIO
import zipfile
from PIL import Image as PImage
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from pymongo import MongoClient
import gridfs

from apps import config
from app import app


client = MongoClient(config.MONGODB_CONNECT_STRING)
db = client[config.MONGODB_DATABASE]
fs = gridfs.GridFS(db)


layout = html.Div(
    [
        html.H1('Upload Images to MongoDB'),
        html.Div([
            dcc.Input(
                id='input-comments',
                placeholder='Add comments',
                type='text',
                value=''
            )
        ]),
        html.Br(),
        dcc.Upload(
            id='upload-data',
            children=html.Div(
                ['Drag and drop or click to select image(s) or zipped images to upload.']
            ),
            style={
                'width': '100%',
                'height': '100px',
                'lineHeight': '100px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px',
            },
            multiple=True,
        ),
        html.H2('File List'),
        html.Ul(id='file-list'),
    ], className='five columns',
)


def extract_zip(data):
    input_zip = zipfile.ZipFile(BytesIO(data))
    return {name: input_zip.read(name) for name in input_zip.namelist()}


def save_file(name, content, comments):
    '''Decode and store a file uploaded with Plotly Dash.'''
    files = []
    metadata = {}
    metadata['comments'] = comments
    filename = name.split('.')[0]
    data = content.encode('utf8').split(b';base64,')[1]
    data = base64.decodebytes(data)

    if name.split('.')[-1] == 'zip':
        zipped_contents = zipfile.ZipFile(BytesIO(data))
        for _name in zipped_contents.namelist():
            filename = _name.split('.')[0:-1]
            try:
                img = PImage.open(BytesIO(zipped_contents.read(_name)))
                content_type = img.get_format_mimetype()
                image_id = fs.put(
                    data=BytesIO(zipped_contents.read(_name)).getvalue(),
                    content_type=content_type,
                    filename=filename[0],
                    metadata=metadata
                )
                files.append(_name)
            except: IOError
    else:
        img = PImage.open(BytesIO(data))
        content_type = img.get_format_mimetype()

        image_id = fs.put(
            data=data,
            content_type=content_type,
            filename=filename,
            metadata=metadata
        )
        files.append(name)
    return files


@app.callback(
    Output('file-list', 'children'),
    [Input('upload-data', 'filename'),
     Input('upload-data', 'contents')],
    [State('input-comments', 'value')])
def update_output(uploaded_filenames, uploaded_file_contents, comments):
    '''Save uploaded files and regenerate the file list.'''
    files = []
    if uploaded_filenames is not None and uploaded_file_contents is not None:
        for name, data in zip(uploaded_filenames, uploaded_file_contents):
            if name.split('.')[-1] != 'zip':
                _ = save_file(name, data, comments)
                files.append(name)
            else:
                files = save_file(name, data, comments)

    if not files:
        return [html.Li('No files yet!')]
    return [html.Li(filename) for filename in files]
