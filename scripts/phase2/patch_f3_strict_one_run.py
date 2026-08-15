#!/usr/bin/env python3
"""Restrict opt-in F3 to one translation-only joint stage."""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import shutil
from pathlib import Path

DEFAULT = Path('third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py')

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{name}: expected one anchor, found {count}')
    return text.replace(old, new, 1)

def patch(text: str) -> str:
    if 'FOHO_F3_STRICT_ONE_RUN' in text:
        raise RuntimeError('strict F3 patch is already present')
    for marker in (
        'FOHO_F3_STAGE1_BEGIN',
        'FOHO_F3_OPTIMIZER',
        'FOHO_F3_STAGE1_END',
    ):
        if marker not in text:
            raise RuntimeError(f'missing required F3 marker: {marker}')

    old_phase1 = (
        '                    if i == handopt_start_step: # pre-guidance step: '
        'optimize hands while reconstructing the object separately'
    )
    new_phase1 = '''                    if _foho_f3_enabled and i == handopt_start_step:
                        # FOHO_F3_STRICT_ONE_RUN
                        print('[FOHO_F3_BYPASS] skipped phase-1 hand optimization')
                    elif _foho_f3_enabled and i == handopt_start_step + 1:
                        print('[FOHO_F3_BYPASS] skipped phase-1.5 object optimization')
                    elif i == handopt_start_step: # pre-guidance step: optimize hands while reconstructing the object separately'''
    text = replace_once(text, old_phase1, new_phase1, 'phase-1 bypass')

    old_joint = (
        '                    elif handopt_start_step + 2 <= i <= guidance_end_step: '
        '# joint optimization step: optimize hands and object together'
    )
    new_joint = '''                    elif (
                        handopt_start_step + 2 <= i <= guidance_end_step
                        and (
                            not _foho_f3_enabled
                            or i == handopt_start_step + 2
                        )
                    ): # joint optimization step: optimize hands and object together'''
    text = replace_once(text, old_joint, new_joint, 'one joint-stage gate')

    old_plan = '''                            # FOHO_F3_OPTIMIZER
                            f3_optimizer = torch.optim.AdamW('''
    new_plan = '''                            # FOHO_F3_OPTIMIZER
                            print(
                                '[FOHO_F3_RUNTIME_PLAN] '
                                f'outer_step={i}, '
                                f'inner_steps={_foho_f3_steps_this_outer}'
                            )
                            f3_optimizer = torch.optim.AdamW('''
    # The plan must be printed after the preflight/real step budget is set.
    old_budget = '''                            _foho_f3_steps_this_outer = (
                                0
                                if _foho_f3_preflight_only
                                else _foho_f3_steps
                            )

                            _foho_f3_optimizer_ids = {'''
    new_budget = '''                            _foho_f3_steps_this_outer = (
                                0
                                if _foho_f3_preflight_only
                                else _foho_f3_steps
                            )
                            print(
                                '[FOHO_F3_RUNTIME_PLAN] '
                                f'outer_step={i}, '
                                f'inner_steps={_foho_f3_steps_this_outer}'
                            )

                            _foho_f3_optimizer_ids = {'''
    if old_plan not in text or old_budget not in text:
        raise RuntimeError('F3 optimizer anchors do not match inspected source')
    text = replace_once(text, old_budget, new_budget, 'runtime-plan print')
    compile(text, '<patched pipelines.py>', 'exec')
    return text

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--pipe', type=Path, default=DEFAULT)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    original = args.pipe.read_text()
    updated = patch(original)
    print(''.join(difflib.unified_diff(
        original.splitlines(keepends=True), updated.splitlines(keepends=True),
        fromfile=str(args.pipe), tofile=str(args.pipe) + '.strict_F3',
    )))
    if not args.apply:
        Path('/tmp/pipelines.py.strict_F3_candidate').write_text(updated)
        print('[CHECK] candidate: /tmp/pipelines.py.strict_F3_candidate')
        return
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = args.pipe.with_name(args.pipe.name + f'.before_strict_F3_{stamp}')
    shutil.copy2(args.pipe, backup)
    args.pipe.write_text(updated)
    print('[OK] backup:', backup)
    print('[OK] patched:', args.pipe)

if __name__ == '__main__':
    main()
