# Phase 0.9 — Manual Asset Verification

## Goal

Verify that all manually required assets for FollowMyHold are present, valid, and loadable.

## Verified assets

The following required assets are present:

third_party/estimator/hand_object_detector/data/pretrained_model/resnet101_caffe.pth
third_party/estimator/hand_object_detector/models/res101_handobj_100K/pascal_voc/faster_rcnn_1_8_89999.pth
third_party/estimator/hamer/_DATA/data/mano/MANO_RIGHT.pkl
third_party/estimator/wilor_ckpt/detector.pt

## Important correction

The first downloaded `resnet101_caffe.pth` was actually an HTML page from Dropbox. It was replaced using the Zenodo download.

Final verified md5:

508530030bf473c7a976e922d69abaef

## Checkpoint loading

- `resnet101_caffe.pth`: load OK
- `faster_rcnn_1_8_89999.pth`: load OK
- `MANO_RIGHT.pkl`: present
- `detector.pt`: required `dill`; after installing `dill`, it should be loadable

## Decision

Phase 0.9 passed after verifying all required assets and removing temporary downloaded archives.  
