from collections.abc import Mapping
import torch

REQUIRED_PARAMETER_NAMES={'global_hand_rotation','global_hand_translation'}
REQUIRED_OWNER_NAMES={'frozen_state','object_vertices','rasterize_object','compute_loss',
                      'gate_pass','snapshot','restore','save_checkpoint','capture'}
REQUIRED_HOOK_NAMES=REQUIRED_OWNER_NAMES|{'build_optimizer'}

def build_complete_h0_hooks(parameters, owners, learning_rate):
    if not isinstance(parameters,Mapping) or set(parameters)!=REQUIRED_PARAMETER_NAMES:
        raise ValueError(f'H0_parameters_must_be_exact_global_Rt:{sorted(parameters) if isinstance(parameters,Mapping) else type(parameters).__name__}')
    if not isinstance(owners,Mapping):
        raise TypeError('owners_must_be_mapping')
    missing=sorted(REQUIRED_OWNER_NAMES-set(owners))
    extra=sorted(set(owners)-REQUIRED_OWNER_NAMES)
    if missing or extra:
        raise ValueError({'missing_owners':missing,'extra_owners':extra})
    for name in REQUIRED_PARAMETER_NAMES:
        value=parameters[name]
        if not hasattr(value,'requires_grad_') or not hasattr(value,'detach'):
            raise TypeError(f'parameter_not_live_tensor:{name}')
    for name in REQUIRED_OWNER_NAMES:
        if not callable(owners[name]):
            raise TypeError(f'owner_not_callable:{name}')
    lr=float(learning_rate)
    if not (lr>0.0):
        raise ValueError('learning_rate_must_be_positive')
    def build_optimizer(selected):
        if not isinstance(selected,Mapping) or set(selected)!=REQUIRED_PARAMETER_NAMES:
            raise ValueError('selected_parameters_must_be_exact_global_Rt')
        for name in REQUIRED_PARAMETER_NAMES:
            if selected[name] is not parameters[name]:
                raise RuntimeError(f'selected_parameter_identity_mismatch:{name}')
        return torch.optim.Adam([selected['global_hand_rotation'],selected['global_hand_translation']],lr=lr)
    hooks=dict(owners); hooks['build_optimizer']=build_optimizer
    if set(hooks)!=REQUIRED_HOOK_NAMES:
        raise RuntimeError('complete_hook_set_not_exact')
    return hooks
