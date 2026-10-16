from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,log):
    result=subprocess.run(argv,text=True,capture_output=True)
    Path(log).write_text(result.stdout+'\n[stderr]\n'+result.stderr)
    return result.returncode
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True)
    ap.add_argument('--output-root',required=True); ap.add_argument('--dry-run',action='store_true')
    a=ap.parse_args(); m=json.loads(Path(a.manifest).read_text()); out=Path(a.output_root); out.mkdir(parents=True,exist_ok=True)
    statuses={}
    for gate in ('B','D0'):
        g=m['gates'][gate]
        argv=[sys.executable,str(Path(__file__).with_name('query_gate.py')),'--gate',gate,
              '--image',m['original_crop'],'--prompt',g['prompt'],'--schema',g['schema'],
              '--output',str(out/f'gate_{gate}.json'),'--receipt',str(out/f'gate_{gate}_receipt.json'),
              '--model',m['model_snapshot'],'--reasoning-effort',m['reasoning_effort']]
        if a.dry_run: argv.append('--dry-run')
        statuses[gate]=run(argv,out/f'gate_{gate}.log')
    decision='vlm_pair_ready' if statuses=={'B':0,'D0':0} else 'review_required_vlm_pair'
    receipt={'schema':'foho.AutomaticCaseState.v1','case_id':m['case_id'],
             'original_crop_sha256':sha(m['original_crop']),'gate_returncodes':statuses,
             'cross_gate_input_forbidden':True,'decision':decision}
    (out/'case_state.json').write_text(json.dumps(receipt,indent=2)+'\n'); print(json.dumps(receipt,indent=2))
if __name__=='__main__': main()
