# Smoke 019 — Exact Fragmentation Root Diagnosis

## Main finding

Smoke 019 locates the root of the fragmented object mesh.

The object is already fragmented in:

debug_obj_before_hunyuan2moge.ply

## Root stage

The root is the final guided object latent/SDF extraction stage:

debug_obj_latent_x1 = self.scheduler.step_final(noise_pred_obj, t, obj_latents)debug_obj_pred_sdf = latent2sdf(debug_obj_latent_x1, xyz_samples, grid_size, self.vae, device)debug_obj_verts, debug_obj_faces, _ = flexi(...)

## Interpretation

The structured prompt successfully improves the inpainted object and Hunyuan initial mesh.

However, final Hunyuan guidance damages the object latent/SDF and extracts a fragmented object mesh.

The transforms only preserve the already-fragmented mesh. The final post-processing removes small floaters but cannot restore completeness.

## Research implication

This supports the HOLDSE-Flow idea that a pipeline needs stage-wise confidence checking.

A later output is not always better than an earlier output.

The system should include:

- object completeness checking
- semantic drift diagnosis
- 2D–3D consistency verification
- confidence-guided fallback
- object-preserving guidance
- contact-aware refinement that does not sacrifice object geometry  
