import argparse,hashlib,json
from pathlib import Path

def sha256(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rewrite(value,pairs):
    if isinstance(value,str):
        for old,new in pairs: value=value.replace(old,new)
        return value
    if isinstance(value,list): return [rewrite(item,pairs) for item in value]
    if isinstance(value,dict): return {key:rewrite(item,pairs) for key,item in value.items()}
    return value

def build(template_path,output_path,receipt_path,stage_name,old_root,new_root,input_pairs):
    errors=[]; template=Path(template_path)
    try: manifest=json.loads(template.read_text())
    except Exception as exc: manifest={}; errors.append(f'template:{type(exc).__name__}:{exc}')
    pairs=[(old_root,new_root)]+list(input_pairs)
    manifest=rewrite(manifest,pairs)
    stages=[row for row in manifest.get('stages',[]) if row.get('name')==stage_name]
    if len(stages)!=1: errors.append(f'stage_count:{stage_name}:{len(stages)}')
    manifest['stages']=stages
    refreshed=[]
    if len(stages)==1:
        for item in stages[0].get('inputs',[]):
            path=Path(item.get('path',''))
            if not path.is_file(): errors.append('missing_input:'+str(path)); continue
            item['sha256']=sha256(path)
            refreshed.append({'path':str(path),'sha256':item['sha256']})
    serialized=json.dumps(manifest,sort_keys=True)
    for old,_ in pairs:
        if old and old in serialized: errors.append('stale_token:'+old)
    output=Path(output_path)
    if not errors:
        output.parent.mkdir(parents=True,exist_ok=True); temporary=output.with_suffix('.tmp')
        temporary.write_text(json.dumps(manifest,indent=2)+'\n'); temporary.replace(output)
    payload={'schema':'tracehoi.FoundationManifestStageRebind.v1','stage':stage_name,
      'template':str(template.resolve()),'template_sha256':sha256(template) if template.is_file() else None,
      'output':str(output.resolve()) if output.is_file() else None,
      'output_sha256':sha256(output) if output.is_file() else None,
      'refreshed_inputs':refreshed,'replacement_count':len(pairs),'errors':errors,
      'decision':'foundation_manifest_stage_rebind_closed' if not errors else 'review_foundation_manifest_stage_rebind'}
    receipt=Path(receipt_path); receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps(payload,indent=2)+'\n'); return payload

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--template',required=True); parser.add_argument('--output',required=True)
    parser.add_argument('--receipt',required=True); parser.add_argument('--stage',required=True)
    parser.add_argument('--old-root',required=True); parser.add_argument('--new-root',required=True)
    parser.add_argument('--replace-input',action='append',default=[])
    args=parser.parse_args(); pairs=[]
    for item in args.replace_input:
        if '=' not in item: pairs.append((item,''))
        else: pairs.append(tuple(item.split('=',1)))
    print(json.dumps(build(args.template,args.output,args.receipt,args.stage,args.old_root,args.new_root,pairs),indent=2))

if __name__=='__main__': main()
