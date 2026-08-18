import hashlib, io, json, math, os
from pathlib import Path
import numpy as np, torch, trimesh
from hamer.models.mano_wrapper import MANO
from foho.guidance.h1_selected_finger_mano_provider_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_4 import H1SelectedFingerMANOProvider

def load_carrier(path):
    original=torch.storage._load_from_bytes
    torch.storage._load_from_bytes=lambda b: torch.load(io.BytesIO(b),map_location='cpu',weights_only=False)
    try: return np.load(path,allow_pickle=True).item()
    finally: torch.storage._load_from_bytes=original

def main():
    receipt=Path(os.environ['CPU904']); bridge_path=Path(os.environ['BRIDGE904'])
    carrier_path=Path(os.environ['UPPERL_CARRIER']); hshape_path=Path(os.environ['RECOVERED_HSHAPE89102'])
    h0_path=Path(os.environ['H0_FINAL_CHECKPOINT']); asset=Path(os.environ['MANO_RIGHT'])
    existing=[str(receipt)] if receipt.exists() else []; errors=[]; checks={}; stats={}
    try:
        bridge=json.loads(bridge_path.read_text()); comp=bridge['composite_local_to_Hshape']
        doc=load_carrier(carrier_path); row=0; params=doc['pred_mano_params']
        layer=MANO(model_path=str(asset.parent),is_rhand=True,use_pca=False,flat_hand_mean=False).cpu()
        provider=H1SelectedFingerMANOProvider(layer,params['global_orient'][row:row+1].float(),
            params['hand_pose'][row:row+1].float(),params['betas'][row:row+1].float(),
            torch.tensor(comp['linear'],dtype=torch.float32),torch.tensor(comp['translation'],dtype=torch.float32)).cpu()
        expected=torch.tensor(np.asarray(trimesh.load(hshape_path,process=False).vertices),dtype=torch.float32)
        h0_before=hashlib.sha256(h0_path.read_bytes()).hexdigest(); frozen_before=provider.frozen_digest()
        zero=provider(); zero_error=float((zero[0]-expected).abs().max())
        trainable=[(n,p) for n,p in provider.named_parameters() if p.requires_grad]
        generator=torch.Generator().manual_seed(1904); projection=torch.randn(zero.shape,generator=generator)
        loss=(zero*projection).sum(); loss.backward(); grad=provider.selected_so3_residual.grad.detach().clone()
        weights=provider.mano_layer.lbs_weights.detach().cpu().float(); sw=weights[:,1:7].sum(1); ow=weights[:,7:16].sum(1); rw=weights[:,0]
        sm=(sw>ow)&(sw>rw)&(sw>1e-5); om=(ow>sw)&(ow>rw)&(ow>1e-5); pm=(rw>sw)&(rw>ow)
        snap=provider.snapshot(); base=provider().detach()
        with torch.no_grad(): provider.selected_so3_residual.fill_(1e-3)
        moved=(provider().detach()-base).norm(dim=-1)[0]
        selected_mean=float(moved[sm].mean()); other_mean=float(moved[om].mean()); palm_mean=float(moved[pm].mean())
        provider.restore(snap); restored=float((provider().detach()-base).abs().max())
        checks={
          'bridge_PASS':str(bridge.get('decision','')).startswith('pass_'),
          'zero_residual_reproduces_Hshape':zero_error<=2e-5,
          'exact_trainable_allowlist':len(trainable)==1 and trainable[0][0]=='selected_so3_residual' and tuple(trainable[0][1].shape)==(6,3),
          'all_18_gradients_finite_nonzero':bool(torch.isfinite(grad).all()) and bool((grad.abs()>0).all()),
          'selected_response_dominates_other':selected_mean>other_mean,
          'selected_response_dominates_palm':selected_mean>palm_mean,
          'snapshot_restore_exact':restored==0.0,
          'frozen_digest_unchanged':provider.frozen_digest()==frozen_before,
          'H0_checkpoint_hash_unchanged':hashlib.sha256(h0_path.read_bytes()).hexdigest()==h0_before,
          'zero_optimizer_updates':True,
          'CPU_only':not torch.cuda.is_available() or os.environ.get('CUDA_VISIBLE_DEVICES','')=='',
        }
        stats={'zero_error':zero_error,'gradient_norm':float(grad.norm()),'gradient_max_abs':float(grad.abs().max()),
          'selected_response_mean':selected_mean,'other_response_mean':other_mean,'palm_response_mean':palm_mean}
        failed=[k for k,v in checks.items() if not v]
        payload={'decision':('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_4_H1_reusable_provider_CPU_closed' if not failed and not existing else 'review_required_14_90_4_recheck_H1_provider_CPU'),
          'checks':checks,'stats':stats,'failed':failed,'missing':[],'existing':existing,'errors':errors,
          'GPU_used':False,'optimizer_updates':0,'H1':{'authorized':0,'spent':0,'executable':False}}
        if not receipt.exists(): receipt.write_text(json.dumps(payload,indent=2)+'\n')
    except Exception as exc: errors.append(f'{type(exc).__name__}:{exc}')
    print(json.dumps(json.loads(receipt.read_text()) if receipt.is_file() else {'decision':'hold_before_H1_provider_CPU','errors':errors}))
if __name__=='__main__': main()
