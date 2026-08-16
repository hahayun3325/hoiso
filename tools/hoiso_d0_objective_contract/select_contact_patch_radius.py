#!/usr/bin/env python3
import json
import sys
from pathlib import Path

HARD_REQUIREMENTS=('contains_seed','connected_by_growth','projects_nonempty','intersects_overlap_or_ROI','local_under_20pct_visible_object')

def select_contact_patch(report,minimum_precision=.90,minimum_relative_support=.50):
    rows=report.get('facts',{}).get('candidates',{})
    assessed=[]; errors=[]
    if not isinstance(rows,dict) or not rows:
        return {'decision':'review_required_missing_radius_candidates','selected_label':None,'assessed_candidates':[],'errors':['missing_candidates']}
    maximum_support=max(int(row.get('ROI_pixel_count',0)) for row in rows.values())
    if maximum_support<=0:
        return {'decision':'review_required_zero_in_ROI_support','selected_label':None,'assessed_candidates':[],'errors':['zero_maximum_support']}
    for label,row in rows.items():
        visible=int(row.get('visible_pixel_count',0)); support=int(row.get('ROI_pixel_count',0)); precision=support/max(1,visible); relative=support/maximum_support
        hard=all(row.get('checks',{}).get(name) is True for name in HARD_REQUIREMENTS)
        feasible=hard and precision>=minimum_precision and relative>=minimum_relative_support
        assessed.append({'label':label,'radius_fraction':float(row.get('radius_fraction_of_object_diagonal')),'visible_pixels':visible,'in_ROI_pixels':support,'maximum_in_ROI_pixels_in_sweep':maximum_support,'patch_precision':precision,'relative_in_ROI_support':relative,'hard_requirements_pass':hard,'feasible':feasible})
    feasible=sorted((row for row in assessed if row['feasible']),key=lambda row:(row['radius_fraction'],row['label']))
    selected=feasible[0]['label'] if feasible else None
    return {'decision':'pass_automatic_contact_patch_radius_selection' if selected else 'review_required_no_feasible_radius','selected_label':selected,'policy':{'minimum_patch_precision':minimum_precision,'minimum_relative_in_ROI_support':minimum_relative_support,'ranking':'smallest_radius_among_feasible','no_feasible_action':'review_or_expand_sweep'},'assessed_candidates':assessed,'errors':errors}

def option(name):
    positions=[index for index,value in enumerate(sys.argv[:-1]) if value==name]
    return sys.argv[positions[-1]+1] if positions else None

def main():
    report_name=option('--report'); output_name=option('--output'); failed=[]; missing=[]; errors=[]
    if not report_name: missing.append('--report')
    if not output_name: missing.append('--output')
    report_path=Path(report_name) if report_name else None; output_path=Path(output_name) if output_name else None
    if report_path is not None and not report_path.is_file(): missing.append(str(report_path))
    if missing:
        payload={'decision':'hold_missing_selector_inputs','selected_label':None,'failed':failed,'missing':missing,'errors':errors}
    else:
        try: payload=select_contact_patch(json.loads(report_path.read_text()))
        except Exception as exc: payload={'decision':'hold_selector_exception','selected_label':None,'failed':failed,'missing':missing,'errors':[f'{type(exc).__name__}:{exc}']}
    if output_path is not None:
        output_path.parent.mkdir(parents=True,exist_ok=True); output_path.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload))

if __name__=='__main__': main()
