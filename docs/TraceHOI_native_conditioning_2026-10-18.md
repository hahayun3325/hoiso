# Native conditioning and scheduler contract

The CPU initialization uses image evidence, HaMeR, the hand bounding box and fresh scene depth. Contact is deferred to later joint rectified-flow optimization. Y9 verified the native state transforms on the server (maximum hand/object discrepancy 4.77e-7 scene units, zero optimizer steps).

This addition prepares and verifies the exact native Hunyuan ImageProcessorV2 conditioning on the existing laptop RGBA. The original scene camera, meshes, masks and human review bytes remain unchanged. It compares Pillow and OpenCV input paths, independent crop/resize/composite reconstruction, RGB and alpha normalization and tensor dimensions. The native maximum occupied row and column are excluded by its half-open crop; the adapter preserves that installed behavior rather than silently correcting it.

A four-step deterministic synthetic velocity tensor checks the pinned scheduler's ascending sigma convention, endpoint equation, non-advancing preview, index changes and finite gradients. The RNG must remain unchanged. This does not execute a model, sample a model latent, run scene optimization or verify physical contact.

The pinned ShapeVAE source exposes __init__, forward and latents2mesh, with no mesh encoder. The native joint loop invokes prepare_latents with no supplied saved latent. A saved mesh therefore does not establish a reusable diffusion latent. Before claiming preservation of the laptop shape during joint flow, validate a latent restart or inversion path. The VAE and joint pipeline are parsed as text only in this step.

Build and verify are standard-library operations. The explicit CPU preflight executes only hash-bound preprocessor and scheduler modules, using the existing Torch, NumPy, Pillow, OpenCV, einops and diffusers installation. It has a 90-second wall, 60-second CPU and 8 GiB address-space bound. No downloads, installation, GPU, model weights, contact objective or native third-party edits occur.

Preparation never claims native conditioning execution. A successful native result has its own binding, processed images and tensors. backend_execution_ready and placement_ready stay false. The full scene renderer, joint regressor, model/latent path and bounded joint-flow execution remain subsequent work.

The manual carrier authenticates the exact Y9 return and terminal, verifies the recorded repository base, tests five exact new additions before and after installation and pushes normally. Cleanup archives and verifies the complete Y9 tree before moving only that tree to Trash. Original terminals, human review JSON, source inputs and evidence archives are retained. Unknown or changed files stop cleanup. Collector copies only verified outputs, refusing to replace different Downloads files.
