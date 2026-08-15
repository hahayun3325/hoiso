from __future__ import annotations

import gc

def cleanup_cuda(tag: str = "") -> None:
    print(f"\n[FOHO_MEM] cleanup_cuda start: {tag}")
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            print("[FOHO_MEM] before empty_cache")
            print(torch.cuda.memory_summary(abbreviated=True))
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            print("[FOHO_MEM] after empty_cache")
            print(torch.cuda.memory_summary(abbreviated=True))
    except Exception as e:
        print(f"[FOHO_MEM] cleanup_cuda failed: {repr(e)}")
    print(f"[FOHO_MEM] cleanup_cuda end: {tag}\n")
