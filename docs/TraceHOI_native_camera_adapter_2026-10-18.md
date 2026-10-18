# Native camera and numeric guidance adapter

The CPU initializer scales and places the saved HaMeR hand relative to the laptop using visual cues, the hand box and fresh scene depth. Contact belongs to subsequent joint rectified-flow optimization. This adapter preserves the initializer, masks and articulation.

The unpublished W7 attempt stopped at its CPU raster fixture before any repository additions. The returned ZIP and original terminal are authenticated. Its real-point camera projection and gradient checks were reached and passed before the raster assertion. W7 recorded no observed pixel mask, so the precise failing pixels cannot be recovered from that run.

## Recovery of the raster test

W7's two square quads put eight integer pixel centers exactly on shared triangle diagonals. The PyTorch3D CPU implementation defines triangle interiors using strictly positive barycentric coordinates, leaving exact-edge inclusion sensitive to floating point arithmetic. This is a defect in the fixture for a camera-calibration assertion; it does not establish that the camera mapping is wrong.

X8 retains the camera factory, projection convention, mesh inputs and tolerances. It shifts each synthetic quad vertically by -1/8 pixel. The analytic full-image mask remains exactly 32 pixels, while every pixel center is more than 0.08 pixels from every triangle edge. Tests still reject half-pixel shifts. This is not permission to accept holes in the recovery fixture.

The native preflight renders both the original fixture (diagnostic only) and the recovery fixture (strict acceptance). It records expected and observed masks, missing and extra pixels, edge margins, versions, projection errors and numeric decoding results. Failures now save native_preflight.json as well as stderr. Old-fixture edge failures and other deviations are distinguished in the record; no native result is invented locally.

## Camera and numeric guidance

The saved camera uses integer-center OpenCV pixels. Scene coordinates are x-right, y-up, z-backward. The PyTorch3D camera receives R=diag(-1,1,-1), T=0, fresh focal lengths and a +0.5 principal-point shift for pixel-cell raster sampling. Only transform_points_screen subtracts 0.5 from its x/y result, preserving the original HaMeR keypoint convention. Raster transforms retain the shift.

The strict numeric loader accepts the bound 21x2 float32 NPY array and returns mano_2d_kps. It rejects other paths, changed bytes, object arrays, non-finite numbers and shape changes. The opt-in private overlay uses no pickle. Legacy behavior and installed third-party sources remain unchanged.

The recorded shader uses world-space vertex normals and global min/max normalization. The preflight checks mesh face-normal orientation, not execution of that shader.

## Verification and scope

Run tools/tracehoi/check_native_camera_adapter.py for 34 deterministic tests. X8 runs 483 code checks before and after installing the five additions, plus real-bundle comparison. Its native CPU preflight runs once, before installation, within 90 seconds wall time, 60 CPU seconds and 8 GiB address space. GPU visibility is disabled, CPU tensors are explicit, and no checkpoints, Hunyuan pipeline or model forward pass are used.

The offline index includes RGB/HaMeR inspection, an unchanged orbit scene and expected/observed/difference raster views. Local previews show analytic expected pixels only. Load actual native_preflight.json to see server observations.

Native camera success does not certify full backend execution. Object conditioning/latent initialization, asset checks and bounded joint rectified-flow execution remain pending. Independent reference annotation and metric scale remain unverified. Backend execution, rectified flow, contact terms, placement and full parent acceptance remain false.

After verified publication and a verified replacement archive, X8 archives the complete V6 and failed W7 trees before moving them to Trash. Unknown files stop retirement. Original terminals, full archives, original inputs and the human review are retained.

Sources: [PyTorch3D cameras](https://pytorch3d.org/docs/cameras) and [CPU rasterization implementation](https://raw.githubusercontent.com/facebookresearch/pytorch3d/main/pytorch3d/csrc/rasterize_meshes/rasterize_meshes_cpu.cpp).
