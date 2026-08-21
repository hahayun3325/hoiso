from __future__ import annotations
import hashlib, json, os
from pathlib import Path
from typing import Any
from foho.configs import load_config
from foho.main import _cmd, _env_foho

SECRET_NAMES={'OPENAI_API_KEY','GEMINI_API_KEY','HF_TOKEN'}
ADAPTER='foho.automation.foundation_run_in_conda_adapter:run'

def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def _input(role: str,path: str) -> dict[str,Any]:
    owner=Path(path)
    if not owner.is_file(): raise FileNotFoundError(str(owner))
    return {'role':role,'path':str(owner.resolve()),'sha256':_sha(owner)}
def _safe_env(cfg) -> dict[str,str]:
    return {key:value for key,value in _env_foho(cfg).items()
            if key not in SECRET_NAMES}
def _env_file(path: str|Path) -> dict[str,str]:
    values={}
    for line in Path(path).read_text().splitlines():
        if line and not line.lstrip().startswith('#') and '=' in line:
            key,value=line.split('=',1); values[key]=value
    return values
def _stage(name,module,args,cfg,cwd,roots,receipt,inputs):
    return {'name':name,'callable':ADAPTER,
      'kwargs':{'runner_args':[cfg.conda_sh,cfg.env_name,_cmd(module,args),cwd,_safe_env(cfg)],
                'runner_kwargs':{},'output_roots':[str(Path(p).resolve()) for p in roots],
                'output_receipt':str(Path(receipt).resolve())},
      'inputs':inputs,
      'expected_outputs':[{'role':name+'_inventory','path':str(Path(receipt).resolve())}],
      'env':{'PYTHONPATH':str((Path(cfg.project_root)/'src').resolve())},
      'timeout_seconds':14400}

def build(config_path: str|Path,manifest_path: str|Path) -> dict[str,Any]:
    cfg=load_config(str(config_path)); raw_config=_env_file(config_path)
    base=Path(cfg.base_dir).resolve()
    crop=_input('accepted_crop',cfg.image_path)
    category=_input('Q0_category_CSV',cfg.gemini_responses)
    object_prompt=_input('Q0_object_prompt_CSV',raw_config['OBJECT_PROMPT_CSV'])
    flux_prompt=_input('Q0_flux_prompt_CSV',raw_config['FLUX_PROMPT_CSV'])
    inv={
      'preprocess':base/'01_preprocess/stage_inventory.json',
      'inpaint':Path(cfg.cropped_inpainted_obj)/'stage_inventory.json',
      'hamer':Path(cfg.hamer_out_path)/'stage_inventory.json',
      'moge':Path(cfg.moge_out_path)/'stage_inventory.json',
      'hunyuan':Path(cfg.hunyuan_hoi_mesh_path)/'stage_inventory.json',
      'h2m':Path(cfg.h2m_rt_path)/'stage_inventory.json',
      'mano':Path(cfg.aligned_mano_path)/'stage_inventory.json'}
    prior=lambda role,key:{'role':role,'path':str(inv[key].resolve())}
    stages=[
      _stage('get_hunyuan_input','foho.preprocess.get_hunyuan_input',{
       'split_path':cfg.split_path,'image_path':cfg.image_path,
       'occ_img_dir':cfg.masked_obj_path,'cropped_img_dir':cfg.cropped_hoi_path,
       'cropped_img_wo_bckg_dir':cfg.cropped_hoi_wo_bckg_path,
       'mask_dir':cfg.mask_dir_path,'original_img_dir':cfg.original_img_dir,
       'gemini_responses':object_prompt['path'],'project_root':cfg.project_root},
       cfg,cfg.project_root,[cfg.masked_obj_path,cfg.cropped_hoi_path,
        cfg.cropped_hoi_wo_bckg_path,cfg.mask_dir_path,cfg.original_img_dir],
       inv['preprocess'],[crop,object_prompt]),
      _stage('inpaint','foho.preprocess.inpaint',{
       'save_dir':cfg.cropped_inpainted_obj,'cropped_img_dir':cfg.cropped_hoi_path,
       'gemini_responses':flux_prompt['path']},cfg,cfg.project_root,
       [cfg.cropped_inpainted_obj],inv['inpaint'],
       [flux_prompt,prior('preprocess_inventory','preprocess')]),
      _stage('moge','foho.geometry.moge',{
       'project_root':cfg.project_root,'input':cfg.cropped_hoi_wo_bckg_path,
       'output':cfg.moge_out_path},cfg,cfg.project_root,[cfg.moge_out_path],
       inv['moge'],[prior('preprocess_inventory','preprocess')]),
      _stage('hunyuan','foho.geometry.hunyuan',{
       'project_root':cfg.project_root,'image_dir':cfg.cropped_hoi_wo_bckg_path,
       'save_dir':cfg.hunyuan_hoi_mesh_path},cfg,cfg.project_root,
       [cfg.hunyuan_hoi_mesh_path],inv['hunyuan'],
       [prior('preprocess_inventory','preprocess')]),
      _stage('hamer','foho.hand.hamer',{
       'hamer_demo_dir':cfg.hamer_demo_dir,'img_folder':cfg.cropped_hoi_path,
       'out_folder':cfg.hamer_out_path,'full_img_dir':cfg.original_img_dir,
       'save_mesh':True},cfg,cfg.hamer_demo_dir,[cfg.hamer_out_path],
       inv['hamer'],[prior('preprocess_inventory','preprocess')]),
      _stage('h2m','foho.alignment.h2m',{
       'hunyuan_mesh_dir':cfg.hunyuan_hoi_mesh_path,
       'moge_out_dir':cfg.moge_out_path,'h2m_rt_dir':cfg.h2m_rt_path},
       cfg,cfg.project_root,[cfg.h2m_rt_path],inv['h2m'],
       [prior('moge_inventory','moge'),prior('hunyuan_inventory','hunyuan')]),
      _stage('mano_registration','foho.alignment.mano',{
       'hamer_out_dir':cfg.hamer_out_path,
       'hunyuan_mesh_dir':cfg.hunyuan_hoi_mesh_path,
       'aligned_mano_dir':cfg.aligned_mano_path},cfg,cfg.project_root,
       [cfg.aligned_mano_path],inv['mano'],
       [prior('hamer_inventory','hamer'),prior('hunyuan_inventory','hunyuan')])]
    manifest={'schema':'tracehoi.FreshFoundationManifest.v1',
      'case_id':'alapuse02v3n60','fresh_output_root':str(base),
      'stages':stages,'excluded_commands':['foho.preprocess.gemini_objname','foho.guidance.run'],
      'Q0_reused':True,'Q0_category_compatibility_owner':category,
      'Q1_after_stage':'mano_registration'}
    raw=json.dumps(manifest,sort_keys=True)
    if any(name in raw for name in SECRET_NAMES):
        raise RuntimeError('secret name serialized')
    target=Path(manifest_path); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
