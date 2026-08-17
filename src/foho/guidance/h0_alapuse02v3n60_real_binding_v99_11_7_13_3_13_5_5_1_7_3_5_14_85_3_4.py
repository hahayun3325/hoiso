from pathlib import Path

from foho.guidance.h0_manifest_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_9 import create_bound_callback

CASE_ROOT=Path('/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2')
PROJECT_ROOT=Path('/home/fredcui/Projects/FollowMyHold')
CASE_MANIFEST=CASE_ROOT/'gate_d0_H0_real_hook_binding_and_execution_contract_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_2/config/alapuse02v3n60_H0_case_manifest_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_2.json'
SOURCE_BUNDLE=CASE_ROOT/'gate_d0_H0_exact_source_diff_bundle_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_10/reports/exact_H0_source_diff_bundle_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_10.json'
GLOBAL_POLICY=PROJECT_ROOT/'config/optimization/H0_global_dimensionless_loss_policy_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_4.json'


def create_callback(mode, output_root, resources_override=None):
    modes={'backward-only':(0,True,False),
           'capture-only':(0,False,True),
           'optimize':(5,False,False)}
    if mode not in modes:
        raise ValueError(f'unsupported_H0_mode:{mode}')
    updates,backward_only,capture_only=modes[mode]
    return create_bound_callback(
        CASE_MANIFEST,SOURCE_BUNDLE,GLOBAL_POLICY,output_root,
        updates=updates,backward_only=backward_only,
        capture_only=capture_only,resources_override=resources_override,
        terminate_after_h0=True)
