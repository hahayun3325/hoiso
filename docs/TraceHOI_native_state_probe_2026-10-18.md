# TraceHOI native visual-state probe

The visual initializer already scales and places the saved HaMeR hand relative to the laptop using image, bounding-box and fresh-depth cues. It must not optimize contact or reject an initial pose using contact metrics. Contact belongs to the later joint rectified-flow stage.

X8 published the camera adapter at `7c4c5005dfd194e56d844514df24445936eae86b`. Its native CPU check verified 38,661 projected points (maximum difference 0.000030517578125 pixels), exact 32-pixel raster coverage, depth and finite projection gradients. The legacy fixture missed pixel (21,14) on a shared triangle edge; the corrected fixture has no tied pixel centers. X8 archived and trashed the V6/W7 working trees after verified publication. The original terminals and complete archives remain evidence.

## New behavior

`native_state_probe` prepares a 512×512 RGBA laptop conditioning image from the saved object-only mask. Retained RGB bytes are identical to the original image; all other pixels are white with zero alpha. Hand-only and ambiguous-overlap pixels are excluded. Conditioning uses the image mask (30,951 pixels), not the narrower depth-valid support (30,949 pixels). No source crop, resize, source-mask change, model preprocessing or conditioning encoder call occurs.

An explicit CPU probe uses the actual PyTorch3D PLY loader and exactly three functions extracted from hash-bound backend sources: the centered scale/rotation/translation function, the native-object-to-scene transform, and `get_guidance_params`. It does not import the Hunyuan pipeline module. The hand uses the existing opt-in `_HandState` and does not receive the object transform.

The probe compares all 778 hand vertices and all 75,002 object vertices to their saved scene meshes, within 2e-6 in scene units. Joint phase 2 must create seven independent leaf tensors with unchanged values. A small synthetic velocity tensor exercises helper cloning; it is not a model output or reusable latent. A numerical squared-value expression verifies finite autograd through the transform parameters; it is not a contact or fitting objective. No optimizer is constructed or stepped. Original tensors and files are rechecked afterward. Pillow RGBA decoding and OpenCV mask decoding must reproduce exact bytes.

## API and limits

The build/verify CLI is `tools/tracehoi/run_native_state_probe.py`, with explicit `--purpose native_state_probe`. The `cpu-preflight` action requires a separately bounded native interpreter and emits a result JSON even after a handled failure. The offline viewer shows the image pair, stage explanations, and accepts a result JSON only for matching runtime and conditioning bindings.

Native state execution is a separate claim from native camera execution and full backend execution. This change does not establish `native_execution_verified`, `backend_execution_ready`, mask accuracy, metric scale, physical contact, final placement or full-parent acceptance. `contact_terms_used` remains false. The installed third-party sources are unchanged.

The saved object PLY is not a diffusion latent. No bound latent was saved with this handoff; fresh random noise would regenerate the object. Encoding or inversion and the model's conditioning preprocessing must be validated before choosing a shape-refinement path. Full-scene renderer behavior and the HaMeR joint-regressor asset also remain runtime dependencies.

## Validation and manual server workflow

The prepared addition includes 27 standard-library tests covering image support, independent PNG decoding, changed source rejection, exact output receipts, prior-camera evidence, scope claims and mutation refusal. Existing 483 tests run before and after installation, followed by real-bundle CLI verification. Local integration fixtures explicitly mock native execution; only a successful server preflight establishes the native-state result.

One CPU preflight is allowed: 90 seconds wall time, 60 CPU seconds, 8 GiB address space, one numerical thread, hidden GPUs, no network/subprocess operations from the native worker, model, checkpoint, installation or retry. After the native check, source checks, tests and normal publication succeed, the server script verifies a replacement archive, archives the entire exact X8 tree and moves only that tree to Trash. Unknown files stop retirement. Retain original run guards, evidence archives, human review, input files and partial Y9 outputs. Manual transfer only.
