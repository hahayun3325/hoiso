import json
import os
from pathlib import Path

import torch
import foho.guidance.h1_read_only_registration_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_2 as panel_module


def main():
    receipt=Path(os.environ['CPU_OWNER19445'])
    checks={}; errors=[]; captured={}
    original_load=panel_module.load_h1_resources
    original_bind=panel_module.bind_h1_live_context
    try:
        def fake_load(*args,**kwargs):
            captured['loader_args']=args
            captured['loader_kwargs']=kwargs
            return {'provider':'sentinel_provider'}
        def fake_bind(context,resources,output_root):
            captured['bind_resources']=resources
            captured['bind_output_root']=str(output_root)
            return {**context,'h1_runtime':'sentinel_runtime'}
        panel_module.load_h1_resources=fake_load
        panel_module.bind_h1_live_context=fake_bind
        paths={
          'h0_manifest':'h0_manifest','h0_source_bundle':'h0_source_bundle',
          'h0_policy':'h0_policy','h1_policy':'h1_policy','provider':'provider',
          'bridge':'bridge','carrier':'carrier','mano':'mano','jacobian':'jacobian',
          'h0_checkpoint':'h0_checkpoint','T_h2m':'accepted_T_h2m'}
        callback=panel_module.create_h1_panel_callback(
            paths,'owner_probe_root','checkpoint','crop','metrics','panel')
        bound=callback.bind_live_context(
            {'parameters':{'global_hand_rotation':torch.zeros(4)}})
        checks={
          'exact_T_h2m_keyword_forwarded':
              captured.get('loader_kwargs')=={'T_h2m_path':'accepted_T_h2m'},
          'all_original_loader_owners_preserved':
              len(captured.get('loader_args',()))==12 and
              captured['loader_args'][9]=='h0_checkpoint',
          'loaded_resources_reach_live_binder':
              captured.get('bind_resources')=={'provider':'sentinel_provider'},
          'read_only_output_root_preserved':
              captured.get('bind_output_root')=='owner_probe_root/read_only_runtime',
          'callback_binding_completed':bound.get('h1_runtime')=='sentinel_runtime',
        }
    except Exception as exc:
        errors.append(f'{type(exc).__name__}:{exc}')
    finally:
        panel_module.load_h1_resources=original_load
        panel_module.bind_h1_live_context=original_bind
    failed=[name for name,value in checks.items() if not value]
    payload={
      'decision':('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_4_5_panel_T_h2m_owner_CPU_closed'
                  if not failed and not errors else
                  'review_required_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_4_5_recheck_panel_T_h2m_owner_CPU'),
      'checks':checks,'failed':failed,'missing':[],
      'existing':[str(receipt)] if receipt.exists() else [],'errors':errors,
      'GPU_used':False,'optimizer_updates':0}
    if not receipt.exists():
        receipt.parent.mkdir(parents=True,exist_ok=True)
        receipt.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload))


if __name__=='__main__':
    main()
