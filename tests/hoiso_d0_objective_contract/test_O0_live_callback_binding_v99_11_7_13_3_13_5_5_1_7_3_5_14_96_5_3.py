import importlib.util,json,os
from pathlib import Path

binder_path=Path(os.environ['O0_BINDER_UNDER_TEST']); out=Path(os.environ['O0_BINDING_CPU_RECEIPT'])
spec=importlib.util.spec_from_file_location('_o0_binding_under_test',binder_path)
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
sentinel=object(); calls={'binder':0,'run':0}; observed={}; errors=[]; original=module.run_live; checks={}
def binder(context):
    calls['binder']+=1; bound=dict(context); bound['o0_runtime']=sentinel; return bound
def fake_run(runtime,attempts=0,checkpoint_every=1,capture_only=False,backward_only=False):
    calls['run']+=1; observed.update({'runtime_identity':runtime is sentinel,'attempts':attempts,
      'checkpoint_every':checkpoint_every,'capture_only':capture_only,'backward_only':backward_only})
    return {'updates_completed':0,'attempts_completed':0,'rolled_back':False,'capture':{'step':0},
      'gradient_stats':{},'metrics':{},'trajectory':[]}
try:
    module.run_live=fake_run
    callback=module.BoundO0Callback(
      binder,attempts=0,backward_only=True,capture_only=False,terminate=False)
    outcome=callback({'owner':'raw_live_fixture'})
    second_rejected=False
    try: callback({'owner':'second_fixture'})
    except RuntimeError as exc: second_rejected=str(exc)=='O0_context_may_be_bound_once'
    checks={'raw_context_bound_once':calls['binder']==1,'runtime_called_once':calls['run']==1,
      'bound_runtime_identity_preserved':observed.get('runtime_identity') is True,
      'backward_arguments_exact':observed=={'runtime_identity':True,'attempts':0,'checkpoint_every':1,'capture_only':False,'backward_only':True},
      'handled_result_returned':outcome.get('handled') is True and outcome.get('result',{}).get('updates_completed')==0,
      'second_binding_rejected':second_rejected}
    failed=[name for name,value in checks.items() if not value]
    payload={'decision':('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_96_5_3_O0_live_binding_CPU_closed' if not failed else
      'review_required_v99_11_7_13_3_13_5_5_1_7_3_5_14_96_5_3_recheck_O0_live_binding_CPU'),
      'checks':checks,'failed':failed,'errors':errors,'GPU_used':False,'optimizer_updates':0}
    if not out.exists(): out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+'\n')
except Exception as exc: errors.append(f'{type(exc).__name__}:{exc}')
finally: module.run_live=original
print(json.dumps(json.loads(out.read_text()) if out.is_file() else
 {'decision':'hold_before_14_96_5_3_O0_live_binding_CPU','checks':checks,'errors':errors}))
