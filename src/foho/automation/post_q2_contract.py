from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any

REQUIRED_EVIDENCE={"panel","get_hunyuan_input","inpaint","moge","hunyuan","hamer","h2m","mano_registration"}

class PostQ2ContractError(RuntimeError): pass
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def validate_q2(path:str|Path)->dict[str,Any]:
    source=Path(path); packet=json.loads(source.read_text())
    if packet.get("schema")!="tracehoi.Q2TerminalResult.v1": raise PostQ2ContractError("Q2 schema")
    if packet.get("decision")!="Q2_PASS" or packet.get("eligible_for_gate_a") is not True:
        raise PostQ2ContractError("Q2 is not eligible for Gate A")
    evidence=packet.get("evidence")
    if not isinstance(evidence,dict) or set(evidence)!=REQUIRED_EVIDENCE:
        raise PostQ2ContractError("Q2 evidence roles")
    for role,record in evidence.items():
        owner=Path(record.get("path",''))
        if not owner.is_file(): raise PostQ2ContractError("missing evidence:"+role)
        if sha(owner)!=record.get("sha256"): raise PostQ2ContractError("evidence hash:"+role)
    return packet
