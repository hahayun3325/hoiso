from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
NEGATIVE={"no","not","without","exclude","excluding","except"}
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def collect(node,key,out):
    if isinstance(node,dict):
        for name,value in node.items():
            if name==key: out.append(value)
            collect(value,key,out)
    elif isinstance(node,list):
        for value in node: collect(value,key,out)
def unique_scalar(node,key):
    values=[]; collect(node,key,values); result=[]
    for value in values:
        if isinstance(value,str) and value.strip() and value.strip() not in result: result.append(value.strip())
    if len(result)!=1: raise ValueError(f"{key}_must_be_unique:{result}")
    return result[0]
def compile_keywords(packet,handoff,branch="recovery",limit=8):
    if branch not in {"primary","recovery"}: raise ValueError("branch")
    category=unique_scalar(packet,"object_category")
    frozen=(handoff.get(branch+"_values") or {}).get("object_segmentation")
    if not isinstance(frozen,list) or not frozen: raise ValueError("object_segmentation_keywords")
    values=[]
    for raw in [category,*frozen]:
        if not isinstance(raw,str) or not raw.strip(): raise ValueError("empty_keyword")
        value=" ".join(raw.strip().split())
        if any(mark in value for mark in [",","\n","\r"]): raise ValueError("unsafe_delimiter")
        if set(value.casefold().split()).intersection(NEGATIVE): raise ValueError("negative_keyword")
        if value.casefold() not in {item.casefold() for item in values}: values.append(value)
    if len(values)>limit: raise ValueError(f"keyword_limit:{len(values)}>{limit}")
    if values[0].casefold()!=category.casefold(): raise ValueError("category_not_first")
    return category,values,", ".join(values)
def write_view(packet_path,handoff_path,branch,image_path,output_csv,receipt_path,limit=8):
    packet=json.loads(Path(packet_path).read_text()); handoff=json.loads(Path(handoff_path).read_text())
    image=Path(image_path).resolve()
    if not image.is_file(): raise FileNotFoundError(image)
    category,keywords,encoded=compile_keywords(packet,handoff,branch,limit)
    target=Path(output_csv); target.parent.mkdir(parents=True,exist_ok=True); temporary=target.with_suffix('.csv.tmp')
    with temporary.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['image_id','image_path','response'])
        writer.writeheader(); writer.writerow({'image_id':image.stem.split('_cropped')[0],
          'image_path':str(image),'response':encoded})
    temporary.replace(target)
    payload={'schema':'tracehoi.Q0FoundationPromptGroundingReceipt.v1','branch':branch,
      'object_category':category,'keywords':keywords,'encoded':encoded,
      'packet':str(Path(packet_path).resolve()),'packet_sha256':sha(packet_path),
      'handoff':str(Path(handoff_path).resolve()),'handoff_sha256':sha(handoff_path),
      'image':str(image),'image_sha256':sha(image),'output_CSV':str(target.resolve()),
      'output_CSV_sha256':sha(target),'negative_prompt_used':False,
      'fixed_hand_prompt':'only hand','api_calls':0,'cuda_started':False,
      'decision':'Q0_category_grounded_prompt_closed'}
    receipt=Path(receipt_path); receipt.parent.mkdir(parents=True,exist_ok=True)
    tmp=receipt.with_suffix('.json.tmp'); tmp.write_text(json.dumps(payload,indent=2)+'\n'); tmp.replace(receipt)
    return payload
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--packet',required=True); parser.add_argument('--handoff',required=True)
    parser.add_argument('--branch',choices=['primary','recovery'],required=True)
    parser.add_argument('--image',required=True); parser.add_argument('--output-csv',required=True)
    parser.add_argument('--receipt',required=True); parser.add_argument('--limit',type=int,default=8)
    args=parser.parse_args(); print(json.dumps(write_view(args.packet,args.handoff,args.branch,args.image,args.output_csv,args.receipt,args.limit),indent=2))
if __name__=='__main__': main()
