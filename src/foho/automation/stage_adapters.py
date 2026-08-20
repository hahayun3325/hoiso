from __future__ import annotations
import hashlib, importlib, inspect, json
from pathlib import Path
from typing import Any, Mapping

class StageContractError(RuntimeError):
    pass

def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_manifest(path: str | Path) -> dict[str, Any]:
    packet=json.loads(Path(path).read_text())
    if packet.get("schema")!="tracehoi.ExactStageOwnerManifest.v1":
        raise StageContractError("wrong stage-manifest schema")
    return packet

def validate_owner(owner: Mapping[str, Any]) -> None:
    module=importlib.import_module(str(owner["module"]))
    function=getattr(module,str(owner["callable"]))
    actual=list(inspect.signature(function).parameters)
    if actual!=list(owner["args"]):
        raise StageContractError(f"signature mismatch: {actual} != {owner['args']}")

def require_inputs(inputs: Mapping[str, Mapping[str, str]]) -> None:
    for role,receipt in inputs.items():
        path=Path(receipt["path"])
        if not path.is_file(): raise StageContractError(f"missing input {role}: {path}")
        if sha256(path)!=receipt["sha256"]: raise StageContractError(f"input hash mismatch: {role}")

def run_callable(owner: Mapping[str, Any], kwargs: Mapping[str, Any]) -> Any:
    validate_owner(owner)
    missing=set(owner["args"])-set(kwargs); extra=set(kwargs)-set(owner["args"])
    if missing or extra:
        raise StageContractError(f"argument mismatch missing={sorted(missing)} extra={sorted(extra)}")
    module=importlib.import_module(str(owner["module"]))
    return getattr(module,str(owner["callable"]))(**dict(kwargs))

def handoff_receipt(stage: str, inputs: Mapping[str, Mapping[str, str]], outputs: Mapping[str, str]) -> dict[str, Any]:
    require_inputs(inputs); out={}
    for role,value in outputs.items():
        path=Path(value)
        if not path.is_file(): raise StageContractError(f"missing output {role}: {path}")
        out[role]={"path":str(path),"sha256":sha256(path)}
    return {"schema":"tracehoi.StageHandoffReceipt.v1","stage":stage,
            "inputs":dict(inputs),"outputs":out,"decision":"stage_handoff_closed"}
