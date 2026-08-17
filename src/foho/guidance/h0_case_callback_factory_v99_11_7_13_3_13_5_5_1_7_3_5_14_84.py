import importlib
import json
from pathlib import Path

CONTROLLER_MODULE="foho.guidance.run_d0_h0_transactional_v99_11_7_13_3_13_5_5_1_7_3_5_14_77"
RUNTIME_MODULE="foho.guidance.h0_live_phase1_runtime_v99_11_7_13_3_13_5_5_1_7_3_5_14_77"

def create_case_callback(phase_config_path, output_path, updates=0, backward_only=True, capture_only=False):
    controller=importlib.import_module(CONTROLLER_MODULE)
    runtime_owner=importlib.import_module(RUNTIME_MODULE)
    config=controller.phase_loader.load_phase_config(str(phase_config_path),'H0_global_hand_Rt')
    output=Path(output_path)
    state={'invocations':0}
    def callback(live_context):
        state['invocations']+=1
        if state['invocations']!=1: raise RuntimeError('H0_case_callback_must_be_invoked_exactly_once')
        if not isinstance(live_context,dict): raise TypeError('live_context_must_be_dictionary')
        required={'owner','parameters','frozen','compute_base_loss','hooks','metadata'}
        missing=sorted(required-set(live_context))
        if missing: raise RuntimeError(f'incomplete_live_context:{missing}')
        runtime=runtime_owner.create_from_live_context(live_context,config)
        result=controller.run_live(config,runtime,int(updates),checkpoint_every=1,capture_only=bool(capture_only),backward_only=bool(backward_only))
        if output.exists(): raise FileExistsError(str(output))
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,indent=2,default=str)+'\n')
        return {'handled':True,'result':result}
    callback.binding={'phase_config':str(phase_config_path),'output':str(output),'updates':int(updates),'backward_only':bool(backward_only),'capture_only':bool(capture_only)}
    return callback
