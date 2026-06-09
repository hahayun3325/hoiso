# OakInk Official Repo Reference

The official OakInk repository was cloned locally only for reference:

`third_party/OakInk`

Commit inspected:

`73dc7c8`

Important findings:

- `view_id=0 -> north_east_color`
- `view_id=1 -> south_east_color`
- `view_id=2 -> north_west_color`
- `view_id=3 -> south_west_color`

For OakInk split000:

`south_east_color_90.png -> view_id=1`

The official docs state:

- `hand_j`: 21x3 hand joints in camera space
- `hand_v`: 778x3 hand vertices in camera space
- `cam_intr`: 3x3 camera intrinsics matrix K
- `obj_transf`: 4x4 object transformation matrix `T_c_o`, from object canonical space to camera space
