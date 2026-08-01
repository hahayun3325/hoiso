# alapuse02v6n60 raw object preflight

Mask decision:
  PASS_MASK_PREFLIGHT_V6

Raw Hunyuan decision:
  PASS_RAW_HUNYUAN_OBJECT_PREFLIGHT_WITH_LOCAL_OCCLUSION_ARTIFACTS

Evidence:
  - positive-only segmentation prompt selected the laptop;
  - screen/lid and keyboard/base are present;
  - hands and support box are excluded;
  - raw Hunyuan mesh is a recognizable open laptop;
  - mesh has one connected watertight component;
  - local front-edge defects do not block screen/base decomposition.

Next:
  run PartField and inspect N=2 as the primary screen/base candidate.
