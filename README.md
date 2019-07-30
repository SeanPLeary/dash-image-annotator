# dash-image-annotator

Image Annotator Web-app using Plotly-Dash, MongoDB, and MLflow

## Task List:

- [ ] multi-page web-app
  - [ ] image uploader to external MongoDB
    - [ ] ingest selected images
    - [ ] ingest zipped images
  - [ ] annotator
    - [ ] query/download images from external MongoDB
    - [ ] manual annotation (save to external MongoDB)
      - [ ] box
        - [ ] editable
      - [ ] free-hand lasso
        - [ ] opened/closed
      - [ ] polygon-lasso (Ctrl+MouseClick)
        - [ ] opened/closed
    - [ ] DeepLearning model prediction (pyfunc models on MLflow server)
      - [ ] one image at a time
      - [ ] batch process
- [ ] Dockerfile
- [ ] Tests
- [ ] Jupyter example notebooks:
  - [ ] database interaction
  - [ ] create train/validation splits with masks
  - [ ] upload images with pre-existing masks

## Build With:

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
