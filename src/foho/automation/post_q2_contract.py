from __future__ import annotations
from pathlib import Path
from typing import Any
from foho.automation.foundation_terminal_contract import (
    FoundationTerminalContractError,sha,validate_foundation_terminal)

PostQ2ContractError=FoundationTerminalContractError

def validate_q2(path: str|Path) -> dict[str,Any]:
    accepted=validate_foundation_terminal(path)
    if accepted.get("source_round")!="Q2":
        raise PostQ2ContractError("expected Q2 terminal result")
    return accepted
