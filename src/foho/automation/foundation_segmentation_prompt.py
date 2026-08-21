import argparse,csv,hashlib,json,re
from pathlib import Path
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text())
def compile_label(packet_path,aliases_path):
    packet=load(packet_path); aliases=load(aliases_path).get('aliases',{})
    category=str(packet.get('object_category','')).strip().lower()
    label=aliases.get(category)
    if not label: raise ValueError('unknown_segmentation_category:'+category)
    if not isinstance(label,str) or not re.fullmatch(r'[a-z0-9][a-z0-9 -]{0,30}',label):
        raise ValueError('invalid_grounding_label')
    if ',' in label or len(label.split())>3: raise ValueError('grounding_label_not_short_scalar')
    return category,label
def write(packet_path,aliases_path,image_path,output_csv,receipt_path):
    errors=[]
    try: category,label=compile_label(packet_path,aliases_path)
    except Exception as exc: category=label=None; errors.append(f'{type(exc).__name__}:{exc}')
    image=Path(image_path); target=Path(output_csv)
    if not image.is_file(): errors.append('image_missing')
    if not errors:
        target.parent.mkdir(parents=True,exist_ok=True); temporary=target.with_suffix('.tmp')
        with temporary.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=['image_id','image_path','response'])
            writer.writeheader(); writer.writerow({'image_id':image.name.split('_')[0].split('.')[0],
              'image_path':str(image.resolve()),'response':label})
        temporary.replace(target)
    payload={'schema':'tracehoi.FoundationSegmentationPromptReceipt.v1','category':category,
      'grounding_label':label,'fixed_hand_prompt':'only hand','part_keywords_forwarded':False,
      'output_CSV':str(target) if target.is_file() else None,
      'output_CSV_sha256':sha(target) if target.is_file() else None,'errors':errors,
      'decision':'foundation_single_label_segmentation_prompt_closed' if not errors
                 else 'review_foundation_single_label_segmentation_prompt'}
    Path(receipt_path).write_text(json.dumps(payload,indent=2)+'\n'); return payload
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--packet',required=True)
    parser.add_argument('--aliases',required=True); parser.add_argument('--image',required=True)
    parser.add_argument('--output-csv',required=True); parser.add_argument('--receipt',required=True)
    args=parser.parse_args(); print(json.dumps(write(args.packet,args.aliases,args.image,args.output_csv,args.receipt),indent=2))
if __name__=='__main__': main()
