from __future__ import annotations
import argparse,csv,json,statistics
from pathlib import Path
from metrics import evaluate_case

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',required=True)
    ap.add_argument('--per-case-csv',required=True)
    ap.add_argument('--summary-json',required=True)
    args=ap.parse_args()
    payload=json.loads(Path(args.manifest).read_text())
    rows=[]
    for case in payload['cases']:
        try: rows.append(evaluate_case(case))
        except Exception as exc: rows.append({'case_id':case['case_id'],'success':False,
                                              'error':f'{type(exc).__name__}:{exc}'})
    fields=['case_id','success','CD_cm2','F5','F10','IV_cm3','error']
    with Path(args.per_case_csv).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    good=[r for r in rows if r['success']]
    summary={'schema':'foho.FollowMyHoldCompatibleMetrics.v1',
             'parity_status':'candidate_not_officially_certified',
             'split_sha256':payload['split_sha256'],'total_cases':len(rows),'successful_cases':len(good),
             'RR':len(good)/len(rows) if rows else 0.0}
    for key in ('CD_cm2','F5','F10','IV_cm3'):
        summary[key]=statistics.fmean(float(r[key]) for r in good) if good else None
    Path(args.summary_json).write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
