from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .branch_retry_controller import TokenBoundedQueryController
from .contracts import canonical_sha256
from .openai_query_adapter import QueryAdapter, QueryRequest, QueryResult


@dataclass(frozen=True)
class AutomaticQueryResult:
    q0: dict[str, Any]
    q1: dict[str, Any]
    q2: dict[str, Any] | None
    foundation_outputs: dict[str, Any]
    semantic_call_count: int
    terminal_drop: bool


class AtomicReceiptWriter:
    def __init__(self, root: str | Path):
        self.root=Path(root)
        self.root.mkdir(parents=True,exist_ok=True)

    def write(self, name: str, payload: Mapping[str, Any]) -> Path:
        target=self.root/f"{name}.json"
        temporary=target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(dict(payload),indent=2,sort_keys=True)+'\n')
        os.replace(temporary,target)
        return target


class AutomaticQueryOrchestrator:
    def __init__(self, adapter: QueryAdapter, receipt_root: str | Path):
        self.adapter=adapter
        self.controller=TokenBoundedQueryController()
        self.receipts=AtomicReceiptWriter(receipt_root)

    def _query(self, request: QueryRequest) -> QueryResult:
        self.controller.claim(request.stage_id)
        try:
            result=self.adapter.query(request)
        except Exception as exc:
            self.controller.record_transport_failure(request.stage_id)
            self.receipts.write(f"{request.stage_id}_failure",{
                "stage_id":request.stage_id,"status":"FAILED",
                "error_type":type(exc).__name__,"error":str(exc),
                "semantic_call_count":self.controller.semantic_call_count})
            raise
        self.controller.complete(request.stage_id)
        self.receipts.write(f"{request.stage_id}_receipt",result.receipt)
        return result

    def run(self, *, crop_path: Path, prompts: Mapping[str, str],
            schemas: Mapping[str, Mapping[str, Any]],
            run_foundations: Callable[[dict[str, Any]], dict[str, Any]],
            build_evidence: Callable[[str, dict[str, Any]], tuple[Path, ...]],
            recover_foundations: Callable[[list[str], dict[str, Any], dict[str, Any]], dict[str, Any]]) -> AutomaticQueryResult:
        q0=self._query(QueryRequest("Q0",prompts["Q0"],(crop_path,),"q0_packet",schemas["Q0"]))
        outputs=run_foundations(q0.packet)
        q1_images=build_evidence("Q1",outputs)
        q1=self._query(QueryRequest("Q1",prompts["Q1"],q1_images,"q1_packet",schemas["Q1"]))
        failed=sorted(item["branch_id"] for item in q1.packet["branches"] if item["verdict"]!="PASS")
        q2_packet=None
        if failed:
            self.controller.authorize_recovery(failed)
            accepted={key:value for key,value in outputs.items() if key not in failed}
            accepted_hash=canonical_sha256(accepted)
            recovered=recover_foundations(failed,q0.packet,outputs)
            accepted_after={key:value for key,value in recovered.items() if key not in failed}
            if canonical_sha256(accepted_after)!=accepted_hash:
                raise RuntimeError("accepted_branch_mutated_during_recovery")
            outputs=recovered
            q2_images=build_evidence("Q2",outputs)
            q2=self._query(QueryRequest("Q2",prompts["Q2"],q2_images,"q2_packet",schemas["Q2"]))
            q2_packet=q2.packet
            terminal=bool(q2_packet.get("terminal_drop")) or any(
                item["verdict"]!="PASS" for item in q2_packet["branches"]
            )
        else:
            terminal=False
        result=AutomaticQueryResult(q0.packet,q1.packet,q2_packet,outputs,
                                    self.controller.semantic_call_count,terminal)
        self.receipts.write("automatic_query_terminal",{
            "semantic_call_count":result.semantic_call_count,
            "terminal_drop":result.terminal_drop,
            "foundation_output_sha256":canonical_sha256(result.foundation_outputs)})
        return result
