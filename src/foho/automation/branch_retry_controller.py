from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TokenBoundedQueryController:
    normal_limit: int = 2
    recovery_limit: int = 3
    attempted: list[str] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    failed_transport: list[str] = field(default_factory=list)
    recovery_authorized: bool = False
    failed_branches: tuple[str, ...] = ()

    def claim(self, stage_id: str) -> None:
        expected=("Q0","Q1","Q2")
        if stage_id not in expected:
            raise ValueError(f"unknown_query_stage:{stage_id}")
        if stage_id in self.attempted:
            raise RuntimeError(f"query_stage_already_attempted:{stage_id}")
        if stage_id=="Q0" and self.attempted:
            raise RuntimeError("Q0_must_be_first")
        if stage_id=="Q1" and self.completed!=["Q0"]:
            raise RuntimeError("Q1_requires_completed_Q0")
        if stage_id=="Q2" and (not self.recovery_authorized or self.completed!=["Q0","Q1"]):
            raise RuntimeError("Q2_requires_failed_branch_recovery_after_Q1")
        limit=self.recovery_limit if self.recovery_authorized else self.normal_limit
        if len(self.attempted)>=limit:
            raise RuntimeError(f"semantic_call_budget_exhausted:{len(self.attempted)}:{limit}")
        self.attempted.append(stage_id)

    def complete(self, stage_id: str) -> None:
        if not self.attempted or self.attempted[-1]!=stage_id:
            raise RuntimeError(f"completion_without_current_claim:{stage_id}")
        self.completed.append(stage_id)

    def record_transport_failure(self, stage_id: str) -> None:
        if not self.attempted or self.attempted[-1]!=stage_id:
            raise RuntimeError(f"failure_without_current_claim:{stage_id}")
        self.failed_transport.append(stage_id)

    def authorize_recovery(self, failed_branches: list[str]) -> None:
        if self.completed!=["Q0","Q1"] or not failed_branches:
            raise RuntimeError("recovery_requires_completed_Q1_and_failed_branches")
        self.recovery_authorized=True
        self.failed_branches=tuple(sorted(set(failed_branches)))

    @property
    def semantic_call_count(self) -> int:
        return len(self.attempted)
