# `alapuse02v3n60` AUTO-V2 toolkit

This toolkit implements the professor-approved **method-level automatic branch**:

```text
spatial VLM proposal
→ box-prompted SAM2 masks
→ fixed part-aware candidate bank
→ deterministic gate
→ blind VLM critic
→ existing exact-file authorization
→ one fixed-seed Hunyuan run
```

Read `PROFESSOR_ANSWER.md` first. The scripts are intentionally fail-closed and avoid `exit 2` / `SystemExit(2)`.

## Included utilities

- `bootstrap_auto_v2.sh`: creates the pre-registered branch and inventories local code/assets.
- `validate_spatial_proposal.py`: validates exact-schema normalized VLM boxes.
- `sam2_box_segment.py`: runs box-prompted SAM2 masks.
- `build_part_graph_candidate_bank.py`: creates the fixed four-candidate bank.
- `select_candidate_from_critic.py`: validates the critic response and performs deterministic preselection.
- `compare_mask_to_oracle.py`: computes evaluation-only IoU and boundary F1 against Candidate I.
- `prompts/`: exact VLM prompt templates.

The scripts were syntax-checked in the artifact environment but were not executed against the user’s desktop repository, SAM2 weights, or Hunyuan installation.
