import torch

def dense_valid_zorder_loss(hand_depth, object_depth, object_only_mask, contact_exempt_mask=None, margin=0.0, object_diagonal=1.0):
    """Object-only occlusion loss for positive camera depth d=-z.

    At a valid object-only pixel, hand depth must be at least object depth plus
    margin. Invalid or D0-contact-exempt pixels have exactly zero weight.
    """
    if hand_depth.shape != object_depth.shape or hand_depth.shape != object_only_mask.shape:
        raise ValueError('hand/object depth and mask shapes must match')
    if contact_exempt_mask is None:
        contact_exempt_mask=torch.zeros_like(object_only_mask,dtype=torch.bool)
    if contact_exempt_mask.shape != object_only_mask.shape:
        raise ValueError('contact exemption shape must match')
    scale=torch.as_tensor(object_diagonal,dtype=hand_depth.dtype,device=hand_depth.device)
    if not bool(torch.isfinite(scale).item()) or float(scale.detach().cpu())<=0:
        raise ValueError('object_diagonal must be finite and positive')
    valid=(object_only_mask.bool() & ~contact_exempt_mask.bool() & torch.isfinite(hand_depth) & torch.isfinite(object_depth) & (hand_depth>0) & (object_depth>0))
    candidate=(object_only_mask.bool() & ~contact_exempt_mask.bool())
    safe_hand=torch.where(valid,hand_depth,torch.zeros_like(hand_depth))
    safe_object=torch.where(valid,object_depth,torch.zeros_like(object_depth))
    violation=torch.relu((safe_object + float(margin) - safe_hand)/scale)
    loss=violation[valid].mean() if bool(valid.any().item()) else hand_depth.sum()*0.0
    facts={'valid_count':int(valid.sum().item()),'candidate_count':int(candidate.sum().item()),'coverage':float(valid.sum().item()/max(int(candidate.sum().item()),1)),'invalid_weight_is_zero':True,'depth_convention':'positive_d_equals_minus_z'}
    return loss,valid,facts
