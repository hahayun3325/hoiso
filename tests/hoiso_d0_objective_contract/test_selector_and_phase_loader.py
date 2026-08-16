import importlib.util
import json
import os
from pathlib import Path

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

selector=load(Path(os.environ['PROJECT_SELECTOR']),'selector')
source=json.loads(Path(os.environ['EXPANSION_REPORT']).read_text())
result=selector.select_contact_patch(source)
rows={row['label']:row for row in result['assessed_candidates']}
checks={'selected_r04':result['selected_label']=='r04','r02_too_little_relative_support':rows['r02']['relative_in_ROI_support']<.50,'r04_precision_pass':rows['r04']['patch_precision']>=.90,'r04_support_pass':rows['r04']['relative_in_ROI_support']>=.50,'r06_precision_fail':rows['r06']['patch_precision']<.90}
payload={'decision':'pass_selector_and_phase_loader_CPU_tests' if all(checks.values()) else 'hold_selector_and_phase_loader_CPU_tests','selector_result':result,'checks':checks,'failed':[name for name,value in checks.items() if not value],'missing':[],'errors':[]}
Path(os.environ['SELECTOR_TEST_REPORT']).write_text(json.dumps(payload,indent=2)+'\n')
print(json.dumps({'decision':payload['decision'],'selected':result['selected_label'],'failed':payload['failed']}))
