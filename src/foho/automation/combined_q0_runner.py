from __future__ import annotations
import base64, hashlib, json, mimetypes, os
from pathlib import Path
from typing import Any
from foho.automation import combined_q0

class CombinedQ0RunnerError(RuntimeError): pass
RATES={
    "gpt-5.5-2026-04-23": {"input":5.00,"cached_input":0.50,"output":30.00},
    "gpt-5.6-sol": {"input":5.00,"cached_input":0.50,"output":30.00},
    "gpt-5.6-terra": {"input":2.00,"cached_input":0.20,"output":12.00},
    "gpt-5.6-luna": {"input":0.20,"cached_input":0.02,"output":1.20},
}

def _sha_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+".incoming")
    temporary.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
    os.replace(temporary,path)
def _get(value: Any, name: str, default: Any=None) -> Any:
    return value.get(name,default) if isinstance(value,dict) else getattr(value,name,default)
def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value,(str,int,float,bool)): return value
    if isinstance(value,dict): return {str(k):_jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [_jsonable(v) for v in value]
    if hasattr(value,"model_dump"): return _jsonable(value.model_dump())
    return str(value)

def build_request(contract: combined_q0.Contract, max_output_tokens: int=6000) -> dict:
    image=contract.crop.read_bytes()
    mime=mimetypes.guess_type(contract.crop.name)[0] or "image/png"
    image_url=f"data:{mime};base64,{base64.b64encode(image).decode('ascii')}"
    return {"model":contract.model,
      "input":[{"role":"user","content":[
        {"type":"input_text","text":contract.prompt},
        {"type":"input_image","image_url":image_url,"detail":"high"}]}],
      "reasoning":{"effort":contract.reasoning_effort},"store":contract.store,
      "max_output_tokens":max_output_tokens,
      "text":{"format":{"type":"json_schema","name":"alapuse02v3n60_combined_q0",
        "strict":True,"schema":contract.output_schema}}}

def request_summary(contract: combined_q0.Contract, max_output_tokens: int=6000) -> dict:
    return {"case_id":contract.case_id,"model":contract.model,
      "reasoning_effort":contract.reasoning_effort,"store":contract.store,
      "crop":str(contract.crop),"crop_sha256":_sha_bytes(contract.crop.read_bytes()),
      "prompt_sha256":hashlib.sha256(contract.prompt.encode()).hexdigest(),
      "output_schema_sha256":hashlib.sha256(json.dumps(contract.output_schema,sort_keys=True).encode()).hexdigest(),
      "input_content_types":["input_text","input_image"],"image_detail":"high",
      "max_output_tokens":max_output_tokens,"strict_json_schema":True}

def _usage_dict(response: Any) -> dict:
    usage=_jsonable(_get(response,"usage",{}))
    return usage if isinstance(usage,dict) else {}
def _estimated_cost(model: str, usage: dict) -> dict:
    rate=RATES.get(model)
    if rate is None: return {"available":False,"reason":f"unpriced_model:{model}"}
    input_tokens=int(usage.get("input_tokens",0) or 0)
    output_tokens=int(usage.get("output_tokens",0) or 0)
    details=usage.get("input_tokens_details",{}) or {}
    cached=int(details.get("cached_tokens",0) or 0) if isinstance(details,dict) else 0
    uncached=max(0,input_tokens-cached)
    value=(uncached*rate["input"]+cached*rate["cached_input"]+output_tokens*rate["output"])/1_000_000
    return {"available":True,"usd":round(value,8),"input_tokens":input_tokens,
      "cached_input_tokens":cached,"output_tokens":output_tokens,"rates":rate}
def _refusals(response: Any) -> list[str]:
    found=[]
    for item in _get(response,"output",[]) or []:
        for content in _get(item,"content",[]) or []:
            if _get(content,"type")=="refusal": found.append(str(_get(content,"refusal","refused")))
    return found

def execute(client: Any, contract: combined_q0.Contract, output_dir: str|Path,
            *, max_output_tokens: int=6000, transport_authorized: bool=False) -> dict:
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    summary=request_summary(contract,max_output_tokens)
    _atomic_json(out/"request_preflight.json",{"schema":"tracehoi.CombinedQ0RequestPreflight.v1",
      **summary,"transport_authorized":transport_authorized,"api_calls_before":0})
    if not transport_authorized:
        raise CombinedQ0RunnerError("transport_not_authorized")
    request=build_request(contract,max_output_tokens)
    try:
        response=client.responses.create(**request)
    except Exception as exc:
        failure={"schema":"tracehoi.CombinedQ0TransportException.v1","error_type":type(exc).__name__,
          "error":str(exc),"api_calls":1,"semantic_packet_written":False,
          "decision":"review_combined_Q0_transport_exception"}
        _atomic_json(out/"transport_exception.json",failure)
        raise CombinedQ0RunnerError(f"transport:{type(exc).__name__}:{exc}") from exc
    usage=_usage_dict(response); response_model=str(_get(response,"model",contract.model))
    telemetry={"schema":"tracehoi.CombinedQ0ResponseTelemetry.v1","response_id":_get(response,"id"),
      "response_model":response_model,"status":_get(response,"status"),
      "error":_jsonable(_get(response,"error")),"incomplete_details":_jsonable(_get(response,"incomplete_details")),
      "usage":usage,"estimated_cost":_estimated_cost(response_model,usage),
      "output_text":_get(response,"output_text",""),"response":_jsonable(response),"api_calls":1}
    _atomic_json(out/"response_telemetry.json",telemetry)
    errors=[]; status=telemetry["status"]; text=str(telemetry["output_text"] or "")
    refusals=_refusals(response)
    if status!="completed": errors.append(f"status:{status}")
    if refusals: errors.append(f"refusal:{refusals}")
    packet=None
    if not errors:
        try: packet=json.loads(text)
        except Exception as exc: errors.append(f"json:{type(exc).__name__}:{exc}")
    if packet is not None and not errors:
        try: combined_q0.validate_semantic_packet(packet,contract)
        except Exception as exc: errors.append(f"semantic:{type(exc).__name__}:{exc}")
    if not errors and packet is not None:
        _atomic_json(out/"combined_Q0_semantic_packet.json",packet)
    receipt={"schema":"tracehoi.CombinedQ0ExecutionReceipt.v1",**summary,
      "response_id":telemetry["response_id"],"response_model":response_model,"status":status,
      "usage":usage,"estimated_cost":telemetry["estimated_cost"],"api_calls":1,
      "telemetry_written_before_validation":(out/"response_telemetry.json").is_file(),
      "semantic_packet":str(out/"combined_Q0_semantic_packet.json") if not errors else None,
      "errors":errors,"gpu_updates":0,
      "decision":"alapuse02v3n60_combined_Q0_live_closed" if not errors else "review_alapuse02v3n60_combined_Q0_live"}
    _atomic_json(out/"execution_receipt.json",receipt)
    if errors: raise CombinedQ0RunnerError(";".join(errors))
    return receipt
