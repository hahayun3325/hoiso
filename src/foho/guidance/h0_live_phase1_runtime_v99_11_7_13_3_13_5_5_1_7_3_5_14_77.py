from pathlib import Path

REQUIRED_PARAMETERS={'global_hand_rotation','global_hand_translation'}
REQUIRED_HOOKS={'frozen_state','object_vertices','rasterize_object','build_optimizer','compute_loss','gate_pass','snapshot','restore','save_checkpoint','capture'}

class LivePhase1Runtime:
    def __init__(self,parameters,hooks,metadata=None):
        missing_parameters=sorted(REQUIRED_PARAMETERS-set(parameters)); missing_hooks=sorted(REQUIRED_HOOKS-set(hooks))
        if missing_parameters or missing_hooks: raise ValueError({'missing_parameters':missing_parameters,'missing_hooks':missing_hooks})
        self._parameters=dict(parameters); self._hooks=dict(hooks); self.metadata=dict(metadata or {})
        for name,value in self._parameters.items():
            if not hasattr(value,'requires_grad_') or not hasattr(value,'detach'): raise TypeError(f'parameter_is_not_live_tensor:{name}')

    def parameter_registry(self): return self._parameters
    def frozen_state(self): return self._hooks['frozen_state']()
    def object_vertices(self): return self._hooks['object_vertices']()
    def rasterize_object(self,vertices): return self._hooks['rasterize_object'](vertices)
    def build_optimizer(self,selected): return self._hooks['build_optimizer'](selected)
    def compute_loss(self,raster,config): return self._hooks['compute_loss'](raster,config)
    def gate_pass(self,metrics): return self._hooks['gate_pass'](metrics)
    def snapshot(self): return self._hooks['snapshot']()
    def restore(self,snapshot): return self._hooks['restore'](snapshot)
    def save_checkpoint(self,step,metrics): return self._hooks['save_checkpoint'](step,metrics)
    def capture(self,step,raster): return self._hooks['capture'](step,raster)

def create_from_live_context(context,phase_config):
    if not isinstance(context,dict): raise TypeError('live_context_must_be_dictionary')
    return LivePhase1Runtime(context.get('parameters',{}),context.get('hooks',{}),{'phase':phase_config.get('phase'),'sources':phase_config.get('sources',{}),'context_owner':context.get('owner')})

def create_runtime(args,remaining,config):
    raise RuntimeError('external_factory_cannot_own_private_Phase1_locals_use_opt_in_synchronous_live_callback')
