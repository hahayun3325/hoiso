import torch

def freeze_then_enable(named_parameters, enabled_names):
    rows=list(named_parameters); names=[name for name,_ in rows]
    if len(names)!=len(set(names)): raise ValueError('duplicate live parameter name')
    requested=list(enabled_names); missing=sorted(set(requested)-set(names))
    if missing: raise KeyError(f'unknown live parameters: {missing}')
    for _,parameter in rows: parameter.requires_grad_(False)
    enabled=[]
    for name,parameter in rows:
        if name in requested: parameter.requires_grad_(True); enabled.append(parameter)
    if len(enabled)!=len(requested): raise RuntimeError('allowlist binding is not one-to-one')
    return enabled,{'enabled':requested,'frozen':sorted(set(names)-set(requested))}

def register_flat_gradient_mask(parameter, flat_indices):
    if not parameter.requires_grad: raise ValueError('parameter must require gradients before registering a mask')
    total=parameter.numel(); indices=sorted(set(int(x) for x in flat_indices))
    if not indices or indices[0]<0 or indices[-1]>=total: raise ValueError('gradient-mask indices out of range or empty')
    mask=torch.zeros(total,dtype=parameter.dtype,device=parameter.device); mask[indices]=1
    handle=parameter.register_hook(lambda gradient: gradient.reshape(-1).mul(mask).reshape_as(gradient))
    return handle,mask.reshape_as(parameter)

def assert_frozen_unchanged(before,after,frozen_mask,atol=0.0):
    delta=(after-before).abs(); changed=delta[frozen_mask.bool()]
    maximum=float(changed.max().detach().cpu()) if changed.numel() else 0.0
    if maximum>float(atol): raise AssertionError(f'frozen parameter changed: {maximum}')
    return maximum
