from __future__ import annotations

import base64
import json
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from .contracts import canonical_sha256, file_sha256, validate_packet


@dataclass(frozen=True)
class QueryRequest:
    stage_id: str
    prompt_text: str
    image_paths: tuple[Path, ...]
    schema_name: str
    schema: Mapping[str, Any]


@dataclass(frozen=True)
class QueryResult:
    packet: dict[str, Any]
    receipt: dict[str, Any]


class QueryAdapter(Protocol):
    def query(self, request: QueryRequest) -> QueryResult: ...


def _data_url(path: Path) -> str:
    mime=mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded=base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class MockQueryAdapter:
    def __init__(self, responses: Mapping[str, Sequence[Mapping[str, Any]] | Mapping[str, Any]]):
        self._responses={}
        for stage,value in responses.items():
            if isinstance(value, Mapping):
                self._responses[stage]=[dict(value)]
            else:
                self._responses[stage]=[dict(item) for item in value]
        self.calls=[]

    def query(self, request: QueryRequest) -> QueryResult:
        queue=self._responses.get(request.stage_id, [])
        if not queue:
            raise RuntimeError(f"missing_mock_response:{request.stage_id}")
        packet=validate_packet(queue.pop(0), request.schema)
        self.calls.append(request.stage_id)
        receipt={"stage_id":request.stage_id,"api_called":False,"mock":True,
                 "model":None,"prompt_sha256":canonical_sha256(request.prompt_text),
                 "image_sha256":[file_sha256(path) for path in request.image_paths],
                 "output_sha256":canonical_sha256(packet),"usage":None}
        return QueryResult(packet,receipt)


class OpenAIResponsesAdapter:
    def __init__(self, *, model: str="gpt-5.5-2026-04-23",
                 reasoning_effort: str="high", api_key_env: str="OPENAI_API_KEY",
                 max_output_tokens: int=4096):
        key=os.environ.get(api_key_env)
        if not key:
            raise RuntimeError(f"missing_API_key_environment:{api_key_env}")
        from openai import OpenAI
        self.client=OpenAI(api_key=key,max_retries=0)
        self.model=model
        self.reasoning_effort=reasoning_effort
        self.api_key_env=api_key_env
        self.max_output_tokens=max_output_tokens

    def query(self, request: QueryRequest) -> QueryResult:
        content=[{"type":"input_text","text":request.prompt_text}]
        for path in request.image_paths:
            content.append({"type":"input_image","image_url":_data_url(path)})
        response=self.client.responses.create(
            model=self.model,
            reasoning={"effort":self.reasoning_effort},
            input=[{"role":"user","content":content}],
            text={"format":{"type":"json_schema","name":request.schema_name,
                            "schema":dict(request.schema),"strict":True}},
            max_output_tokens=self.max_output_tokens,
            store=False,
        )
        packet=validate_packet(json.loads(response.output_text),request.schema)
        usage=response.usage.model_dump(mode="json") if response.usage is not None else None
        receipt={"stage_id":request.stage_id,"api_called":True,"mock":False,
                 "response_id":response.id,"model":self.model,
                 "reasoning_effort":self.reasoning_effort,"store":False,"max_retries":0,
                 "api_key_environment":self.api_key_env,
                 "prompt_sha256":canonical_sha256(request.prompt_text),
                 "image_sha256":[file_sha256(path) for path in request.image_paths],
                 "output_sha256":canonical_sha256(packet),"usage":usage}
        return QueryResult(packet,receipt)
