from __future__ import annotations
import argparse, hashlib, json, math, os
from pathlib import Path
from typing import Any

RASTER={'.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff'}
MESH={'.ply','.obj','.glb','.gltf','.stl','.off'}

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def atomic(path: Path, payload: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    os.replace(temp,path)

def load(path: str|Path) -> dict[str,Any]:
    return json.loads(Path(path).read_text())

def flatten_inventory(path: str|Path) -> list[dict[str,Any]]:
    packet=load(path)
    if packet.get('decision')!='foundation_stage_artifact_inventory_closed':
        raise RuntimeError('inventory not closed: '+str(path))
    rows=[]
    for root in packet.get('output_roots',[]):
        for row in root.get('files',[]):
            asset=Path(row['path'])
            if not asset.is_file() or asset.stat().st_size!=row.get('bytes') or sha(asset)!=row.get('sha256'):
                raise RuntimeError('inventory asset mismatch: '+str(asset))
            rows.append({'path':str(asset),'sha256':row['sha256'],'bytes':row['bytes'],
                         'suffix':asset.suffix.lower()})
    if len(rows)!=packet.get('file_count'): raise RuntimeError('inventory file_count mismatch')
    return rows

def score(row: dict[str,Any], positive: tuple[str,...], negative: tuple[str,...]=()) -> tuple[int,int,str]:
    name=Path(row['path']).name.lower(); value=0
    for index,token in enumerate(positive):
        if token in name: value+=100-index
    for token in negative:
        if token in name: value-=150
    if row['suffix'] in RASTER: value+=20
    return value,-len(name),name

def choose(rows: list[dict[str,Any]], *, suffixes: set[str]|None=None,
           positive: tuple[str,...]=(), negative: tuple[str,...]=()) -> dict[str,Any]:
    pool=[row for row in rows if suffixes is None or row['suffix'] in suffixes]
    if not pool: raise RuntimeError('no asset candidate for '+repr((suffixes,positive)))
    return max(pool,key=lambda row:score(row,positive,negative))

def resolve(config: dict[str,Any]) -> tuple[list[dict[str,Any]],dict[str,list[dict[str,Any]]]]:
    stages={stage:flatten_inventory(path) for stage,path in config['inventories'].items()}
    crop=Path(config['accepted_crop']['path'])
    if not crop.is_file() or sha(crop)!=config['accepted_crop']['sha256']:
        raise RuntimeError('accepted crop mismatch')
    obj=choose(stages['get_hunyuan_input'],suffixes=RASTER,
               positive=('object_mask','obj_mask','object','obj','mask'),negative=('hand',))
    hand=choose(stages['get_hunyuan_input'],suffixes=RASTER,
                positive=('hand_mask','hand','mask'),negative=('object','obj'))
    if obj['path']==hand['path']: raise RuntimeError('object and hand masks resolved to one file')
    cells=[
      {'id':'accepted_crop','title':'A. accepted cropped RGB','kind':'raster',
       'assets':[{'path':str(crop),'sha256':config['accepted_crop']['sha256'],'bytes':crop.stat().st_size}]},
      {'id':'object_mask','title':'B. fresh object mask','kind':'raster','assets':[obj]},
      {'id':'hand_mask','title':'C. fresh hand mask','kind':'raster','assets':[hand]},
      {'id':'inpainted_object','title':'D. fresh inpainted object','kind':'raster',
       'assets':[choose(stages['inpaint'],suffixes=RASTER,positive=('inpaint','output','image'))]},
      {'id':'moge_scene','title':'E. fresh MoGe scene / depth','kind':'raster',
       'assets':[choose(stages['moge'],suffixes=RASTER,
                        positive=('depth_vis','depth','normal','image','visual'))]},
      {'id':'hunyuan_mesh','title':'F. fresh Hunyuan object mesh','kind':'mesh',
       'assets':[choose(stages['hunyuan'],suffixes=MESH,positive=('mesh','glb','obj'))]},
      {'id':'hamer_hand','title':'G. fresh HaMeR hand','kind':'visual_or_mesh',
       'assets':[choose(stages['hamer'],suffixes=RASTER|MESH,
                        positive=('render','overlay','visual','hand','mesh'))]},
      {'id':'h2m_mano','title':'H. fresh H2M + MANO registration','kind':'registration',
       'assets':[choose(stages['h2m'],positive=('h2m','transform','matrix','rt')),
                 choose(stages['mano_registration'],positive=('mano','aligned','registered','mesh'))]}]
    return cells,stages

def font(size: int):
    from PIL import ImageFont
    candidates=['/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf',
      '/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf',
      '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf']
    for raw in candidates:
        path=Path(raw)
        if path.is_file(): return ImageFont.truetype(str(path),size=size),str(path)
    return ImageFont.load_default(),'PIL_default'

def raster_tile(path: Path, size: tuple[int,int]):
    from PIL import Image
    image=Image.open(path).convert('RGB'); image.thumbnail(size)
    canvas=Image.new('RGB',size,'white')
    canvas.paste(image,((size[0]-image.width)//2,(size[1]-image.height)//2))
    return canvas

def mesh_tile(path: Path, size: tuple[int,int], color=(26,126,160)):
    import numpy as np, trimesh
    from PIL import Image, ImageDraw
    loaded=trimesh.load(path,process=False,force='scene')
    scene_geometry_count=len(loaded.geometry) if isinstance(loaded,trimesh.Scene) else 1
    mesh=loaded.dump(concatenate=True) if isinstance(loaded,trimesh.Scene) else loaded
    vertices=np.asarray(mesh.vertices,dtype=float); faces=np.asarray(mesh.faces,dtype=int)
    if vertices.ndim!=2 or len(vertices)<3 or faces.ndim!=2 or len(faces)<1:
        raise RuntimeError('invalid mesh: '+str(path))
    if not np.isfinite(vertices).all(): raise RuntimeError('nonfinite mesh: '+str(path))
    center=(vertices.min(axis=0)+vertices.max(axis=0))/2; vertices=vertices-center
    scale=float(np.ptp(vertices,axis=0).max())
    if not math.isfinite(scale) or scale<=0: raise RuntimeError('degenerate mesh: '+str(path))
    vertices/=scale
    edges=np.vstack((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]))
    edges=np.unique(np.sort(edges,axis=1),axis=0)
    if len(edges)>24000: edges=edges[np.linspace(0,len(edges)-1,24000,dtype=int)]
    try: component_count=len(mesh.split(only_watertight=False))
    except Exception: component_count=-1
    canvas=Image.new('RGB',size,'white'); draw=ImageDraw.Draw(canvas); body,_=font(17)
    views=[('XY',0,1),('XZ',0,2),('YZ',1,2)]; gap=10; footer_h=34
    plot_h=size[1]-footer_h; panel_w=(size[0]-2*gap)//3
    for view,(label,a,b) in enumerate(views):
        offset=view*(panel_w+gap); pts=vertices[:,[a,b]]
        px=offset+panel_w/2+pts[:,0]*(panel_w*.82)
        py=plot_h/2-pts[:,1]*(plot_h*.76)
        if view:
            draw.line((offset-gap/2,0,offset-gap/2,plot_h),fill=(170,170,170),width=1)
        draw.rectangle((offset+4,4,offset+42,27),fill='white')
        draw.text((offset+8,5),label,font=body,fill='black')
        for i,j in edges:
            draw.line((float(px[i]),float(py[i]),float(px[j]),float(py[j])),fill=color,width=1)
    draw.rectangle((0,plot_h,size[0],size[1]),fill='white')
    caption=('one mesh | three orthographic views | V='+str(len(vertices))+
             ' F='+str(len(faces))+' CC='+str(component_count)+
             ' scene-geometries='+str(scene_geometry_count))
    draw.text((8,plot_h+6),caption,font=body,fill='black')
    return canvas

def metadata_tile(paths: list[Path], size: tuple[int,int]):
    from PIL import Image, ImageDraw
    canvas=Image.new('RGB',size,'white'); draw=ImageDraw.Draw(canvas); body,_=font(20)
    y=15
    for path in paths:
        lines=[path.name,f'type: {path.suffix.lower() or "file"}',f'bytes: {path.stat().st_size}',
               f'sha256: {sha(path)[:20]}...']
        if path.suffix.lower() in {'.json','.txt','.csv'}:
            try:
                preview=path.read_text(errors='replace').replace('\n',' ')[:120]
                lines.append('preview: '+preview)
            except Exception: pass
        elif path.suffix.lower() in {'.npy','.npz'}:
            try:
                import numpy as np
                value=np.load(path,allow_pickle=False)
                if hasattr(value,'files'):
                    lines.append('arrays: '+','.join(value.files[:8]))
                else:
                    lines.append('shape: '+repr(tuple(value.shape)))
                    lines.append('finite: '+str(bool(np.all(np.isfinite(value)))))
            except Exception as exc: lines.append('array read: '+type(exc).__name__)
        for line in lines:
            draw.text((15,y),line,font=body,fill='black'); y+=25
        y+=10
    return canvas

def render_cell(cell: dict[str,Any], size: tuple[int,int]):
    paths=[Path(row['path']) for row in cell['assets']]
    first=paths[0]
    if cell['kind']=='raster': return raster_tile(first,size)
    if cell['kind']=='mesh': return mesh_tile(first,size)
    if cell['kind']=='visual_or_mesh':
        return raster_tile(first,size) if first.suffix.lower() in RASTER else mesh_tile(first,size,(178,43,128))
    mano=paths[-1]
    if mano.suffix.lower() in RASTER: return raster_tile(mano,size)
    if mano.suffix.lower() in MESH:
        image=mesh_tile(mano,size,(178,43,128))
        from PIL import ImageDraw
        draw=ImageDraw.Draw(image); body,_=font(18)
        draw.rectangle((0,size[1]-58,size[0],size[1]),fill='white')
        draw.text((8,size[1]-54),'H2M: '+paths[0].name,font=body,fill='black')
        draw.text((8,size[1]-30),'MANO: '+mano.name,font=body,fill='black')
        return image
    return metadata_tile(paths,size)

def build(config_path: str|Path, output_path: str|Path, manifest_path: str|Path) -> dict[str,Any]:
    from PIL import Image, ImageDraw
    config=load(config_path); cells,stages=resolve(config)
    cell_w,cell_h,label_h=640,420,48
    canvas=Image.new('RGB',(cell_w*4,(cell_h+label_h)*2),'white')
    title_font,font_owner=font(23)
    for index,cell in enumerate(cells):
        x=(index%4)*cell_w; y=(index//4)*(cell_h+label_h)
        tile=render_cell(cell,(cell_w,cell_h)); canvas.paste(tile,(x,y+label_h))
        draw=ImageDraw.Draw(canvas); draw.rectangle((x,y,x+cell_w,y+label_h),fill=(18,18,18))
        draw.text((x+10,y+10),cell['title'],font=title_font,fill='white')
    output=Path(output_path); output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_suffix('.tmp.png'); canvas.save(temp,format='PNG'); os.replace(temp,output)
    payload={'schema':'tracehoi.Q1EvidencePanelManifest.v1','case_id':config['case_id'],
      'panel':str(output.resolve()),'panel_sha256':sha(output),'width':canvas.width,'height':canvas.height,
      'font_owner':font_owner,'config':str(Path(config_path).resolve()),
      'config_sha256':sha(Path(config_path)),'policy':config['policy'],
      'cells':cells,'inventory_file_counts':{key:len(value) for key,value in stages.items()},
      'optimizer_updates':0,'api_calls':0,'errors':[],
      'decision':'Q1_evidence_panel_closed'}
    atomic(Path(manifest_path),payload); return payload

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True); parser.add_argument('--panel',required=True)
    parser.add_argument('--manifest',required=True); args=parser.parse_args()
    result=build(args.config,args.panel,args.manifest)
    print(json.dumps({'decision':result['decision'],'panel':result['panel'],
      'panel_sha256':result['panel_sha256'],'manifest':args.manifest},indent=2))
if __name__=='__main__': main()
