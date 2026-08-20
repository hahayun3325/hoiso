from __future__ import annotations
from typing import Any

def run(*, runner_args: list[Any], runner_kwargs: dict[str, Any] | None = None) -> None:
    if not isinstance(runner_args, list):
        raise TypeError('runner_args must be a list')
    if runner_kwargs is None:
        runner_kwargs = {}
    if not isinstance(runner_kwargs, dict):
        raise TypeError('runner_kwargs must be a dict')
    from foho.utils.runner import run_in_conda
    result = run_in_conda(*runner_args, **runner_kwargs)
    returncode = getattr(result, 'returncode', None)
    if returncode is None and isinstance(result, int) and not isinstance(result, bool):
        returncode = result
    if returncode not in (None, 0):
        raise RuntimeError(f'run_in_conda returned nonzero status: {returncode}')
