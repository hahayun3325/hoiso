import torch

def interpolate_metric_face_depth(pix_to_face, bary_coords, faces, vertex_metric_depth, layer=0):
    """Interpolate supplied camera-space vertex depth over visible packed faces.

    The caller owns the signed-camera convention and metric units. This function
    performs no inverse-depth conversion, normalization, detach, or device move.
    """
    if pix_to_face.ndim+1 != bary_coords.ndim or bary_coords.shape[-1] != 3:
        raise ValueError('fragment_shape_mismatch')
    if pix_to_face.shape != bary_coords.shape[:-1]:
        raise ValueError('fragment_prefix_mismatch')
    if faces.ndim != 2 or faces.shape[-1] != 3:
        raise ValueError('faces_must_be_F_by_3')
    if vertex_metric_depth.ndim != 1:
        raise ValueError('vertex_metric_depth_must_be_vector')
    if layer < 0 or layer >= pix_to_face.shape[-1]:
        raise ValueError('invalid_layer')
    face_id=pix_to_face[...,layer]
    bary=bary_coords[...,layer,:]
    valid_face=face_id.ge(0)
    safe_face=face_id.clamp_min(0)
    vertex_ids=faces[safe_face]
    triangle_depth=vertex_metric_depth[vertex_ids]
    depth=(triangle_depth*bary).sum(dim=-1)
    valid=valid_face & torch.isfinite(depth)
    depth=torch.where(valid,depth,torch.zeros_like(depth))
    return depth,valid
