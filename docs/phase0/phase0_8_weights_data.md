# Phase 0.8 — Fetch Bundled Weights / Data

## Goal

Fetch FollowMyHold bundled weights/data and identify remaining manual assets.

## Initial issue

The first fetch attempt failed because:

- `scripts/fetch_data.sh` had a shell parsing issue at line 1.
- `gdown` failed because `bs4` / BeautifulSoup was missing.

## Repair

The environment was repaired by installing:

- `beautifulsoup4`
- `bs4`

The fetch script header was inspected and fixed if needed.

## Required asset checklist

The required assets are:

third_party/estimator/hand_object_detector/data/pretrained_model/resnet101_caffe.pth
third_party/estimator/hand_object_detector/models/res101_handobj_100K/pascal_voc/faster_rcnn_1_8_89999.pth
third_party/estimator/hamer/_DATA/data/mano/MANO_RIGHT.pkl
third_party/estimator/wilor_ckpt/detector.pt

## Important note

Some assets may require manual download, especially `MANO_RIGHT.pkl`.  
Large model files and licensed assets must not be committed to GitHub.  
