#!/usr/bin/env bash
set -euo pipefail

BASE_RUN_ID="${1:?Usage: bash create_phase42_mock_selector_for_oakink_run.sh <base_run_id>}"

cd /home/fredcui/Projects/FollowMyHold

RUN="$HOME/foho_phase0/runs/${BASE_RUN_ID}"
OUT_ROOT="$HOME/foho_phase0/inspection/oakink_000/${BASE_RUN_ID}"
CAND="$OUT_ROOT/object_only_candidates"
MOCK="$OUT_ROOT/phase42_selector_mock"

mkdir -p "$CAND" "$MOCK"

# Temporary diagnostic: split Hunyuan HOI into components.
# This is not final semantic object extraction.
for r in 0 1 2; do
  python scripts/phase0/extract_object_candidate_from_hunyuan_hoi.py \
    --mesh "$RUN/hunyuan_hoi_out/oakink_hoi_mesh.ply" \
    --rank "$r" \
    --out "$CAND/hunyuan_component_rank${r}_candidate.ply" || true
done

PYTHONPATH=src python scripts/phase0/select_phase42_object_candidate.py \
  --out_dir "$MOCK" \
  --candidate "hunyuan_rank0" "$CAND/hunyuan_component_rank0_candidate.ply" "hunyuan_component" \
  --candidate "hunyuan_rank1" "$CAND/hunyuan_component_rank1_candidate.ply" "hunyuan_component" \
  --candidate "hunyuan_rank2" "$CAND/hunyuan_component_rank2_candidate.ply" "hunyuan_component" \
  --candidate "final_obj" "$RUN/guidance_out/oakink_obj.ply" "final_guided"

cat "$MOCK/phase42_object_selection_report.json"
