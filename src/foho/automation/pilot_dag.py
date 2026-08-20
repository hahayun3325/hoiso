from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Callable, Mapping
from foho.automation.stage_adapters import handoff_receipt, require_inputs

CASE_ALLOWLIST=("alapuse02v3n60",)
STAGE_ORDER=(
    "input_adapter",
    "combined_q0",
    "foundation_models",
    "auto_v2_q1",
    "gate_a",
    "cpu_hand_registration",
    "gate_c",
    "gate_d0",
    "contract_compile",
    "h0",
    "h1",
    "o0",
    "j0",
    "f0",
)

class PipelineContractError(RuntimeError):
    pass

def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _atomic_json(path: Path, packet: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(dict(packet),indent=2,sort_keys=True)+"\n")
    temporary.replace(path)

def validate_owner_bundle(path: str | Path, roots: Mapping[str,str]) -> dict[str,Any]:
    packet=json.loads(Path(path).read_text())
    if packet.get("schema")!="tracehoi.AutomaticSemanticOwnerBundles.v1":
        raise PipelineContractError("wrong owner-bundle schema")
    if packet.get("decision")!="automatic_semantic_owner_bundles_closed_for_mocking":
        raise PipelineContractError("owner bundle is not closed for mocking")
    required={"combined_q0","gate_a","gate_c_auto_v2","gate_d0","f0"}
    if set(packet.get("owners",{}))!=required:
        raise PipelineContractError("owner bundle role set is not exact")
    for role,spec in packet["owners"].items():
        if not spec.get("terminal_validator_required"):
            raise PipelineContractError(f"missing terminal validator: {role}")
        for record in spec.get("records",[]):
            locator=str(record["locator"]); resolved=locator
            for token,value in roots.items(): resolved=resolved.replace(token,value)
            if resolved.startswith("$"):
                raise PipelineContractError(f"unresolved locator: {locator}")
            owner=Path(resolved)
            if not owner.is_file(): raise PipelineContractError(f"missing owner: {owner}")
            if _sha256(owner)!=record["sha256"]:
                raise PipelineContractError(f"owner hash mismatch: {role}:{owner}")
    return packet

class RestartableCaseDAG:
    def __init__(self, case_id: str, run_root: str | Path, owner_bundle: str | Path,
                 roots: Mapping[str,str], stage_order=STAGE_ORDER):
        if case_id not in CASE_ALLOWLIST:
            raise PipelineContractError(f"case is not allowlisted: {case_id}")
        self.case_id=case_id; self.run_root=Path(run_root)
        self.receipt_root=self.run_root/"receipts"; self.state_path=self.run_root/"state.json"
        self.stage_order=tuple(stage_order)
        if len(set(self.stage_order))!=len(self.stage_order):
            raise PipelineContractError("duplicate stage name")
        self.owner_bundle=validate_owner_bundle(owner_bundle,roots)

    def start(self, inputs: Mapping[str,Mapping[str,str]]) -> dict[str,Any]:
        if self.state_path.is_file(): return self.resume()
        require_inputs(inputs)
        state={"schema":"tracehoi.AutomaticPilotState.v1","case_id":self.case_id,
               "stage_order":list(self.stage_order),"next_index":0,
               "last_outputs":dict(inputs),"history":[],"status":"ready",
               "api_calls":0,"gpu_updates":0}
        _atomic_json(self.state_path,state); return state

    def resume(self) -> dict[str,Any]:
        if not self.state_path.is_file(): raise PipelineContractError("pilot state is absent")
        state=json.loads(self.state_path.read_text())
        if state.get("case_id")!=self.case_id or tuple(state.get("stage_order",()))!=self.stage_order:
            raise PipelineContractError("pilot state identity mismatch")
        require_inputs(state.get("last_outputs",{}))
        return state

    def run_stage(self, stage: str,
                  producer: Callable[[Path,Mapping[str,Mapping[str,str]]],Mapping[str,str]]) -> dict[str,Any]:
        state=self.resume(); index=int(state["next_index"])
        if index>=len(self.stage_order): raise PipelineContractError("pipeline already complete")
        expected=self.stage_order[index]
        if stage!=expected: raise PipelineContractError(f"stage order mismatch: {stage} != {expected}")
        inputs=state["last_outputs"]; require_inputs(inputs)
        stage_root=self.run_root/f"{index:02d}_{stage}"; stage_root.mkdir(parents=True,exist_ok=True)
        try:
            outputs=dict(producer(stage_root,inputs))
            if not outputs: raise PipelineContractError(f"stage emitted no outputs: {stage}")
            receipt=handoff_receipt(stage,inputs,outputs)
        except Exception as exc:
            failure={"schema":"tracehoi.AutomaticStageFailure.v1","case_id":self.case_id,
                     "stage":stage,"index":index,"error_type":type(exc).__name__,
                     "error":str(exc),"decision":"stage_failed_without_promotion"}
            _atomic_json(self.receipt_root/f"{index:02d}_{stage}_failure.json",failure)
            state["status"]="failed"; state["failed_stage"]=stage
            _atomic_json(self.state_path,state)
            raise
        receipt.update({"case_id":self.case_id,"index":index,"api_calls":0,"gpu_updates":0})
        receipt_path=self.receipt_root/f"{index:02d}_{stage}.json"; _atomic_json(receipt_path,receipt)
        state["history"].append({"stage":stage,"receipt_path":str(receipt_path),
                                 "receipt_sha256":_sha256(receipt_path)})
        state["last_outputs"]=receipt["outputs"]; state["next_index"]=index+1
        state.pop("failed_stage",None)
        state["status"]="complete" if state["next_index"]==len(self.stage_order) else "ready"
        _atomic_json(self.state_path,state); return receipt
