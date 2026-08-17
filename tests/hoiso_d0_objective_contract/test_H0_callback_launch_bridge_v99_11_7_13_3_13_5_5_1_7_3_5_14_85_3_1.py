import importlib.util, json, os
from pathlib import Path

spec=importlib.util.spec_from_file_location('h0_bridge_148531',os.environ['LAUNCH_BRIDGE8531'])
bridge=importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)
target_path=Path(os.environ['BRIDGE_TEST_RECEIPT8531'])
existing=[str(target_path)] if target_path.exists() else []
errors=[]; failed=[]; checks={}; calls={'target':0,'callback_identity':False}
try:
    sentinel=object()
    def callback(context): return {'handled':True,'context':context}
    def fake_target(value,*,h0_live_callback=None):
        calls['target']+=1; calls['callback_identity']=h0_live_callback is callback
        return h0_live_callback({'value':value,'sentinel':sentinel})
    result=bridge.invoke_callback_capable_target(fake_target,callback,{'value':7})
    duplicate_rejected=False
    try: bridge.invoke_callback_capable_target(fake_target,callback,{'value':7,'h0_live_callback':callback})
    except ValueError: duplicate_rejected=True
    nonexplicit_rejected=False
    def kwargs_only(**kwargs): return kwargs
    try: bridge.invoke_callback_capable_target(kwargs_only,callback,{})
    except TypeError: nonexplicit_rejected=True
    checks={'target_called_once':calls['target']==1,'callback_identity_preserved':calls['callback_identity'],
            'handled_true_preserved':result.get('handled') is True,'ordinary_keyword_preserved':result.get('context',{}).get('value')==7,
            'duplicate_callback_rejected':duplicate_rejected,'nonexplicit_target_rejected':nonexplicit_rejected}
    failed=[k for k,v in checks.items() if not v]
except Exception as exc:
    errors.append(f'{type(exc).__name__}:{exc}')
decision=('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1_callback_launch_bridge_CPU_closed'
          if not failed and not existing and not errors else
          'hold_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1_callback_launch_bridge_CPU')
payload={'decision':decision,'checks':checks,'calls':calls,'failed':failed,
         'existing':existing,'errors':errors,'GPU_used':False,'optimizer_updates':0}
if not existing:
    target_path.write_text(json.dumps(payload,indent=2)+'\n')
print(f'decision={decision} checks={checks} failed={failed} existing={existing} errors={errors}')
