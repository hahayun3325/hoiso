from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any

REQUIRED_EVIDENCE={"panel","get_hunyuan_input","inpaint","moge","hunyuan","hamer","h2m","mano_registration"}

class FoundationTerminalContractError(RuntimeError):
    pass

def sha(path: str|Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _load(path: str|Path) -> dict[str,Any]:
    source=Path(path)
    if not source.is_file():
        raise FoundationTerminalContractError("missing packet:"+str(source))
    try: packet=json.loads(source.read_text())
    except Exception as exc:
        raise FoundationTerminalContractError("invalid JSON:"+str(source)) from exc
    if not isinstance(packet,dict):
        raise FoundationTerminalContractError("packet is not an object:"+str(source))
    return packet

def _evidence(packet: dict[str,Any]) -> dict[str,Any]:
    evidence=packet.get("evidence")
    if not isinstance(evidence,dict) or set(evidence)!=REQUIRED_EVIDENCE:
        raise FoundationTerminalContractError("foundation evidence roles")
    for role,record in evidence.items():
        if not isinstance(record,dict):
            raise FoundationTerminalContractError("evidence record:"+role)
        owner=Path(str(record.get("path",'')))
        if not owner.is_file():
            raise FoundationTerminalContractError("missing evidence:"+role)
        if sha(owner)!=record.get("sha256"):
            raise FoundationTerminalContractError("evidence hash:"+role)
    return evidence

def validate_foundation_terminal(path: str|Path) -> dict[str,Any]:
    source=Path(path); packet=_load(source); schema=packet.get("schema")
    if packet.get("eligible_for_gate_a") is not True:
        raise FoundationTerminalContractError("foundation result is not eligible for Gate A")
    if packet.get("errors") not in (None,[]):
        raise FoundationTerminalContractError("foundation result contains errors")
    if schema=="tracehoi.FoundationTerminalPass.v1":
        if packet.get("decision") not in {
            "replacement_Q1_PASS_gate_A_readiness_closed","foundation_terminal_pass_closed"}:
            raise FoundationTerminalContractError("Q1 terminal decision")
        if packet.get("Q2_calls_in_lineage") not in (None,0):
            raise FoundationTerminalContractError("direct Q1 pass has Q2 calls")
        result=Path(str(packet.get("source_result",'')))
        if not result.is_file() or sha(result)!=packet.get("source_result_sha256"):
            raise FoundationTerminalContractError("source Q1 result hash")
        q1=_load(result)
        if (q1.get("decoded") or {}).get("overall_decision")!="PASS":
            raise FoundationTerminalContractError("source Q1 result is not PASS")
        source_round=str(packet.get("source_round") or "Q1")
    elif schema=="tracehoi.Q2TerminalResult.v1":
        if packet.get("decision")!="Q2_PASS":
            raise FoundationTerminalContractError("Q2 is not PASS")
        if packet.get("third_jury_call_allowed") is not False:
            raise FoundationTerminalContractError("Q2 is not terminal")
        if (packet.get("decoded") or {}).get("overall_decision")!="PASS":
            raise FoundationTerminalContractError("decoded Q2 is not PASS")
        source_round="Q2"
    else:
        raise FoundationTerminalContractError("foundation terminal schema")
    evidence=_evidence(packet)
    return {"schema":"tracehoi.FoundationTerminalAcceptance.v1",
      "case_id":packet.get("case_id"),"source_round":source_round,
      "source_receipt":str(source.resolve()),"source_receipt_sha256":sha(source),
      "evidence":evidence,"eligible_for_gate_a":True,
      "decision":"foundation_terminal_acceptance_closed"}
