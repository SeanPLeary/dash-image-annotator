# dash-image-annotator

Image Annotator Web-app using Plotly-Dash, MongoDB, and MLflow

## Main Task List:

- [x] multi-page web-app
  - [x] image uploader to external MongoDB
    - [x] ingest selected images
    - [x] ingest zipped images
  - [x] annotator
    - [x] query/display images from external MongoDB
    - [x] manual annotation (save to external MongoDB)
      - [x] box
        - [x] editable
      - [x] free-hand lasso
        - [x] opened/closed
      - [x] polygon-lasso (Ctrl+MouseClick)
        - [x] opened/closed
    - [x] DeepLearning model prediction (pyfunc models on MLflow server)
      - [x] one image at a time
      - [x] batch process
- [ ] Dockerfile
- [ ] Tests
- [ ] Jupyter example notebooks:
  - [ ] database interaction
  - [ ] create train/validation splits with masks
  - [ ] upload images with pre-existing masks

## Built With:

1. python (version=3.6.7)
2. [Plotly-Dash](https://dash.plot.ly/)
3. [Visdcc](https://github.com/jimmybow/visdcc)
4. [MongoDB/GridFS](https://api.mongodb.com/python/current/api/gridfs/index.html)
5. [MLflow](https://mlflow.org/)
6. [Pillow](https://pillow.readthedocs.io/en/stable/)

## Step-By-Step Guide:

TODO

### References:

1. [Example: Upload and Download Files with Plotly Dash](https://docs.faculty.ai/user-guide/apps/examples/dash_file_upload_download.html)
2. [Visdcc](https://github.com/jimmybow/visdcc)
