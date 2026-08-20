from __future__ import annotations
import importlib, json
from pathlib import Path
from foho.automation.pilot_dag import RestartableCaseDAG, STAGE_ORDER
class BranchConnectorError(RuntimeError): pass
def expand(value,context):
    if isinstance(value,str):
        result=value
        for key,item in context.items(): result=result.replace("${"+key+"}",str(item))
        if "${" in result: raise BranchConnectorError(f"unresolved:{result}")
        return result
    if isinstance(value,list): return [expand(item,context) for item in value]
    if isinstance(value,dict): return {key:expand(item,context) for key,item in value.items()}
    return value
def call(locator,kwargs):
    module,name=locator.split(":",1)
    return getattr(importlib.import_module(module),name)(**dict(kwargs))
def producer(spec,context,mode):
    def run(stage_root,inputs):
        stage_root=Path(stage_root); stage_root.mkdir(parents=True,exist_ok=True)
        local=dict(context,STAGE_ROOT=str(stage_root))
        outputs={key:value["path"] for key,value in inputs.items()} if spec.get("carry_inputs") else {}
        selected=spec[mode]
        if mode=="live":
            for item in selected.get("calls",[]): call(item["callable"],expand(item.get("kwargs",{}),local))
        for role,value in expand(selected.get("outputs",{}),local).items():
            owner=Path(value)
            if not owner.is_file(): raise BranchConnectorError(f"missing:{role}:{owner}")
            outputs[role]=str(owner)
        if not outputs: raise BranchConnectorError("empty outputs")
        return outputs
    return run
def run_until(config_path,run_root,stop_after,mode="reference"):
    config=json.loads(Path(config_path).read_text())
    dag=RestartableCaseDAG(config["case_id"],run_root,config["owner_bundle"],config["roots"])
    state=dag.start(config["initial_inputs"])
    while state["status"]!="complete":
        stage=STAGE_ORDER[int(state["next_index"])]
        if stage not in config["stages"]: break
        dag.run_stage(stage,producer(config["stages"][stage],config["context"],mode))
        state=dag.resume()
        if stage==stop_after: break
    return state
