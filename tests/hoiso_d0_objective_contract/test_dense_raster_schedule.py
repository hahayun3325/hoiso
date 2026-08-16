import importlib.util, json, os
from pathlib import Path

path=Path(os.environ['PROJECT_RASTER_SCHEDULE']); target=Path(os.environ['RASTER_TEST_REPORT'])
spec=importlib.util.spec_from_file_location('raster_schedule',path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
calls=[]
def rasterize(value):
    calls.append(value); return {'raster_of':value,'call':len(calls)}

fixed=module.DenseRasterSchedule(rasterize,True)
fixed_a=fixed.for_forward('object_fixed'); fixed_b=fixed.for_forward('object_changed_but_forbidden')
moving=module.DenseRasterSchedule(rasterize,False)
move_0a=moving.for_forward('object_0',0); move_0b=moving.for_forward('object_0',0)
moving.finish_forward(0); move_1=moving.for_forward('object_1',1); moving.finish_forward(1)
missing_key_rejected=False
try: moving.for_forward('object_2')
except module.DenseRasterScheduleError: missing_key_rejected=True
checks={'fixed_rasterized_once':fixed_a is fixed_b and fixed_a['raster_of']=='object_fixed','moving_shared_within_iteration':move_0a is move_0b,'moving_regenerated_next_iteration':move_1 is not move_0a and move_1['raster_of']=='object_1','moving_requires_iteration_key':missing_key_rejected,'total_expected_raster_calls':len(calls)==3}
payload={'decision':'pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_68_dense_raster_schedule_CPU_closed' if all(checks.values()) else 'hold_v99_11_7_13_3_13_5_5_1_7_3_5_14_68_dense_raster_schedule_CPU','checks':checks,'call_trace':calls,'failed':[name for name,value in checks.items() if not value],'missing':[],'existing':[],'errors':[]}
target.write_text(json.dumps(payload,indent=2)+'\n'); print(json.dumps({'decision':payload['decision'],'failed':payload['failed'],'call_trace':calls}))
