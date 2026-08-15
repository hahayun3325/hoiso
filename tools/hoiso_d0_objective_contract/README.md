# HOISO-Flow Gate-D0 Objective Contract Toolkit

Preparation-only, fail-closed utilities for compiling a semantic Gate-B/D0 result into exact current hand/object geometry and phase-specific optimization policies.

This toolkit does **not** query an MLLM, run HaMeR, modify a mesh, launch an optimizer, or authorize Gate D1. It creates auditable contracts for:

- Gate D0 semantic review;
- finger-name → current MANO joint/vertex binding;
- object-part/side → current Gate-A patch binding;
- D0-guided hand-only objective configuration;
- D0-guided joint objective configuration;
- dense valid z-order input auditing;
- resource-receipt templates.

## Quick start

```bash
cd /home/fredcui/Projects/FollowMyHold
source /home/fredcui/anaconda3/etc/profile.d/conda.sh
conda activate foho

export PROJECT_ROOT=/home/fredcui/Projects/FollowMyHold
export DATA_ROOT=/home/fredcui/foho_phase0
export CASE_ROOT="$DATA_ROOT/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2"

bash /PATH/TO/hoiso_d0_objective_contract_toolkit/scripts/bootstrap_d0_contract.sh
```

Then complete the generated files in `$CASE_ROOT/gate_d0_contact_contract_v1/config`, validate the semantic response, compile exact geometry bindings, audit z-order support, and generate hand/joint objective policies.
