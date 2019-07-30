#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys


# Host and Port of image-annotator/uploader web-app
HOST = os.environ.get('HOST', '127.0.0.1')
PORT = os.environ.get('PORT', 8050)


# Optional. Example: http://127.0.0.1:5000
MLFLOW_URI = os.environ.get('MLFLOW_URI')


try:
    # Example: mongodb://user:password@xx.xxx.xxx.xx:port
    MONGODB_CONNECT_STRING = os.environ['MONGODB_CONNECT_STRING']
except KeyError:
    print('Please set the environment variable MONGODB_CONNECT_STRING')
    sys.exit(1)


try:
    # Database name
    MONGODB_DATABASE = os.environ['MONGODB_DATABASE']
except KeyError:
    print('Please set the environment variable MONGODB_DATABASE')
    sys.exit(1)


# Annotation labels
DEFAULT_LABELS = {
    'labels': ['label_1', 'label_2', 'label_3', 'label_4'],
    'colors': ['rgb(255,0,0)', 'rgb(0,255,0)', 'rgb(0,0,255)', 'rgb(255,0,255)']
}


# Set image display height in pixels
#  - images will be displayed with this height while maintaining the aspect ratio
IMG_DISPLAY_HEIGHT = 512
