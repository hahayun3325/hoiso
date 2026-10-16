from __future__ import annotations
import argparse,base64,hashlib,json,mimetypes,os,random,time
from pathlib import Path
import jsonschema
from openai import OpenAI

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def image_data_url(path):
    mime=mimetypes.guess_type(path)[0] or 'image/png'
    return f'data:{mime};base64,'+base64.b64encode(Path(path).read_bytes()).decode()
def request_hash(gate,image,prompt,schema,model,effort):
    return hashlib.sha256(json.dumps({'gate':gate,'image_sha256':sha(image),
      'prompt_sha256':sha(prompt),'schema_sha256':sha(schema),'model':model,
      'reasoning_effort':effort},sort_keys=True).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--gate',choices=['B','D0'],required=True)
    ap.add_argument('--image',required=True); ap.add_argument('--prompt',required=True)
    ap.add_argument('--schema',required=True); ap.add_argument('--output',required=True)
    ap.add_argument('--receipt',required=True); ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--model',default='gpt-5.5-2026-04-23')
    ap.add_argument('--reasoning-effort',default='high')
    args=ap.parse_args()
    prompt=Path(args.prompt).read_text(); schema=json.loads(Path(args.schema).read_text())
    rid=request_hash(args.gate,args.image,args.prompt,args.schema,args.model,args.reasoning_effort)
    base={'schema':'foho.VLMQueryReceipt.v1','semantic_model_label':'gpt-5.5-high',
          'api_model':args.model,'reasoning_effort':args.reasoning_effort,'gate':args.gate,
          'image_sha256':sha(args.image),'prompt_sha256':sha(args.prompt),
          'output_schema_sha256':sha(args.schema),'request_hash':rid,'store':False}
    if args.dry_run:
        base.update({'status':'dry_run_valid','api_called':False})
        Path(args.receipt).write_text(json.dumps(base,indent=2)+'\n'); print(json.dumps(base,indent=2)); return
    if 'OPENAI_API_KEY' not in os.environ: raise RuntimeError('OPENAI_API_KEY_missing')
    client=OpenAI(); last=None
    for attempt in range(1,4):
        try:
            response=client.responses.create(
              model=args.model,reasoning={'effort':args.reasoning_effort},store=False,
              input=[{'role':'system','content':[{'type':'input_text','text':prompt}]},
                     {'role':'user','content':[{'type':'input_text','text':
                       f'Gate {args.gate}. Analyze only the attached original crop. Return the required JSON.'},
                       {'type':'input_image','image_url':image_data_url(args.image),'detail':'high'}]}],
              text={'format':{'type':'json_schema','name':f'hoiso_gate_{args.gate.lower()}',
                              'schema':schema,'strict':True}})
            result=json.loads(response.output_text); jsonschema.validate(result,schema)
            out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(json.dumps(result,indent=2)+'\n')
            usage=response.usage.model_dump() if response.usage else None
            base.update({'status':'success','api_called':True,'attempt':attempt,
                         'response_id':response.id,'usage':usage,'output_sha256':sha(out)})
            Path(args.receipt).write_text(json.dumps(base,indent=2)+'\n')
            print(json.dumps(base,indent=2)); return
        except Exception as exc:
            last=exc
            status=getattr(exc,'status_code',None)
            if status not in (429,500,502,503,504) or attempt==3: raise
            time.sleep((2**attempt)+random.random())
    raise last
if __name__=='__main__': main()
