# Phase 0 evaluation script inventory

## Scripts matching eval / metric / alignment
scripts/phase0/align_selected_object_to_final_obj_bbox.py
scripts/phase0/audit_arctic_phase017_generated_files.py
scripts/phase0/audit_arctic_selector_native_v2_sources.py
scripts/phase0/build_arctic_final_metric_overlay_image.py
scripts/phase0/build_arctic_final_qual_panel.py
scripts/phase0/build_arctic_final_qual_panel_source_manifest.py
scripts/phase0/build_arctic_final_report_metrics_csv.py
scripts/phase0/build_arctic_final_report_table.py
scripts/phase0/build_arctic_phase017_eval_manifest.py
scripts/phase0/build_arctic_phase017_paper_eval_manifest.py
scripts/phase0/build_arctic_selected_case_hand_side_map.py
scripts/phase0/build_arctic_selected_eval_mesh_manifest.py
scripts/phase0/check_arctic_paper_eval_readiness.py
scripts/phase0/check_arctic_paper_eval_readiness_v2.py
scripts/phase0/check_mask_inpaint_alignment.py
scripts/phase0/compare_arctic_aket01_manual_vs_official_transform.py
scripts/phase0/compare_arctic_dryrun_vs_surface_metrics.py
scripts/phase0/delete_old_arctic_base_runs_after_v2_success.py
scripts/phase0/delete_salvaged_arctic_from_polluted_oakink.py
scripts/phase0/diagnose_oakink_hand_object_alignment.py
scripts/phase0/evaluate_arctic_aket01_first_metric_dryrun.py
scripts/phase0/evaluate_arctic_default_vs_selector_proxy.py
scripts/phase0/evaluate_arctic_selected_cases_dryrun.py
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py
scripts/phase0/evaluate_fallback_alignment.py
scripts/phase0/evaluate_oakink000_diagnostic.py
scripts/phase0/evaluate_oakink000_gpt55_stage_contact.py
scripts/phase0/evaluate_oakink000_gpt55_stage_contact_v2.py
scripts/phase0/evaluate_oakink000_object_gt_diagnostic.py
scripts/phase0/evaluate_oakink000_paper_like_metrics.py
scripts/phase0/evaluate_oakink000_selector_candidates_contact.py
scripts/phase0/export_oakink000_selected_gt_annotations.py
scripts/phase0/find_arctic_aket01_in_splits.py
scripts/phase0/find_arctic_input_provenance_by_hash.py
scripts/phase0/inspect_arctic_aket01_crop_coordinate_system.py
scripts/phase0/inspect_arctic_aket01_exact_gt.py
scripts/phase0/inspect_arctic_aket01_metric_gt_keys.py
scripts/phase0/inspect_arctic_aket01_processed_vertices.py
scripts/phase0/inspect_arctic_gt_files_for_aket01.py
scripts/phase0/inspect_arctic_gt_layout_deep.py
scripts/phase0/inventory_arctic_gt_required_dirs.py
scripts/phase0/locate_arctic_aket01_in_p1_train.py
scripts/phase0/make_arctic_aket01_crop_transform_diagnostic_grid.py
scripts/phase0/make_arctic_aket01_gt_2d_crop_overlay.py
scripts/phase0/make_arctic_aket01_gt_2d_official_transform_overlay.py
scripts/phase0/make_arctic_aket01_gt_2d_overlay.py
scripts/phase0/make_arctic_candidate_sheet.py
scripts/phase0/make_arctic_candidate_sheet_v2.py
scripts/phase0/make_arctic_default_vs_selector_panel.py
scripts/phase0/make_arctic_phase017_gpt55_panel.py
scripts/phase0/make_arctic_selected_cases_gt_2d_official_overlays.py
scripts/phase0/make_arctic_selector_native_v2_panel_clean.py
scripts/phase0/make_arctic_selector_native_v2_panel_mixed_paths.py
scripts/phase0/make_arctic_selector_native_v2_panel.py
scripts/phase0/make_oakink000_llm_scene_alignment_grid_short_native.py
scripts/phase0/make_oakink000_paper_like_metric_overlay.py
scripts/phase0/make_oakink000_scene_alignment_grid.py
scripts/phase0/make_oakink000_selected_gt_overlay.py
scripts/phase0/make_oakink000_selected_object_only_grid.py
scripts/phase0/map_arctic_phase017_cases_to_split_rows.py
scripts/phase0/measure_final_hoi_alignment.py
scripts/phase0/mesh_metric_utils.py
scripts/phase0/prepare_arctic_phase017_configs_gpt55_auto.py
scripts/phase0/prepare_arctic_phase017_inputs_gpt55.py
scripts/phase0/prepare_arctic_selector_native_rerun_configs.py
scripts/phase0/repair_all_arctic_selector_native_v2_configs.py
scripts/phase0/repair_arctic_default_configs.py
scripts/phase0/repair_arctic_phase017_configs.py
scripts/phase0/repair_one_arctic_selector_native_config.py
scripts/phase0/run_arctic_default_baselines.sh
scripts/phase0/salvage_arctic_outputs_from_polluted_oakink.py
scripts/phase0/summarize_arctic_phase017_logs.py
scripts/phase0/summarize_arctic_surface_metric_deltas.py
scripts/phase0/verify_arctic_clean_default_vs_selector_pairs.py
scripts/phase0/verify_arctic_default_vs_selector_pairs.py
scripts/phase0/verify_arctic_phase017_outputs.py
scripts/phase0/verify_arctic_phase017_provenance_pixels.py
scripts/phase0/verify_arctic_salvage_readiness.py

## Grep for important metric names
scripts/phase0/summarize_arctic_surface_metric_deltas.py:10:pivot = ok.pivot(index="case", columns="method", values=["object_cd_mm", "object_f5", "object_f10"])
scripts/phase0/summarize_arctic_surface_metric_deltas.py:14:    cd_default = pivot.loc[case, ("object_cd_mm", "default")]
scripts/phase0/summarize_arctic_surface_metric_deltas.py:15:    cd_selector = pivot.loc[case, ("object_cd_mm", "gpt55_selector")]
scripts/phase0/summarize_arctic_surface_metric_deltas.py:16:    f5_default = pivot.loc[case, ("object_f5", "default")]
scripts/phase0/summarize_arctic_surface_metric_deltas.py:17:    f5_selector = pivot.loc[case, ("object_f5", "gpt55_selector")]
scripts/phase0/summarize_arctic_surface_metric_deltas.py:18:    f10_default = pivot.loc[case, ("object_f10", "default")]
scripts/phase0/summarize_arctic_surface_metric_deltas.py:19:    f10_selector = pivot.loc[case, ("object_f10", "gpt55_selector")]
scripts/phase0/summarize_arctic_surface_metric_deltas.py:27:        "f5_delta": f5_selector - f5_default,
scripts/phase0/summarize_arctic_surface_metric_deltas.py:28:        "f10_delta": f10_selector - f10_default,
scripts/phase0/summarize_arctic_surface_metric_deltas.py:33:avg = ok.groupby("method")[["object_cd_mm", "object_f5", "object_f10"]].mean()
scripts/phase0/summarize_arctic_surface_metric_deltas.py:34:cd_default = avg.loc["default", "object_cd_mm"]
scripts/phase0/summarize_arctic_surface_metric_deltas.py:35:cd_selector = avg.loc["gpt55_selector", "object_cd_mm"]
scripts/phase0/compare_arctic_dryrun_vs_surface_metrics.py:11:dry = dry[dry["status"] == "ok"][["case", "method", "object_cd_mm", "object_f5", "object_f10"]]
scripts/phase0/compare_arctic_dryrun_vs_surface_metrics.py:12:surf = surf[surf["status"] == "ok"][["case", "method", "object_cd_mm", "object_f5", "object_f10"]]
scripts/phase0/compare_arctic_dryrun_vs_surface_metrics.py:16:avg_dry = dry.groupby("method")[["object_cd_mm", "object_f5", "object_f10"]].mean()
scripts/phase0/compare_arctic_dryrun_vs_surface_metrics.py:17:avg_surf = surf.groupby("method")[["object_cd_mm", "object_f5", "object_f10"]].mean()
scripts/phase0/build_arctic_final_metric_overlay_image.py:16:avg = df.groupby("label")[["object_cd_mm", "f5", "f10", "hand_align_cd_mm"]].mean()
scripts/phase0/build_arctic_final_metric_overlay_image.py:17:baseline_cd = avg.loc["baseline", "object_cd_mm"]
scripts/phase0/build_arctic_final_metric_overlay_image.py:18:selector_cd = avg.loc["gpt55_selector", "object_cd_mm"]
scripts/phase0/build_arctic_final_metric_overlay_image.py:48:    draw.text((x0 + 20, y), f"Object CD: {row['object_cd_mm']:.2f} mm", fill="black")
scripts/phase0/build_arctic_final_metric_overlay_image.py:50:    draw.text((x0 + 20, y), f"F5: {row['f5']:.4f}", fill="black")
scripts/phase0/build_arctic_final_metric_overlay_image.py:52:    draw.text((x0 + 20, y), f"F10: {row['f10']:.4f}", fill="black")
scripts/phase0/build_arctic_final_metric_overlay_image.py:63:piv = df.pivot(index="case", columns="label", values="object_cd_mm")
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:134:    precision = float((d_pred_gt < tau).mean())
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:135:    recall = float((d_gt_pred < tau).mean())
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:136:    if precision + recall < 1e-12:
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:137:        return 0.0, precision, recall
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:138:    return float(2 * precision * recall / (precision + recall)), precision, recall
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:209:        f5, p5, r5 = fscore(d_pred_gt, d_gt_pred, 0.005)
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:210:        f10, p10, r10 = fscore(d_pred_gt, d_gt_pred, 0.010)
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:219:            "sim_scale": s,
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:220:            "hand_align_rmse_m": hand_rmse,
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:221:            "hand_align_rmse_mm": hand_rmse * 1000.0,
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:223:            "object_cd_mm": cd_mm,
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:224:            "f5": f5,
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:225:            "f10": f10,
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:226:            "precision_5mm": p5,
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:227:            "recall_5mm": r5,
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:228:            "precision_10mm": p10,
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:229:            "recall_10mm": r10,
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:252:            "CD(mm)=", r.get("object_cd_mm"),
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:253:            "F5=", r.get("f5"),
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:254:            "F10=", r.get("f10"),
scripts/phase0/evaluate_oakink000_paper_like_metrics.py:256:            "hand_rmse(mm)=", r.get("hand_align_rmse_mm"),
scripts/phase0/evaluate_arctic_selected_cases_dryrun.py:60:        out[f"precision{int(th*1000)}"] = p
scripts/phase0/evaluate_arctic_selected_cases_dryrun.py:61:        out[f"recall{int(th*1000)}"] = r
scripts/phase0/evaluate_arctic_selected_cases_dryrun.py:111:        "sim_scale": scale,
scripts/phase0/evaluate_arctic_selected_cases_dryrun.py:112:        "hand_cd_mm": hand_m["cd_m"] * 1000,
scripts/phase0/evaluate_arctic_selected_cases_dryrun.py:113:        "object_cd_mm": obj_m["cd_m"] * 1000,
scripts/phase0/evaluate_arctic_selected_cases_dryrun.py:114:        "object_f5": obj_m["f5"],
scripts/phase0/evaluate_arctic_selected_cases_dryrun.py:115:        "object_f10": obj_m["f10"],
scripts/phase0/evaluate_oakink000_object_gt_diagnostic.py:59:    f5, p5, r5 = fscore(d_pred_gt, d_gt_pred, 0.05)
scripts/phase0/evaluate_oakink000_object_gt_diagnostic.py:69:        "precision_tau_0.01": p1,
scripts/phase0/evaluate_oakink000_object_gt_diagnostic.py:70:        "recall_tau_0.01": r1,
scripts/phase0/evaluate_oakink000_object_gt_diagnostic.py:72:        "precision_tau_0.02": p2,
scripts/phase0/evaluate_oakink000_object_gt_diagnostic.py:73:        "recall_tau_0.02": r2,
scripts/phase0/evaluate_oakink000_object_gt_diagnostic.py:74:        "fscore_tau_0.05": f5,
scripts/phase0/evaluate_oakink000_object_gt_diagnostic.py:75:        "precision_tau_0.05": p5,
scripts/phase0/evaluate_oakink000_object_gt_diagnostic.py:76:        "recall_tau_0.05": r5,
scripts/phase0/inspect_oakink000_candidate_hand_params.py:28:        print("  first values:", np.array2string(v[:10], precision=5))
scripts/phase0/evaluate_arctic_aket01_first_metric_dryrun.py:95:        precision = float((d_pred < th).mean())
scripts/phase0/evaluate_arctic_aket01_first_metric_dryrun.py:96:        recall = float((d_gt < th).mean())
scripts/phase0/evaluate_arctic_aket01_first_metric_dryrun.py:97:        f = 2 * precision * recall / max(precision + recall, 1e-12)
scripts/phase0/evaluate_arctic_aket01_first_metric_dryrun.py:99:        out[f"precision_{int(th*1000)}mm"] = precision
scripts/phase0/evaluate_arctic_aket01_first_metric_dryrun.py:100:        out[f"recall_{int(th*1000)}mm"] = recall
scripts/phase0/evaluate_arctic_aket01_first_metric_dryrun.py:171:        "sim_scale": scale,
scripts/phase0/evaluate_arctic_aket01_first_metric_dryrun.py:173:        "hand_cd_mm": hand_metric["cd"] * 1000.0,
scripts/phase0/evaluate_arctic_aket01_first_metric_dryrun.py:175:        "object_cd_mm": obj_metric["cd"] * 1000.0,
scripts/phase0/evaluate_arctic_aket01_first_metric_dryrun.py:176:        "object_f5": obj_metric["fscore_5mm"],
scripts/phase0/evaluate_arctic_aket01_first_metric_dryrun.py:177:        "object_f10": obj_metric["fscore_10mm"],
scripts/phase0/build_arctic_final_report_table.py:15:    "object_cd_mm",
scripts/phase0/build_arctic_final_report_table.py:16:    "f5",
scripts/phase0/build_arctic_final_report_table.py:17:    "f10",
scripts/phase0/build_arctic_final_report_table.py:21:    "sim_scale",
scripts/phase0/build_arctic_final_report_table.py:24:case_table["object_cd_mm"] = case_table["object_cd_mm"].round(2)
scripts/phase0/build_arctic_final_report_table.py:25:case_table["f5"] = case_table["f5"].round(4)
scripts/phase0/build_arctic_final_report_table.py:26:case_table["f10"] = case_table["f10"].round(4)
scripts/phase0/build_arctic_final_report_table.py:29:case_table["sim_scale"] = case_table["sim_scale"].round(4)
scripts/phase0/build_arctic_final_report_table.py:33:    "object_cd_mm",
scripts/phase0/build_arctic_final_report_table.py:34:    "f5",
scripts/phase0/build_arctic_final_report_table.py:35:    "f10",
scripts/phase0/build_arctic_final_report_table.py:39:avg["object_cd_mm"] = avg["object_cd_mm"].round(2)
scripts/phase0/build_arctic_final_report_table.py:40:avg["f5"] = avg["f5"].round(4)
scripts/phase0/build_arctic_final_report_table.py:41:avg["f10"] = avg["f10"].round(4)
scripts/phase0/build_arctic_final_report_table.py:45:piv = df.pivot(index="case", columns="label", values=["object_cd_mm", "f5", "f10"])
scripts/phase0/build_arctic_final_report_table.py:49:    b_cd = piv.loc[case, ("object_cd_mm", "baseline")]
scripts/phase0/build_arctic_final_report_table.py:50:    s_cd = piv.loc[case, ("object_cd_mm", "gpt55_selector")]
scripts/phase0/build_arctic_final_report_table.py:51:    b_f5 = piv.loc[case, ("f5", "baseline")]
scripts/phase0/build_arctic_final_report_table.py:52:    s_f5 = piv.loc[case, ("f5", "gpt55_selector")]
scripts/phase0/build_arctic_final_report_table.py:53:    b_f10 = piv.loc[case, ("f10", "baseline")]
scripts/phase0/build_arctic_final_report_table.py:54:    s_f10 = piv.loc[case, ("f10", "gpt55_selector")]
scripts/phase0/build_arctic_final_report_table.py:60:        "f5_delta": round(s_f5 - b_f5, 4),
scripts/phase0/build_arctic_final_report_table.py:61:        "f10_delta": round(s_f10 - b_f10, 4),
scripts/phase0/build_arctic_final_report_metrics_csv.py:54:        "object_cd_m": r["object_cd_mm"] / 1000.0,
scripts/phase0/build_arctic_final_report_metrics_csv.py:55:        "object_cd_mm": r["object_cd_mm"],
scripts/phase0/build_arctic_final_report_metrics_csv.py:56:        "f5": r["object_f5"],
scripts/phase0/build_arctic_final_report_metrics_csv.py:57:        "f10": r["object_f10"],
scripts/phase0/build_arctic_final_report_metrics_csv.py:58:        "precision_5mm": r["object_precision_5mm"],
scripts/phase0/build_arctic_final_report_metrics_csv.py:59:        "recall_5mm": r["object_recall_5mm"],
scripts/phase0/build_arctic_final_report_metrics_csv.py:60:        "precision_10mm": r["object_precision_10mm"],
scripts/phase0/build_arctic_final_report_metrics_csv.py:61:        "recall_10mm": r["object_recall_10mm"],
scripts/phase0/build_arctic_final_report_metrics_csv.py:62:        "hand_align_cd_mm": r["hand_cd_mm"],
scripts/phase0/build_arctic_final_report_metrics_csv.py:63:        "sim_scale": r["sim_scale"],
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:96:        precision = float((d_pred < th).mean())
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:97:        recall = float((d_gt < th).mean())
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:98:        f = 2.0 * precision * recall / max(precision + recall, 1e-12)
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:100:        out[f"precision_{key}mm"] = precision
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:101:        out[f"recall_{key}mm"] = recall
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:179:        "sim_scale": float(scale),
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:180:        "hand_cd_mm": hand_m["cd_m"] * 1000.0,
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:181:        "object_cd_mm": obj_m["cd_m"] * 1000.0,
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:184:        "object_f5": obj_m["fscore_5mm"],
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:185:        "object_f10": obj_m["fscore_10mm"],
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:186:        "object_precision_5mm": obj_m["precision_5mm"],
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:187:        "object_recall_5mm": obj_m["recall_5mm"],
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:188:        "object_precision_10mm": obj_m["precision_10mm"],
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:189:        "object_recall_10mm": obj_m["recall_10mm"],
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:204:    "hand_cd_mm",
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:205:    "object_cd_mm",
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:206:    "object_f5",
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:207:    "object_f10",
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:208:    "object_precision_5mm",
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:209:    "object_recall_5mm",
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:210:    "object_precision_10mm",
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:211:    "object_recall_10mm",
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:220:        "case", "method", "fixed_gt_hand", "sim_scale", "hand_cd_mm",
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:221:        "object_cd_mm", "object_f5", "object_f10",
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:222:        "object_precision_5mm", "object_recall_5mm",
scripts/phase0/evaluate_arctic_selected_cases_surface_paperstyle.py:223:        "object_precision_10mm", "object_recall_10mm",
scripts/phase0/mesh_metric_utils.py:31:        precision = float(np.mean(d_pred_to_gt < th))
scripts/phase0/mesh_metric_utils.py:32:        recall = float(np.mean(d_gt_to_pred < th))
scripts/phase0/mesh_metric_utils.py:33:        f = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
docs/phase0/phase0_17_arctic_quantitative_observations.md:127:## Precision and recall interpretation
docs/phase0/phase0_17_arctic_quantitative_observations.md:129:In the surface-sampled average, the selector increases precision but decreases recall:
docs/phase0/phase0_17_arctic_quantitative_observations.md:131:- precision@5mm: **0.0408 → 0.0513**
docs/phase0/phase0_17_arctic_quantitative_observations.md:132:- recall@5mm: **0.0394 → 0.0301**
docs/phase0/phase0_17_arctic_quantitative_observations.md:133:- precision@10mm: **0.0726 → 0.1023**
docs/phase0/phase0_17_arctic_quantitative_observations.md:134:- recall@10mm: **0.0707 → 0.0563**
docs/phase0/phase0_17_oakink000_metric_result_interpretation.md:32:The similarity-ICP run is not reliable because it collapsed to `sim_scale=0.0` and produced identical CD for both methods. This is a degenerate transform and should not be reported.
docs/phase0/phase0_17_metric_terms_explained.md:35:## hand_align_rmse
docs/phase0/phase0_17_metric_terms_explained.md:37:hand_align_rmse is the RMSE between the aligned predicted hand vertices and GT hand vertices.
