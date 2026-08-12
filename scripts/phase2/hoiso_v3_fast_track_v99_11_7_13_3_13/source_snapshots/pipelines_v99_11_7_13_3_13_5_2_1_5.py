# Open Source Model Licensed under the Apache License Version 2.0
# and Other Licenses of the Third-Party Components therein:
# The below Model in this distribution may have been modified by THL A29 Limited
# ("Tencent Modifications"). All Tencent Modifications are Copyright (C) 2024 THL A29 Limited.

# Copyright (C) 2024 THL A29 Limited, a Tencent company.  All rights reserved.
# The below software and/or models in this distribution may have been
# modified by THL A29 Limited ("Tencent Modifications").
# All Tencent Modifications are Copyright (C) THL A29 Limited.

# Hunyuan 3D is licensed under the TENCENT HUNYUAN NON-COMMERCIAL LICENSE AGREEMENT
# except for the third-party components listed below.
# Hunyuan 3D does not impose any additional limitations beyond what is outlined
# in the repsective licenses of these third-party components.
# Users must comply with all terms and conditions of original licenses of these third-party
# components and must ensure that the usage of the third party components adheres to
# all relevant laws and regulations.

# For avoidance of doubts, Hunyuan 3D means the large language models and
# their software and algorithms, including trained model weights, parameters (including
# optimizer states), machine-learning model code, inference-enabling code, training-enabling code,
# fine-tuning enabling code and other elements of the foregoing made publicly available
# by Tencent in accordance with TENCENT HUNYUAN COMMUNITY LICENSE AGREEMENT.

# MODIFIED FROM HUNYUAN3D-2.

import copy
import importlib
import inspect
import logging
import os
from typing import List, Optional, Union

import math 
import numpy as np
import torch
import torch.nn.functional as F
import torch.nn as nn
from torchvision import transforms
import trimesh
import yaml
from PIL import Image
from diffusers.utils.torch_utils import randn_tensor
from tqdm import tqdm
from skimage import measure
import matplotlib
matplotlib.use('Agg') # to solve qt thread issue
import matplotlib.pyplot as plt
from kiui.vis import plot_image as plti
import datetime
import json
import cv2

from pytorch3d.structures import Meshes, join_meshes_as_scene
from pytorch3d.renderer.mesh.textures import TexturesVertex
from pytorch3d.renderer.mesh.shader import ShaderBase
from pytorch3d.ops import interpolate_face_attributes
from pytorch3d.renderer.blending import softmax_rgb_blend
from pytorch3d.io import load_ply
from pytorch3d.ops import knn_points
from pytorch3d.io import IO
from pytorch3d.loss import (
    mesh_edge_loss, 
)

import kaolin.non_commercial as knc
import kaolin.ops.mesh as mesh_ops

import utilz.kaolin_sdf_ops as kaolin_sdf
from utilz.code_utils import get_guidance_params

logger = logging.getLogger(__name__)

class PhongNormalShader(ShaderBase): 
    def forward(self, fragments, meshes, **kwargs):
        """
        This shader computes the normal map of the mesh using the vertex normals
        Usage: Inside the pytorch3d renderer
        """
        cameras = kwargs.get("cameras", self.cameras)
        blend_params = kwargs.get("blend_params", self.blend_params)
        faces = meshes.faces_packed()  
        vertex_normals = meshes.verts_normals_packed()  
        faces_normals = vertex_normals[faces]
        ones = torch.ones_like(fragments.bary_coords)
        pixel_normals = interpolate_face_attributes(
            fragments.pix_to_face, ones, faces_normals
        )
        normal_map = softmax_rgb_blend(
                pixel_normals, fragments, blend_params, znear=cameras.znear, zfar=cameras.zfar
            )
        return normal_map
    

def transform_mesh_around_center(mesh, T):
    '''Applies a transformation around the mesh center'''
    verts = mesh.verts_padded().squeeze(0)
    center = (verts.min(dim=0)[0] + verts.max(dim=0)[0]) / 2.0 #verts.mean(dim=0, keepdim=True)  # or use .min() and .max() for bbox center

    R = T[:3, :3]
    t = T[:3, 3]

    verts = (verts - center) @ R.T + center + t
    mesh = mesh.update_padded(verts.unsqueeze(0))
    return mesh


def transform_mesh_around_center_w_scale(mesh, T, scale):
    '''Applies a transformation around the mesh center and scales it'''
    verts = mesh.verts_padded().squeeze(0)
    center = (verts.min(dim=0)[0] + verts.max(dim=0)[0]) / 2.0 #verts.mean(dim=0, keepdim=True)  # or use .min() and .max() for bbox center

    R = T[:3, :3]
    t = T[:3, 3]

    verts = (scale * (verts - center)) @ R.T + center + t
    mesh = mesh.update_padded(verts.unsqueeze(0))
    return mesh


def mano_vert_to_3dkps(mano_mesh, J_regressor, device):
    """
    Converts MANO mesh vertices to respective 3D keypoints.
    mano_mesh: MANO hand mesh (assuming a Pytorch3D mesh with vertices of shape (778,3))
    J_regressor: (16, 778) tensor
    """
    FINGERTIP_IDXS_MANO = torch.tensor([744, 320, 443, 554, 671], dtype=torch.int64, device=device)
    mano_to_openpose = [0, 13, 14, 15, 16, 1, 2, 3, 17, 4, 5, 6, 18, 10, 11, 12, 19, 7, 8, 9, 20]

    verts = mano_mesh.verts_packed()
    fingertip_3d_kps = torch.index_select(verts, 0, FINGERTIP_IDXS_MANO)
    regressed_3d_kps = J_regressor @ verts
    opt_3d_kps = torch.cat([regressed_3d_kps, fingertip_3d_kps], dim=0)
    opt_3d_kps = opt_3d_kps[mano_to_openpose, :]
    return opt_3d_kps


def normal_alignment_loss(rendered_normals, gt_normals, valid_mask):
    '''
    Compute the normal alignment loss between rendered normals and ground truth normals.
    '''
    rendered_normals = F.normalize(rendered_normals, dim=-1)
    gt_normals = F.normalize(gt_normals, dim=-1)

    cos_sim = torch.sum(rendered_normals * gt_normals, dim=-1)  
    loss = 1 - cos_sim  # High when normals are misaligned, 0 when perfectly aligned
    loss = loss[valid_mask]
    return loss.mean()


from pytorch3d.transforms import axis_angle_to_matrix, quaternion_to_matrix, Rotate, Translate
def scale_trans_rot(mesh, scale, trans, rotation):
    '''
    Scale, translate and rotate the mesh.
    '''
    verts = mesh.verts_padded() 
    centroid = verts.mean(dim=1, keepdim=True)
    scaled_verts = scale * (verts - centroid) + centroid 

    if rotation.numel() == 3: # axis-angle
        R = axis_angle_to_matrix(rotation).unsqueeze(0).to(centroid.device)
    elif rotation.numel() == 4: # quaternion
        R = quaternion_to_matrix(rotation).unsqueeze(0).to(centroid.device)
    else:
        raise ValueError(f"Unsupported rotation format with shape {rotation.shape}, expected axis-angle (3,) or quaternion (4,)")

    rotated_verts = torch.bmm(scaled_verts - centroid, R.transpose(1, 2)) + centroid  # (N=1, V, 3)
    trans = trans.view(-1, 1, 3)  # Ensure trans has shape (N, 1, 3)
    transformed_verts = rotated_verts + trans
    transformed_mesh = Meshes(
        verts=transformed_verts,
        faces=mesh.faces_padded(),
        textures=mesh.textures
    )
    return transformed_mesh


def normal_alignment_loss(rendered_normals, gt_normals, valid_mask=None):
    rendered_normals = F.normalize(rendered_normals, dim=-1)
    gt_normals = F.normalize(gt_normals, dim=-1)

    cos_sim = torch.sum(rendered_normals * gt_normals, dim=-1)  
    loss = 1 - cos_sim  # High when normals are misaligned, 0 when perfectly aligned
    if valid_mask is not None:
        loss = loss[valid_mask]
    return loss.mean()


def plot_in_grid(img1, img2, save_path):
    img1_np = img1.detach().cpu().numpy()[0]
    img2_np = img2.detach().cpu().numpy()[0]

    fig, axes = plt.subplots(1, 2, figsize=(4, 2))
    axes[0].imshow(img1_np)
    axes[0].axis('off')  # hide axis

    axes[1].imshow(img2_np)
    axes[1].axis('off')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def safe_intersection_loss(sdf_hand, sdf_obj,
                           sharpness=10.0,
                           clamp_val=5.0,
                           eps=1e-6):
    # 1) clamp extreme SDFs to avoid overflow in exp()
    sdf_h = sdf_hand
    sdf_o = sdf_obj

    # 2) convert to soft‐occupancy
    occ_h = torch.relu(-sdf_h) #torch.sigmoid(-sdf_h * sharpness)
    occ_o = torch.relu(-sdf_o) #torch.sigmoid(-sdf_o * sharpness)

    # 3) compute intersection, safely handle empty meshes
    if occ_h.numel() == 0 or occ_o.numel() == 0:
        print('For intersection loss, one of the meshes is empty')
        return torch.tensor(0.0, device=sdf_h.device, dtype=sdf_h.dtype)

    inter = occ_h * occ_o
    loss = torch.mean(inter)

    # 4) if it’s NaN for any reason, zero it out
    if torch.isnan(loss):
        print('Intersection loss is NaN')
        return torch.tensor(0.0, device=loss.device, dtype=loss.dtype)
    return loss


def honerf_intersection_loss(sdf_hand, sdf_obj):
    """ SDF intersection loss from https://github.com/iscas3dv/HO-NeRF/blob/main/fitting_single.py """
    obj_inner_id = (sdf_obj < 0)
    hand_select_sdf = sdf_hand[obj_inner_id]
    obj_select_sdf = sdf_obj[obj_inner_id]
    penet_points_id = (hand_select_sdf < 0)
    interaction_loss = penet_points_id.sum() / 1000

    return interaction_loss




def foho_clone_p3d_mesh(mesh):
    """Clone a PyTorch3D Meshes object without gradients."""
    try:
        from pytorch3d.structures import Meshes
        verts = mesh.verts_packed().detach().clone()
        faces = mesh.faces_packed().detach().clone()
        return Meshes(verts=[verts], faces=[faces])
    except Exception as e:
        print(f"[FOHO_INTERNAL_SELECTOR_AUTO] clone failed: {e}")
        return None


def foho_score_p3d_mesh(mesh):
    """Compute cheap mesh quality score for a PyTorch3D Meshes object."""
    try:
        import numpy as np
        import trimesh

        verts = mesh.verts_packed().detach().cpu().numpy()
        faces = mesh.faces_packed().detach().cpu().numpy()

        tri = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
        comps = tri.split(only_watertight=False)
        face_counts = np.array([len(c.faces) for c in comps], dtype=float)

        largest_ratio = face_counts.max() / max(len(tri.faces), 1) if len(face_counts) else 0.0
        frag = (len(comps) - 1) + (1.0 - largest_ratio)

        return {
            "components": int(len(comps)),
            "largest_face_ratio": float(largest_ratio),
            "fragmentation_score": float(frag),
            "watertight": bool(tri.is_watertight),
        }
    except Exception as e:
        print(f"[FOHO_INTERNAL_SELECTOR_AUTO] score failed: {e}")
        return {
            "components": 999,
            "largest_face_ratio": 0.0,
            "fragmentation_score": 999.0,
            "watertight": False,
        }



def foho_save_native_obj_render(renderer, obj_mesh, moge_normal, save_path):
    """Save a native pipeline-view object render for selector visualization."""
    try:
        with torch.cuda.amp.autocast(enabled=False):
            rendered_normal, _ = render_normal_and_disparity(renderer, obj_mesh)
        plot_in_grid(rendered_normal, moge_normal, save_path=save_path)
        print(f"[FOHO_SELECTOR_RENDER] saved {save_path}")
    except Exception as e:
        print(f"[FOHO_SELECTOR_RENDER] failed to save {save_path}: {e}")


def foho_export_p3d_mesh(mesh, save_path):
    """Export a PyTorch3D Meshes object for selector/debug inspection."""
    try:
        import os
        import trimesh
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        verts = mesh.verts_packed().detach().cpu().numpy()
        faces = mesh.faces_packed().detach().cpu().numpy()
        trimesh.Trimesh(vertices=verts, faces=faces, process=False).export(save_path)
        print(f"[FOHO_SELECTOR_DEBUG] exported {save_path}")
    except Exception as e:
        print(f"[FOHO_SELECTOR_DEBUG] export failed for {save_path}: {e}")


def transform_hunyuan2moge(mesh, RT):
    ''' mesh is a pytorch3d mesh object '''
    # transform the mesh
    verts = mesh.verts_padded()
    verts = verts.squeeze(0)
    verts = verts @ RT[:3, :3].T + RT[:3, 3]
    verts = verts.unsqueeze(0)
    mesh = mesh.update_padded(verts)
    return mesh


def scale_mesh_around_bbox_center(mesh: Meshes, scale: float) -> Meshes:
    verts = mesh.verts_packed()
    
    # Compute AABB
    min_xyz = verts.min(dim=0).values
    max_xyz = verts.max(dim=0).values
    center = (min_xyz + max_xyz) / 2.0

    # Translate to origin, scale, then translate back
    verts_translated = verts - center
    verts_scaled = verts_translated * scale
    verts_final = verts_scaled + center

    # Recreate the mesh with scaled vertices
    new_mesh = Meshes(verts=[verts_final], faces=[mesh.faces_packed()])
    
    return new_mesh


def render_normal_and_disparity(renderer, mesh):
    norms = renderer(mesh) # .to('cpu')
    rendered_depth_map = renderer.rasterizer(mesh).zbuf.squeeze(-1)

    alpha = norms[..., 3]
    mask = alpha > 0.0
    normsneg = norms[..., :3]
    normalized_norms = (normsneg - normsneg.min()) / (normsneg.max() - normsneg.min() + 1e-6) # 6e-5 or 1e-6 added for numerical stability
    normalized_norms[~mask] = 0.0
    # plti(normalized_norms)

    rendered_depth_map[rendered_depth_map<0] = 10
    rendered_disparity_map = 1 / (rendered_depth_map + 1e-6) # Depth to disparity
    rendered_disparity_map = (rendered_disparity_map - rendered_disparity_map.min()) / (rendered_disparity_map.max() - rendered_disparity_map.min() + 1e-6) # Normalize disparity

    # rendered_disparity_map[rendered_disparity_map == 0] = 100.0
    
    return normalized_norms, rendered_disparity_map


def latent2sdf(pred, xyz_samples, grid_size, vae, device, return_mesh=False, save_name='default'):
    # Scale acc to Hunyuan
    pred = 1 / vae.scale_factor * pred
    pred = vae(pred)

    # Decode to SDF by querying the latent space
    batch_logits = []
    batch_size = 1
    num_chunks = 8000
    for start in range(0, xyz_samples.shape[0], num_chunks):
        queries = xyz_samples[start: start + num_chunks, :].to(device)
        queries = queries.half()
        batch_queries = queries.unsqueeze(0)
        logits = vae.geo_decoder(batch_queries.to(device), pred)
        batch_logits.append(logits)
        del queries
    grid_logits = torch.cat(batch_logits, dim=1)
    grid_logits = grid_logits.view((batch_size, grid_size[0], grid_size[1], grid_size[2])).float()

    # NOTE: making the SDF negative, some other codes might need fixing after this, like opt_latents and scale_hamer
    grid_logits = -grid_logits
    del batch_queries

    if return_mesh:
        vertices, faces, normals, _ = measure.marching_cubes(
                        grid_logits[0].cpu().numpy(),
                        0,
                        method="lewiner"
                    )

        bounds = 1.10
        bounds = [-bounds, -bounds, -bounds, bounds, bounds, bounds]
        bbox_min = np.array(bounds[0:3])
        bbox_max = np.array(bounds[3:6])
        bbox_size = bbox_max - bbox_min
        vertices = vertices / grid_size * bbox_size + bbox_min

        mesh_f = np.ascontiguousarray(faces)#[:, ::-1] # NOTE: this is not needed if sdf has conventional sign
        mesh_v = vertices.astype(np.float32)
        mesh_output = trimesh.Trimesh(mesh_v, mesh_f)
        debug_root = os.environ.get("FOHO_DEBUG_DIR")
        if debug_root:
            os.makedirs(debug_root, exist_ok=True)
            mesh_output.export(os.path.join(debug_root, f"Guidance_{save_name}.ply"))
        return mesh_output

    return grid_logits


def generate_dense_grid_points(bbox_min: np.ndarray,
                               bbox_max: np.ndarray,
                               octree_depth: int,
                               indexing: str = "ij",
                               octree_resolution: int = None,
                               ):
    length = bbox_max - bbox_min
    num_cells = np.exp2(octree_depth)
    if octree_resolution is not None:
        num_cells = octree_resolution

    x = np.linspace(bbox_min[0], bbox_max[0], int(num_cells) + 1, dtype=np.float32)
    y = np.linspace(bbox_min[1], bbox_max[1], int(num_cells) + 1, dtype=np.float32)
    z = np.linspace(bbox_min[2], bbox_max[2], int(num_cells) + 1, dtype=np.float32)
    [xs, ys, zs] = np.meshgrid(x, y, z, indexing=indexing)
    xyz = np.stack((xs, ys, zs), axis=-1)
    xyz = xyz.reshape(-1, 3)
    grid_size = [int(num_cells) + 1, int(num_cells) + 1, int(num_cells) + 1]

    return xyz, grid_size, length


def retrieve_timesteps(
    scheduler,
    num_inference_steps: Optional[int] = None,
    device: Optional[Union[str, torch.device]] = None,
    timesteps: Optional[List[int]] = None,
    sigmas: Optional[List[float]] = None,
    **kwargs,
    ):
    """
    Calls the scheduler's `set_timesteps` method and retrieves timesteps from the scheduler after the call. Handles
    custom timesteps. Any kwargs will be supplied to `scheduler.set_timesteps`.

    Args:
        scheduler (`SchedulerMixin`):
            The scheduler to get timesteps from.
        num_inference_steps (`int`):
            The number of diffusion steps used when generating samples with a pre-trained model. If used, `timesteps`
            must be `None`.
        device (`str` or `torch.device`, *optional*):
            The device to which the timesteps should be moved to. If `None`, the timesteps are not moved.
        timesteps (`List[int]`, *optional*):
            Custom timesteps used to override the timestep spacing strategy of the scheduler. If `timesteps` is passed,
            `num_inference_steps` and `sigmas` must be `None`.
        sigmas (`List[float]`, *optional*):
            Custom sigmas used to override the timestep spacing strategy of the scheduler. If `sigmas` is passed,
            `num_inference_steps` and `timesteps` must be `None`.

    Returns:
        `Tuple[torch.Tensor, int]`: A tuple where the first element is the timestep schedule from the scheduler and the
        second element is the number of inference steps.
    """
    if timesteps is not None and sigmas is not None:
        raise ValueError("Only one of `timesteps` or `sigmas` can be passed. Please choose one to set custom values")
    if timesteps is not None:
        accepts_timesteps = "timesteps" in set(inspect.signature(scheduler.set_timesteps).parameters.keys())
        if not accepts_timesteps:
            raise ValueError(
                f"The current scheduler class {scheduler.__class__}'s `set_timesteps` does not support custom"
                f" timestep schedules. Please check whether you are using the correct scheduler."
            )
        scheduler.set_timesteps(timesteps=timesteps, device=device, **kwargs)
        timesteps = scheduler.timesteps
        num_inference_steps = len(timesteps)
    elif sigmas is not None:
        accept_sigmas = "sigmas" in set(inspect.signature(scheduler.set_timesteps).parameters.keys())
        if not accept_sigmas:
            raise ValueError(
                f"The current scheduler class {scheduler.__class__}'s `set_timesteps` does not support custom"
                f" sigmas schedules. Please check whether you are using the correct scheduler."
            )
        scheduler.set_timesteps(sigmas=sigmas, device=device, **kwargs)
        timesteps = scheduler.timesteps
        num_inference_steps = len(timesteps)
    else:
        scheduler.set_timesteps(num_inference_steps, device=device, **kwargs)
        timesteps = scheduler.timesteps
    return timesteps, num_inference_steps


def export_to_trimesh(mesh_output):
    if isinstance(mesh_output, list):
        outputs = []
        for mesh in mesh_output:
            if mesh is None:
                outputs.append(None)
            else:
                mesh.mesh_f = mesh.mesh_f[:, ::-1]
                mesh_output = trimesh.Trimesh(mesh.mesh_v, mesh.mesh_f)
                outputs.append(mesh_output)
        return outputs
    else:
        mesh_output.mesh_f = mesh_output.mesh_f[:, ::-1]
        mesh_output = trimesh.Trimesh(mesh_output.mesh_v, mesh_output.mesh_f)
        return mesh_output


def get_obj_from_str(string, reload=False):
    module, cls = string.rsplit(".", 1)
    if reload:
        module_imp = importlib.import_module(module)
        importlib.reload(module_imp)
    return getattr(importlib.import_module(module, package=None), cls)


def instantiate_from_config(config, **kwargs):
    if "target" not in config:
        raise KeyError("Expected key `target` to instantiate.")
    cls = get_obj_from_str(config["target"])
    params = config.get("params", dict())
    kwargs.update(params)
    instance = cls(**kwargs)
    return instance


class Hunyuan3DDiTPipeline:
    @classmethod
    def from_single_file(
        cls,
        ckpt_path,
        config_path,
        device='cuda',
        dtype=torch.float16,
        **kwargs,
    ):
        
        # load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # load ckpt
        if not os.path.exists(ckpt_path):
            raise FileNotFoundError(f"Model file {ckpt_path} not found")
        logger.info(f"Loading model from {ckpt_path}")

        if ckpt_path.endswith('.safetensors'):
            # parse safetensors
            import safetensors.torch
            safetensors_ckpt = safetensors.torch.load_file(ckpt_path, device='cpu')
            ckpt = {}
            for key, value in safetensors_ckpt.items():
                model_name = key.split('.')[0]
                new_key = key[len(model_name) + 1:]
                if model_name not in ckpt:
                    ckpt[model_name] = {}
                ckpt[model_name][new_key] = value
        else:
            ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=True)

        # load model
        model = instantiate_from_config(config['model'])
        model.load_state_dict(ckpt['model'])
        vae = instantiate_from_config(config['vae'])
        vae.load_state_dict(ckpt['vae'])
        conditioner = instantiate_from_config(config['conditioner'])
        if 'conditioner' in ckpt:
            conditioner.load_state_dict(ckpt['conditioner'])
        image_processor = instantiate_from_config(config['image_processor'])
        scheduler = instantiate_from_config(config['scheduler'])

        model_kwargs = dict(
            vae=vae,
            model=model,
            scheduler=scheduler,
            conditioner=conditioner,
            image_processor=image_processor,
            device=device,
            dtype=dtype,
        )
        model_kwargs.update(kwargs)

        return cls(
            **model_kwargs,
        )

    @classmethod
    def from_pretrained(
        cls,
        model_path,
        device='cuda',
        dtype=torch.float16,
        use_safetensors=None,
        variant=None,
        subfolder='hunyuan3d-dit-v2-0',
        **kwargs,
    ):
        original_model_path = model_path
        if not os.path.exists(model_path):
            # try local path
            base_dir = os.environ.get('HY3DGEN_MODELS', '~/.cache/hy3dgen')
            model_path = os.path.expanduser(os.path.join(base_dir, model_path, subfolder))
            if not os.path.exists(model_path):
                try:
                    import huggingface_hub
                    # download from huggingface
                    path = huggingface_hub.snapshot_download(repo_id=original_model_path)
                    model_path = os.path.join(path, subfolder)
                except ImportError:
                    logger.warning(
                        "You need to install HuggingFace Hub to load models from the hub."
                    )
                    raise RuntimeError(f"Model path {model_path} not found")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path {original_model_path} not found")

        extension = 'ckpt' if not use_safetensors else 'safetensors'
        variant = '' if variant is None else f'.{variant}'
        ckpt_name = f'model{variant}.{extension}'
        config_path = os.path.join(model_path, 'config.yaml')
        ckpt_path = os.path.join(model_path, ckpt_name)

        return cls.from_single_file(
            ckpt_path,
            config_path,
            device=device,
            dtype=dtype,
            use_safetensors=use_safetensors,
            variant=variant,
            **kwargs
        )

    def __init__(
        self,
        vae,
        model,
        scheduler,
        conditioner,
        image_processor,
        device='cuda',
        dtype=torch.float16,
        **kwargs
    ):
        self.vae = vae
        self.model = model
        self.scheduler = scheduler
        self.conditioner = conditioner

        self.image_processor = image_processor

        # NOTE (ayce): added object & hoi scheduler
        self.object_scheduler = copy.deepcopy(scheduler)
        self.hoi_scheduler = copy.deepcopy(scheduler)

        self.to(device, dtype)

    def to(self, device=None, dtype=None):
        if device is not None:
            self.device = torch.device(device)
            self.vae.to(device)
            self.model.to(device)
            self.conditioner.to(device)
        if dtype is not None:
            self.dtype = dtype
            self.vae.to(dtype=dtype)
            self.model.to(dtype=dtype)
            self.conditioner.to(dtype=dtype)

    def encode_cond(self, image, mask, do_classifier_free_guidance, dual_guidance, to_cpu=False):
        bsz = image.shape[0]
        
        cond = self.conditioner(image=image, mask=mask)

        # # addition for multi-view
        # bsz = 1

        if do_classifier_free_guidance:
            un_cond = self.conditioner.unconditional_embedding(bsz)

            if dual_guidance:
                un_cond_drop_main = copy.deepcopy(un_cond)
                un_cond_drop_main['additional'] = cond['additional']

                def cat_recursive(a, b, c):
                    if isinstance(a, torch.Tensor):
                        return torch.cat([a, b, c], dim=0).to(self.dtype)
                    out = {}
                    for k in a.keys():
                        out[k] = cat_recursive(a[k], b[k], c[k])
                    return out

                cond = cat_recursive(cond, un_cond_drop_main, un_cond)
            else:
                un_cond = self.conditioner.unconditional_embedding(bsz)

                def cat_recursive(a, b):
                    if isinstance(a, torch.Tensor):
                        return torch.cat([a, b], dim=0).to(self.dtype)
                    out = {}
                    for k in a.keys():
                        out[k] = cat_recursive(a[k], b[k])
                    return out

                cond = cat_recursive(cond, un_cond)

        if to_cpu:
            self.conditioner.to('cpu')
        return cond

    # NOTE: Added encoding multiview condition
    def encode_cond_mv(self, image, mask, do_classifier_free_guidance, dual_guidance):
        bsz = 1 # image.shape[0], NOTE: not supporting batch processing for now
        conds = []

        for img, mas in zip(image, mask):
            cond = self.conditioner(image=img.unsqueeze(0), mask=mas.unsqueeze(0))
            conds.append(cond['main'])
        
        cond['main'] = torch.cat(conds, dim=0)

        if do_classifier_free_guidance:
            un_cond = self.conditioner.unconditional_embedding(bsz)

            if dual_guidance:
                un_cond_drop_main = copy.deepcopy(un_cond)
                un_cond_drop_main['additional'] = cond['additional']

                def cat_recursive(a, b, c):
                    if isinstance(a, torch.Tensor):
                        return torch.cat([a, b, c], dim=0).to(self.dtype)
                    out = {}
                    for k in a.keys():
                        out[k] = cat_recursive(a[k], b[k], c[k])
                    return out

                cond = cat_recursive(cond, un_cond_drop_main, un_cond)
            else:
                un_cond = self.conditioner.unconditional_embedding(bsz)

                def cat_recursive(a, b):
                    if isinstance(a, torch.Tensor):
                        return torch.cat([a, b], dim=0).to(self.dtype)
                    out = {}
                    for k in a.keys():
                        out[k] = torch.cat([a[k], b[k]], dim=0).to(self.dtype)
                    return out

                cond = cat_recursive(cond, un_cond)
                
        return cond

    def prepare_extra_step_kwargs(self, generator, eta):
        # prepare extra kwargs for the scheduler step, since not all schedulers have the same signature
        # eta (η) is only used with the DDIMScheduler, it will be ignored for other schedulers.
        # eta corresponds to η in DDIM paper: https://arxiv.org/abs/2010.02502
        # and should be between [0, 1]

        accepts_eta = "eta" in set(inspect.signature(self.scheduler.step).parameters.keys())
        extra_step_kwargs = {}
        if accepts_eta:
            extra_step_kwargs["eta"] = eta

        # check if the scheduler accepts generator
        accepts_generator = "generator" in set(inspect.signature(self.scheduler.step).parameters.keys())
        if accepts_generator:
            extra_step_kwargs["generator"] = generator
        return extra_step_kwargs

    def prepare_latents(self, batch_size, dtype, device, generator, latents=None):
        shape = (batch_size, *self.vae.latent_shape)
        if isinstance(generator, list) and len(generator) != batch_size:
            raise ValueError(
                f"You have passed a list of generators of length {len(generator)}, but requested an effective batch"
                f" size of {batch_size}. Make sure the batch size matches the length of the generators."
            )

        if latents is None:
            latents = randn_tensor(shape, generator=generator, device=device, dtype=dtype)
        else:
            latents = latents.to(device)

        # scale the initial noise by the standard deviation required by the scheduler
        latents = latents * getattr(self.scheduler, 'init_noise_sigma', 1.0)
        return latents

    def prepare_image(self, image, hand_mask=None):
        if isinstance(image, str) and not os.path.exists(image):
            raise FileNotFoundError(f"Couldn't find image at path {image}")

        if not isinstance(image, list):
            image = [image]
        image_pts = []
        mask_pts = []
        
        for img in image:
            processed = self.image_processor(img, return_mask=True)
            if isinstance(processed, dict):
                image_pt = processed.get("image")
                mask_pt = processed.get("mask")
            else:
                image_pt, mask_pt = processed
            image_pts.append(image_pt)
            mask_pts.append(mask_pt)

        image_pts = torch.cat(image_pts, dim=0).to(self.device, dtype=self.dtype)
        if mask_pts[0] is not None:
            mask_pts = torch.cat(mask_pts, dim=0).to(self.device, dtype=self.dtype)
        else:
            mask_pts = None

        return image_pts, mask_pts

    def get_guidance_scale_embedding(self, w, embedding_dim=512, dtype=torch.float32):
        """
        See https://github.com/google-research/vdm/blob/dc27b98a554f65cdc654b800da5aa1846545d41b/model_vdm.py#L298

        Args:
            timesteps (`torch.Tensor`):
                generate embedding vectors at these timesteps
            embedding_dim (`int`, *optional*, defaults to 512):
                dimension of the embeddings to generate
            dtype:
                data type of the generated embeddings

        Returns:
            `torch.FloatTensor`: Embedding vectors with shape `(len(timesteps), embedding_dim)`
        """
        assert len(w.shape) == 1
        w = w * 1000.0

        half_dim = embedding_dim // 2
        emb = torch.log(torch.tensor(10000.0)) / (half_dim - 1)
        emb = torch.exp(torch.arange(half_dim, dtype=dtype) * -emb)
        emb = w.to(dtype)[:, None] * emb[None, :]
        emb = torch.cat([torch.sin(emb), torch.cos(emb)], dim=1)
        if embedding_dim % 2 == 1:  # zero pad
            emb = torch.nn.functional.pad(emb, (0, 1))
        assert emb.shape == (w.shape[0], embedding_dim)
        return emb

    @torch.no_grad()
    def __call__(
        self,
        image: Union[str, List[str], Image.Image] = None,
        num_inference_steps: int = 50,
        timesteps: List[int] = None,
        sigmas: List[float] = None,
        eta: float = 0.0,
        guidance_scale: float = 7.5,
        dual_guidance_scale: float = 10.5,
        dual_guidance: bool = True,
        generator=None,
        box_v=1.01,
        octree_resolution=384,
        mc_level=-1 / 512,
        num_chunks=8000,
        mc_algo='mc',
        output_type: Optional[str] = "trimesh",
        enable_pbar=True,
        **kwargs,
    ) -> List[List[trimesh.Trimesh]]:
        callback = kwargs.pop("callback", None)
        callback_steps = kwargs.pop("callback_steps", None)

        device = self.device
        dtype = self.dtype
        do_classifier_free_guidance = guidance_scale >= 0 and \
                                      getattr(self.model, 'guidance_cond_proj_dim', None) is None
        dual_guidance = dual_guidance_scale >= 0 and dual_guidance

        image, mask = self.prepare_image(image)
        
        cond = self.encode_cond(image=image,
                                mask=mask,
                                do_classifier_free_guidance=do_classifier_free_guidance,
                                dual_guidance=dual_guidance)
        batch_size = image.shape[0]

        t_dtype = torch.long
        timesteps, num_inference_steps = retrieve_timesteps(
            self.scheduler, num_inference_steps, device, timesteps, sigmas)

        latents = self.prepare_latents(batch_size, dtype, device, generator)
        extra_step_kwargs = self.prepare_extra_step_kwargs(generator, eta)

        guidance_cond = None
        if getattr(self.model, 'guidance_cond_proj_dim', None) is not None:
            print('Using lcm guidance scale')
            guidance_scale_tensor = torch.tensor(guidance_scale - 1).repeat(batch_size)
            guidance_cond = self.get_guidance_scale_embedding(
                guidance_scale_tensor, embedding_dim=self.model.guidance_cond_proj_dim
            ).to(device=device, dtype=latents.dtype)

        for i, t in enumerate(tqdm(timesteps, disable=not enable_pbar, desc="Diffusion Sampling:", leave=False)):
            # expand the latents if we are doing classifier free guidance
            if do_classifier_free_guidance:
                latent_model_input = torch.cat([latents] * (3 if dual_guidance else 2))
            else:
                latent_model_input = latents
            latent_model_input = self.scheduler.scale_model_input(latent_model_input, t)

            # predict the noise residual
            timestep_tensor = torch.tensor([t], dtype=t_dtype, device=device)
            timestep_tensor = timestep_tensor.expand(latent_model_input.shape[0])
            noise_pred = self.model(latent_model_input, timestep_tensor, cond, guidance_cond=guidance_cond)

            # no drop, drop clip, all drop
            if do_classifier_free_guidance:
                if dual_guidance:
                    noise_pred_clip, noise_pred_dino, noise_pred_uncond = noise_pred.chunk(3)
                    noise_pred = (
                        noise_pred_uncond
                        + guidance_scale * (noise_pred_clip - noise_pred_dino)
                        + dual_guidance_scale * (noise_pred_dino - noise_pred_uncond)
                    )
                else:
                    noise_pred_cond, noise_pred_uncond = noise_pred.chunk(2)
                    noise_pred = noise_pred_uncond + guidance_scale * (noise_pred_cond - noise_pred_uncond)

            # compute the previous noisy sample x_t -> x_t-1
            outputs = self.scheduler.step(noise_pred, t, latents, **extra_step_kwargs)
            latents = outputs.prev_sample

            if callback is not None and i % callback_steps == 0:
                step_idx = i // getattr(self.scheduler, "order", 1)
                callback(step_idx, t, outputs)

        return self._export(
            latents,
            output_type,
            box_v, mc_level, num_chunks, octree_resolution, mc_algo,
        )

    def _export(self, latents, output_type, box_v, mc_level, num_chunks, octree_resolution, mc_algo, transform_cam_pose=None):
        if not output_type == "latent":
            latents = 1. / self.vae.scale_factor * latents
            latents = self.vae(latents)
            if transform_cam_pose is not None:
                outputs = self.vae.latents2mesh(
                    latents,
                    bounds=box_v,
                    mc_level=mc_level,
                    num_chunks=num_chunks,
                    octree_resolution=octree_resolution,
                    mc_algo=mc_algo,
                    transform_cam_pose=transform_cam_pose,
                )
            else:
                outputs = self.vae.latents2mesh(
                    latents,
                    bounds=box_v,
                    mc_level=mc_level,
                    num_chunks=num_chunks,
                    octree_resolution=octree_resolution,
                    mc_algo=mc_algo,
                )
        else:
            outputs = latents

        if output_type == 'trimesh':
            outputs = export_to_trimesh(outputs)

        return outputs


class Hunyuan3DDiTFlowMatchingPipeline(Hunyuan3DDiTPipeline):

    @torch.no_grad()
    def __call__(
        self,
        image: Union[str, List[str], Image.Image] = None,
        num_inference_steps: int = 50,
        timesteps: List[int] = None,
        sigmas: List[float] = None,
        eta: float = 0.0,
        guidance_scale: float = 7.5,
        generator=None,
        box_v=1.01,
        octree_resolution=384,
        mc_level=0.0,
        mc_algo='mc',
        num_chunks=8000,
        output_type: Optional[str] = "trimesh",
        enable_pbar=True,
        transform_cam_pose=None,
        multi_view=False,
        mask_exists=False,
        **kwargs,
    ) -> List[List[trimesh.Trimesh]]:
        callback = kwargs.pop("callback", None)
        callback_steps = kwargs.pop("callback_steps", None)

        device = self.device
        dtype = self.dtype
        do_classifier_free_guidance = guidance_scale >= 0 and not (
            hasattr(self.model, 'guidance_embed') and
            self.model.guidance_embed is True
        )
        
        # if not mask_exists:
        #     image, mask = self.prepare_image(image)
        # else:
        image, mask = self.prepare_image(image)
        # breakpoint()
        
        cond = self.encode_cond(
            image=image,
            mask=mask,
            do_classifier_free_guidance=do_classifier_free_guidance,
            dual_guidance=False,
        )
        batch_size = image.shape[0]

        # 5. Prepare timesteps
        # NOTE: this is slightly different from common usage, we start from 0.
        sigmas = np.linspace(0, 1, num_inference_steps) if sigmas is None else sigmas
        timesteps, num_inference_steps = retrieve_timesteps(
            self.scheduler,
            num_inference_steps,
            device,
            sigmas=sigmas,
        )
        latents = self.prepare_latents(batch_size, dtype, device, generator)

        guidance = None
        
        if hasattr(self.model, 'guidance_embed') and \
            self.model.guidance_embed is True:
            guidance = torch.tensor([guidance_scale] * batch_size, device=device, dtype=dtype)
        
        for i, t in enumerate(tqdm(timesteps, disable=not enable_pbar, desc="Diffusion Sampling:")):
            # expand the latents if we are doing classifier free guidance
            if do_classifier_free_guidance:
                latent_model_input = torch.cat([latents] * 2)
            else:
                latent_model_input = latents

            # NOTE: we assume model get timesteps ranged from 0 to 1
            timestep = t.expand(latent_model_input.shape[0]).to(
                latents.dtype) / self.scheduler.config.num_train_timesteps
            # NOTE: model prediction type is epsilon -model predicts the noise-
            noise_pred = self.model(latent_model_input, timestep, cond, guidance=guidance)

            if do_classifier_free_guidance:
                noise_pred_cond, noise_pred_uncond = noise_pred.chunk(2)
                noise_pred = noise_pred_uncond + guidance_scale * (noise_pred_cond - noise_pred_uncond)

            # compute the previous noisy sample x_t -> x_t-1
            outputs = self.scheduler.step(noise_pred, t, latents)
            latents = outputs.prev_sample

            if callback is not None and i % callback_steps == 0:
                step_idx = i // getattr(self.scheduler, "order", 1)
                callback(step_idx, t, outputs)

        if transform_cam_pose is not None:
            return self._export(
                latents,
                output_type,
                box_v, mc_level, num_chunks, octree_resolution, mc_algo, 
                transform_cam_pose=transform_cam_pose,
            )

        return self._export(
            latents,
            output_type,
            box_v, mc_level, num_chunks, octree_resolution, mc_algo, 
        )


def compute_loss_stable_fp32(loss_terms: dict) -> torch.Tensor:
    """
    Compute final loss in float32 to avoid instability in backward.

    Args:
        loss_terms (dict): Dictionary of individual loss components (tensors).

    Returns:
        torch.Tensor: Summed final loss in float32.
    """
    total_loss_fp32 = torch.tensor(0.0, dtype=torch.float32, device=next(iter(loss_terms.values())).device)
    for name, loss_val in loss_terms.items():
        if loss_val is not None:
            if torch.isnan(loss_val).any():
                print(f"NaN detected in {name}, skipping...")
                continue
            total_loss_fp32 = total_loss_fp32 + loss_val.float()
    return total_loss_fp32


def visualize_w_white_bg(renderer, mesh):
    norms = renderer(mesh)

    alpha = norms[..., 3]
    mask = alpha > 0.0
    normsneg = norms[..., :3]

    # Normalize only foreground pixels
    normalized_norms = torch.zeros_like(normsneg)
    foreground = normsneg[mask]
    min_val = foreground.min()
    max_val = foreground.max()
    normalized_foreground = (foreground - min_val) / (max_val - min_val + 1e-6)
    normalized_norms[mask] = normalized_foreground

    # Set background to white
    normalized_norms[~mask] = 1.0
    return normalized_norms


class Hunyuan3DDiTFlowMatchingPipeline_main(Hunyuan3DDiTPipeline):

    @torch.no_grad()
    def __call__(
        self,
        image: Union[str, List[str], Image.Image] = None,
        num_inference_steps: int = 30,
        timesteps: List[int] = None,
        sigmas: List[float] = None,
        eta: float = 0.0,
        guidance_scale: float = 7.5,
        generator=None,
        box_v=1.10, 
        octree_resolution=64,
        mc_level=0.0,
        mc_algo='mc',
        num_chunks=8000,
        output_type: Optional[str] = "trimesh",
        enable_pbar=True,
        config=None,
        renderer=None,
        sil_renderer=None,
        cropped_obj_img_path=None,
        hamer_for_guid_path=None,
        aligned_mano_mesh_path=None,
        obj_mask_path=None,
        hand_mask_path=None,
        moge_mesh_path=None,
        h2m_rt_path=None,
        hunyuan_hoi_mesh_path=None,
        **kwargs,
    ) -> List[List[trimesh.Trimesh]]:
        callback = kwargs.pop("callback", None)
        callback_steps = kwargs.pop("callback_steps", None)

        debug_root = os.environ.get("FOHO_DEBUG_DIR")
        debugging = bool(debug_root)  # set FOHO_DEBUG_DIR to enable debug dumps

        # exp dir initialize
        index = cropped_obj_img_path.split('/')[-1].split('_')[0]
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        exp_dir = f"{timestamp}_exp_obj{index}_inpainted"
        if debugging:
            save_dir = os.path.join(debug_root, exp_dir)
            os.makedirs(save_dir, exist_ok=True)
            param_log_path = os.path.join(save_dir, "params.json")
            loss_log_path = os.path.join(save_dir, "losses.txt")
            loss_log_file = open(loss_log_path, "w")
        else:
            save_dir = None
            loss_log_file = None

        hand_mask_check = cv2.imread(hand_mask_path, cv2.IMREAD_GRAYSCALE)
        H, W = hand_mask_check.shape[:2]

        device = self.device
        dtype = self.dtype
        do_classifier_free_guidance = guidance_scale >= 0 and not (
            hasattr(self.model, 'guidance_embed') and
            self.model.guidance_embed is True
        )

        # Normalize image input to a single RGBA array before alpha extraction.
        img0 = image[0] if isinstance(image, (list, tuple)) else image
        if isinstance(img0, str):
            img0 = Image.open(img0)
        if isinstance(img0, Image.Image):
            img0 = img0.convert("RGBA")
        img0_np = np.array(img0)
        if img0_np.ndim == 3 and img0_np.shape[-1] >= 4:
            obj_alpha_ori = (img0_np[..., 3] > 0).astype(np.uint8)
        else:
            # Fallback: treat as fully-opaque if no alpha channel exists.
            obj_alpha_ori = np.ones(img0_np.shape[:2], dtype=np.uint8)
        obj_alpha_ori = torch.from_numpy(obj_alpha_ori).to(device).bool().unsqueeze(2).unsqueeze(0) # 1XHXWX1
        obj_img, obj_mask = self.prepare_image(image)

        cond_obj = self.encode_cond(
            image=obj_img,
            mask=obj_mask,
            do_classifier_free_guidance=do_classifier_free_guidance,
            dual_guidance=False,
        )

        # sample dense grid points to be used for latent decoding to sdf
        octree_res = 64
        bounds = 1.10
        bounds = [-bounds, -bounds, -bounds, bounds, bounds, bounds]
        bbox_min = np.array(bounds[0:3])
        bbox_max = np.array(bounds[3:6])
        bbox_size = bbox_max - bbox_min
        xyz_samples, grid_size, length = generate_dense_grid_points(
            bbox_min=bbox_min,
            bbox_max=bbox_max,
            octree_depth=5,
            octree_resolution=octree_res,
            indexing="ij")
        xyz_samples = torch.FloatTensor(xyz_samples)
        xyz_samples = xyz_samples.to(device)
        
        # setup Kaolin voxel grid
        flexi = knc.FlexiCubes(device=device)
        voxel_vertices, cube_indices = flexi.construct_voxel_grid(octree_res)

        obj_guidance_scale = config().obj_guidance_scale
        batch_size = config().batch_size # NOTE: not supporting batch processing for now
        optimization_steps_hand = config().optimization_steps_hand
        optimization_steps_joint = config().optimization_steps_joint
        optimization_steps_scale = config().optimization_steps_scale
        num_inference_steps = config().num_inference_steps
        guidance_start_step = config().guidance_start_step
        handopt_start_step = int(
            os.environ.get(
                "FOHO_HANDOPT_START_STEP",
                str(config().handopt_start_step),
            )
        )
        guidance_end_step = num_inference_steps

        # initialize optimization learning rates
        phase1_hand_lrs = config().phase1_hand_lrs
        phase2_hand_lrs = config().phase2_hand_lrs
        obj_lrs = config().obj_lrs
        obj_2half_lrs = config().obj_2half_lrs
        noise_obj_lr1 = config().noise_obj_lr1
        noise_obj_lr2 = config().noise_obj_lr2
        print(f"[FOHO_DEBUG] noise_obj_lr1={noise_obj_lr1}, noise_obj_lr2={noise_obj_lr2}")
        use_intersection_loss = config().use_intersection_loss

        params_to_save = {
            'obj_guidance_scale': obj_guidance_scale,
            'optimization_steps_hand': optimization_steps_hand,
            'optimization_steps_joint': optimization_steps_joint,
            'optimization_steps_scale': optimization_steps_scale,
            'num_inference_steps': num_inference_steps,
            'guidance_start_step': guidance_start_step,
            'handopt_start_step': handopt_start_step,
            'guidance_end_step': guidance_end_step,
            'phase1_hand_lrs': phase1_hand_lrs,
            'phase2_hand_lrs': phase2_hand_lrs,
            'obj_lrs': obj_lrs,
            'obj_2half_lrs': obj_2half_lrs,
            'noise_obj_lr1': noise_obj_lr1,
            'noise_obj_lr2': noise_obj_lr2,
            'use_intersection_loss': use_intersection_loss,
            } 
        if debugging:
            with open(param_log_path, "w") as f:
                json.dump(params_to_save, f, indent=4)

        # 5. Prepare timesteps
        # NOTE: this is slightly different from common usage, we start from 0.
        sigmas = np.linspace(0, 1, num_inference_steps) if sigmas is None else sigmas
        timesteps_obj, num_inference_steps_obj = retrieve_timesteps(
            self.scheduler,
            num_inference_steps,
            device,
            sigmas=sigmas,
        )
        
        guidance = None
        if hasattr(self.model, 'guidance_embed') and \
            self.model.guidance_embed is True:
            guidance = torch.tensor([guidance_scale] * batch_size, device=device, dtype=dtype)
        
        torch.cuda.empty_cache()
        self.model.eval()
        self.vae.eval()

        latents = self.prepare_latents(batch_size, dtype, device, generator)
        obj_latents = latents.clone()
        
        # initialize hunyuan hand transformation params
        scale_hand = torch.tensor([1.0], device=device)

        # FOHO_GATE_A_FIXED_OBJECT_PRELOAD -- load ONCE, unconditionally,
        # before either optimization phase, so the cache exists regardless
        # of whether optimization_steps_scale (FOHO_OPT_STEPS_SCALE) is 0.
        _foho_fixed_obj_ply_preload = os.environ.get("FOHO_GATE_A_FIXED_OBJECT_PLY", "")
        _foho_fixed_obj_mesh_cached = None
        if _foho_fixed_obj_ply_preload:
            from pytorch3d.io import IO as _FOHO_LOAD_IO
            _foho_fixed_obj_mesh_cached = _FOHO_LOAD_IO().load_mesh(_foho_fixed_obj_ply_preload, device=device)
            print(f"[FOHO_GATE_A_FIXED_OBJECT] preloaded frozen Gate A mesh from "
                  f"{_foho_fixed_obj_ply_preload}, verts={_foho_fixed_obj_mesh_cached.verts_packed().shape[0]}")
        # FOHO_F2_SCREEN_LID_TARGET_PRELOAD
        _foho_f2_target_ply = os.environ.get(
            "FOHO_GATE_C_SCREEN_LID_TARGET", ""
        )
        _foho_f2_weight = float(
            os.environ.get("FOHO_F2_SCREEN_LID_CONTACT_WEIGHT", "0.0")
        )
        _foho_f2_hand_patch_size = int(
            os.environ.get("FOHO_F2_HAND_PATCH_SIZE", "64")
        )
        _foho_f2_target_distance_m = float(
            os.environ.get("FOHO_F2_TARGET_DISTANCE_M", "0.003")
        )
        _foho_f2_huber_beta_m = float(
            os.environ.get("FOHO_F2_HUBER_BETA_M", "0.010")
        )
        _foho_f2_match_tolerance_m = float(
            os.environ.get("FOHO_F2_TARGET_MATCH_TOL_M", "0.0001")
        )

        _foho_f2_target_obj_idx = None
        _foho_f2_hand_patch_idx = None

        if _foho_f2_target_ply and _foho_f2_weight > 0.0:
            if _foho_fixed_obj_mesh_cached is None:
                raise RuntimeError(
                    "F2 requires FOHO_GATE_A_FIXED_OBJECT_PLY."
                )
            if not os.path.isfile(_foho_f2_target_ply):
                raise FileNotFoundError(
                    f"Gate-C target not found: {_foho_f2_target_ply}"
                )

            from pytorch3d.io import IO as _FOHO_F2_IO

            _foho_f2_target_mesh_cached = _FOHO_F2_IO().load_mesh(
                _foho_f2_target_ply,
                device=device,
            )

            # The target is a canonical subset of the fixed Gate-A object.
            # Map every target vertex to its corresponding full-object vertex.
            # Later we extract these indices from transformed_obj_mesh, which
            # guarantees exactly the same object transform and rotation center.
            with torch.no_grad():
                _foho_f2_match_d2, _foho_f2_match_idx, _ = knn_points(
                    _foho_f2_target_mesh_cached.verts_padded(),
                    _foho_fixed_obj_mesh_cached.verts_padded(),
                    K=1,
                )
                _foho_f2_max_match_m = torch.sqrt(
                    torch.clamp(_foho_f2_match_d2.max(), min=0.0)
                ).item()

                if _foho_f2_max_match_m > _foho_f2_match_tolerance_m:
                    raise RuntimeError(
                        "Gate-C target is not an exact-enough subset of the "
                        f"fixed object: max match={_foho_f2_max_match_m:.8f} m, "
                        f"tolerance={_foho_f2_match_tolerance_m:.8f} m"
                    )

                _foho_f2_target_obj_idx = (
                    _foho_f2_match_idx[0, :, 0].long()
                )

            print(
                "[FOHO_F2] preloaded Gate-C screen/lid target; "
                f"target_verts={len(_foho_f2_target_obj_idx)}, "
                f"max_match_m={_foho_f2_max_match_m:.8f}, "
                f"weight={_foho_f2_weight}, "
                f"hand_patch_size={_foho_f2_hand_patch_size}, "
                f"target_distance_m={_foho_f2_target_distance_m}"
            )

        # FOHO_F3_STAGE1_BEGIN
        # FOHO_F3_LOAD_CONTACT_SPEC
        _foho_f3_enabled = (
            os.environ.get("FOHO_F3_STAGE1", "0") == "1"
        )
        _foho_f3_preflight_only = (
            os.environ.get("FOHO_F3_PREFLIGHT_ONLY", "0") == "1"
        )
        _foho_f3_root = os.environ.get("FOHO_F3_ROOT", "")
        _foho_f3_translation_lr = float(
            os.environ.get("FOHO_F3_TRANSLATION_LR", "0.002")
        )
        _foho_f3_steps = int(
            os.environ.get("FOHO_F3_STEPS", "10")
        )
        _foho_f3_contact_weight = float(
            os.environ.get("FOHO_F3_CONTACT_WEIGHT", "10.0")
        )
        _foho_f3_2d_weight = float(
            os.environ.get("FOHO_F3_2D_KPS_WEIGHT", "0.0001")
        )
        _foho_f3_trans_reg_weight = float(
            os.environ.get("FOHO_F3_TRANS_REG_WEIGHT", "0.01")
        )
        _foho_f3_target_distance_m = float(
            os.environ.get("FOHO_F3_TARGET_DISTANCE_M", "0.003")
        )
        _foho_f3_huber_beta_m = float(
            os.environ.get("FOHO_F3_HUBER_BETA_M", "0.010")
        )
        _foho_f3_max_translation_delta_m = float(
            os.environ.get(
                "FOHO_F3_MAX_TRANSLATION_DELTA_M", "0.060"
            )
        )
        _foho_f3_match_tolerance_m = float(
            os.environ.get("FOHO_F3_TARGET_MATCH_TOL_M", "0.0001")
        )
        _foho_f3_log_every = max(
            1, int(os.environ.get("FOHO_F3_LOG_EVERY", "5"))
        )

        _foho_f3_target_obj_idx = None
        _foho_f3_tip_idx = None
        _foho_f3_trans_hand_anchor = None

        # FOHO_F3_1_STAGE1_BEGIN
        _foho_f31_enabled = (
            os.environ.get("FOHO_F3_1_STAGE1", "0") == "1"
        )
        if _foho_f31_enabled and _foho_f3_enabled:
            raise RuntimeError(
                "FOHO_F3_STAGE1 and FOHO_F3_1_STAGE1 are mutually exclusive"
            )
        if _foho_f31_enabled:
            _foho_f3_enabled = True
            _foho_f3_preflight_only = (
                os.environ.get("FOHO_F3_1_PREFLIGHT_ONLY", "0") == "1"
            )
            _foho_f3_root = os.environ.get("FOHO_F3_1_ROOT", "")
            _foho_f3_translation_lr = float(
                os.environ.get(
                    "FOHO_F3_1_TRANSLATION_LR", _foho_f3_translation_lr
                )
            )
            _foho_f3_steps = int(
                os.environ.get("FOHO_F3_1_STEPS", _foho_f3_steps)
            )
            _foho_f31_rotation_lr = float(
                os.environ.get("FOHO_F3_1_ROTATION_LR", "0.001")
            )
            _foho_f31_max_rotation_rad = float(
                os.environ.get("FOHO_F3_1_MAX_ROTATION_DELTA_DEG", "10")
            ) * torch.pi / 180.0
        else:
            _foho_f31_rotation_lr = None
            _foho_f31_max_rotation_rad = None
        _foho_f31_rotation_delta_hand = None

        # FOHO_F3_2_CONTACT_COLLISION_V2_BEGIN
        # F3.2 reuses the verified F3.1 local-contact assets and bounded
        # hand-only parameterization, but adds a collision cleanup term.
        _foho_f32_enabled = (
            os.environ.get("FOHO_F3_2_STAGE1", "0") == "1"
        )
        if _foho_f32_enabled:
            if (
                os.environ.get("FOHO_F3_STAGE1", "0") == "1"
                or os.environ.get("FOHO_F3_1_STAGE1", "0") == "1"
            ):
                raise RuntimeError(
                    "FOHO_F3_2_STAGE1 is mutually exclusive with F3/F3.1."
                )

            # Internally reuse the F3.1 two-trainable implementation:
            # hand translation + bounded hand rotation delta.
            _foho_f31_enabled = True
            _foho_f3_enabled = True
            _foho_f3_preflight_only = (
                os.environ.get("FOHO_F3_2_PREFLIGHT_ONLY", "0") == "1"
            )
            _foho_f3_root = os.environ.get("FOHO_F3_2_ROOT", "")
            _foho_f3_translation_lr = float(
                os.environ.get(
                    "FOHO_F3_2_TRANSLATION_LR",
                    os.environ.get("FOHO_F3_1_TRANSLATION_LR", _foho_f3_translation_lr),
                )
            )
            _foho_f3_steps = int(
                os.environ.get(
                    "FOHO_F3_2_STEPS",
                    os.environ.get("FOHO_F3_1_STEPS", _foho_f3_steps),
                )
            )
            _foho_f31_rotation_lr = float(
                os.environ.get(
                    "FOHO_F3_2_ROTATION_LR",
                    os.environ.get("FOHO_F3_1_ROTATION_LR", "0.001"),
                )
            )
            _foho_f31_max_rotation_rad = (
                float(
                    os.environ.get(
                        "FOHO_F3_2_MAX_ROTATION_DELTA_DEG",
                        os.environ.get("FOHO_F3_1_MAX_ROTATION_DELTA_DEG", "10"),
                    )
                )
                * torch.pi
                / 180.0
            )

        _foho_f32_stage_a_steps = int(
            os.environ.get("FOHO_F3_2_STAGE_A_STEPS", "5")
        )
        _foho_f32_collision_weight = float(
            os.environ.get("FOHO_F3_2_COLLISION_WEIGHT", "50.0")
        )
        _foho_f32_anchor_trans_weight = float(
            os.environ.get("FOHO_F3_2_ANCHOR_TRANS_WEIGHT", "5.0")
        )
        _foho_f32_anchor_rot_weight = float(
            os.environ.get("FOHO_F3_2_ANCHOR_ROT_WEIGHT", "5.0")
        )
        _foho_f32_contact_preserve_weight = float(
            os.environ.get(
                "FOHO_F3_2_CONTACT_PRESERVE_WEIGHT",
                str(_foho_f3_contact_weight),
            )
        )
        _foho_f32_mask_refresh = max(
            1, int(os.environ.get("FOHO_F3_2_MASK_REFRESH", "1"))
        )
        _foho_f32_stage_a_trans_hand = None
        _foho_f32_stage_a_rotation_delta_hand = None
        _foho_f32_collision_mask = None

        # FOHO_F3_3_ESCAPE_SEED_V2_BEGIN
        _foho_f33_enabled = _foho_f32_enabled and os.environ.get("FOHO_F3_3_ENABLE", "0") == "1"
        _foho_f33_escape_z_m = float(os.environ.get("FOHO_F3_3_ESCAPE_Z_M", "0.0"))
        _foho_f33_escape_applied = False
        if _foho_f33_enabled:
            print("[FOHO_F3_3_RUNTIME_CONTRACT] " f"escape_z_m={_foho_f33_escape_z_m:.6f}")
        # FOHO_F3_3_ESCAPE_SEED_V2_END
        # FOHO_F3_2_CONTACT_COLLISION_V2_END

        # FOHO_F3_1_STAGE1_END

        if _foho_f3_enabled:
            import json as _foho_f3_json
            import numpy as _foho_f3_np
            from pytorch3d.io import IO as _FOHO_F3_IO

            if _foho_fixed_obj_mesh_cached is None:
                raise RuntimeError(
                    "F3 requires FOHO_GATE_A_FIXED_OBJECT_PLY."
                )
            if not _foho_f3_root:
                raise RuntimeError("F3 requires FOHO_F3_ROOT.")

            _foho_f3_spec_name = (
                "F3_1_contact_spec.json"
                if _foho_f31_enabled else "F3_contact_spec.json"
            )
            _foho_f3_ids_name = (
                "F3_1_local_lid_target_vertex_ids.npy"
                if _foho_f31_enabled else "F3_local_lid_target_vertex_ids.npy"
            )
            _foho_f3_spec_path = os.path.join(
                _foho_f3_root, "inputs", _foho_f3_spec_name
            )
            _foho_f3_ids_path = os.path.join(
                _foho_f3_root, "inputs", _foho_f3_ids_name
            )
            _foho_f3_lid_ply = (
                os.environ.get("FOHO_F3_CANONICAL_LID_PLY", "")
                or os.environ.get(
                    "FOHO_GATE_C_SCREEN_LID_TARGET", ""
                )
            )

            for _foho_f3_required in (
                _foho_f3_spec_path,
                _foho_f3_ids_path,
                _foho_f3_lid_ply,
            ):
                if not os.path.isfile(_foho_f3_required):
                    raise FileNotFoundError(
                        f"F3 required input missing: "
                        f"{_foho_f3_required}"
                    )

            with open(
                _foho_f3_spec_path, "r", encoding="utf-8"
            ) as _foho_f3_file:
                _foho_f3_spec = _foho_f3_json.load(
                    _foho_f3_file
                )

            if (
                _foho_f3_spec.get("target_spec_status")
                != "PASS_CANONICAL_LOCAL_TARGET"
                or not _foho_f3_spec.get(
                    "target_approved_geometrically", False
                )
            ):
                raise RuntimeError(
                    "F3 target has not passed the canonical "
                    "local-target audit."
                )

            if (
                not _foho_f3_preflight_only
                and not _foho_f3_spec.get(
                    "approved_for_f3_stage1", False
                )
            ):
                raise RuntimeError(
                    "F3 execution is not authorized in "
                    "F3_contact_spec.json."
                )

            _foho_f3_tip_ids = _foho_f3_spec.get(
                "primary_mano_tip_vertex_ids",
                _foho_f3_spec.get("mano_tip_vertex_ids", []),
            )
            if not _foho_f3_tip_ids:
                raise RuntimeError(
                    "F3 primary fingertip IDs are missing."
                )
            if any(
                int(_idx) < 0 or int(_idx) >= 778
                for _idx in _foho_f3_tip_ids
            ):
                raise RuntimeError(
                    "F3 fingertip IDs are outside MANO-778 space."
                )

            # FOHO_F3_LOAD_LOCAL_TARGET_IDS
            _foho_f3_local_ids_np = (
                _foho_f3_np.load(_foho_f3_ids_path)
                .astype(_foho_f3_np.int64)
                .reshape(-1)
            )
            if _foho_f3_local_ids_np.size < 4:
                raise RuntimeError(
                    "F3 local target contains fewer than four vertices."
                )

            _foho_f3_lid_mesh = (
                _FOHO_F3_IO()
                .load_mesh(_foho_f3_lid_ply, device=device)
            )
            _foho_f3_lid_vertices = (
                _foho_f3_lid_mesh.verts_packed()
            )
            if (
                _foho_f3_local_ids_np.min() < 0
                or _foho_f3_local_ids_np.max()
                >= _foho_f3_lid_vertices.shape[0]
            ):
                raise RuntimeError(
                    "F3 target IDs are outside the canonical "
                    "lid vertex range."
                )

            _foho_f3_local_ids = torch.as_tensor(
                _foho_f3_local_ids_np,
                dtype=torch.long,
                device=device,
            )
            _foho_f3_selected_lid = (
                _foho_f3_lid_vertices[_foho_f3_local_ids]
                .unsqueeze(0)
            )

            # Map lid-local IDs into the frozen full Gate-A object.
            with torch.no_grad():
                (
                    _foho_f3_match_d2,
                    _foho_f3_match_idx,
                    _,
                ) = knn_points(
                    _foho_f3_selected_lid,
                    _foho_fixed_obj_mesh_cached.verts_padded(),
                    K=1,
                )
                _foho_f3_max_match_m = torch.sqrt(
                    torch.clamp(
                        _foho_f3_match_d2.max(), min=0.0
                    )
                ).item()
                if (
                    _foho_f3_max_match_m
                    > _foho_f3_match_tolerance_m
                ):
                    raise RuntimeError(
                        "F3 target is not an exact-enough subset "
                        "of the fixed object: "
                        f"{_foho_f3_max_match_m:.8f} m"
                    )
                _foho_f3_target_obj_idx = (
                    _foho_f3_match_idx[0, :, 0].long()
                )

            _foho_f3_tip_idx = torch.as_tensor(
                [int(_idx) for _idx in _foho_f3_tip_ids],
                dtype=torch.long,
                device=device,
            )
            print(
                "[FOHO_F3_LOAD_CONTACT_SPEC] "
                f"tips={_foho_f3_tip_ids}, "
                f"target_vertices="
                f"{len(_foho_f3_target_obj_idx)}, "
                f"max_match_m={_foho_f3_max_match_m:.8f}, "
                f"preflight_only={_foho_f3_preflight_only}"
            )
        trans_hand = torch.tensor([0.0, 0.0, 0.0], device=device)
        rotation_hand = torch.tensor([1.0, 0.0, 0.0, 0.0], device=device) # quaternion wxyz

        # initialize obj transformation params
        scale_obj = torch.tensor([1.0], device=device)
        trans_obj = torch.tensor([0.0, 0.0, 0.0], device=device)
        rotation_obj = torch.tensor([1.0, 0.0, 0.0, 0.0], device=device) # quaternion wxyz

        # FOHO_INTERNAL_PHASE42_SELECTOR_STATE_PATCH
        # Store object states so an internal selector can choose which state enters joint alignment.
        foho_obj_state_before_phase42 = None
        foho_phase42_selector_applied = False
        foho_obj_mesh_before_phase42 = None
        foho_obj_mesh_phase42_before_joint = None

        # load mano keypoint stuff obtained from modified HaMeR demo
        J_regressor = torch.load('./third_party/estimator/hamer/J_regressor_hamer.pt')
        hamer4guid = np.load(hamer_for_guid_path, allow_pickle=True).item()
        hamer_2d_kps = hamer4guid['mano_2d_kps'] # in input image space

        # load aligned mano mesh (aligned to hunyuan), NOTE: it is not perfectly aligned. 
        mano_verts, mano_faces = load_ply(aligned_mano_mesh_path)
        tex_hand = torch.zeros_like(mano_verts) # add texture to the hand mesh for silhoutte loss
        tex_hand[:, 1] = 1.0 # green
        tex_hand = TexturesVertex(verts_features=[tex_hand])
        mano_mesh = Meshes(verts=[mano_verts], faces=[mano_faces], textures=tex_hand).to(device)        

        # load moge hand mask
        moge_hand_mask = cv2.imread(hand_mask_path, cv2.IMREAD_GRAYSCALE)
        moge_hand_mask = torch.tensor(moge_hand_mask, device=device).float().unsqueeze(0) # (1, h, w)
        moge_hand_mask = (moge_hand_mask > 0).bool() # convert to bool

        # load obj mask (moge masks and img masks are the same since moge is image space aligned)
        moge_obj_mask = cv2.imread(obj_mask_path, cv2.IMREAD_GRAYSCALE)
        moge_obj_mask = torch.tensor(moge_obj_mask, device=device).float().unsqueeze(0) # (1, h, w)
        moge_obj_mask = (moge_obj_mask > 0).bool() # convert to bool

        # load hunyuan space to moge scene space transformation obtained from icp
        T_h2m = torch.tensor(np.load(h2m_rt_path), dtype=torch.float32, device=device)
        mano_mesh_moge = transform_hunyuan2moge(mano_mesh, T_h2m)
        # FOHO_EXTERNAL_S100_UP_SEAM_V99_11_7_13_3_13_4_1_BEGIN
        import os as _foho_os
        _foho_external_anchor_active = bool(_foho_os.environ.get("FOHO_EXTERNAL_HAND_ANCHOR_MODE", "").strip())
        if _foho_external_anchor_active:
            if _foho_os.environ.get("FOHO_EXTERNAL_HAND_ANCHOR_MODE", "").strip() != "object_only":
                raise RuntimeError("external hand anchor currently authorizes object_only mode")
            optimization_steps_joint = 0
            import importlib.util as _foho_importlib_util
            _foho_helper_path = _foho_os.environ["FOHO_EXTERNAL_HAND_RUNTIME_HELPER"]
            _foho_helper_spec = _foho_importlib_util.spec_from_file_location("foho_external_hand_runtime", _foho_helper_path)
            if _foho_helper_spec is None or _foho_helper_spec.loader is None:
                raise RuntimeError(f"cannot load external hand runtime helper: {_foho_helper_path}")
            _foho_helper = _foho_importlib_util.module_from_spec(_foho_helper_spec)
            _foho_helper_spec.loader.exec_module(_foho_helper)
            transformed_hand_mesh, _foho_anchor_state = _foho_helper.activate_external_anchor(
                torch_module=torch,
                device=device,
                mano_mesh_moge=mano_mesh_moge,
                scale_hand=scale_hand,
                trans_hand=trans_hand,
                rotation_hand=rotation_hand,
                quaternion_to_matrix=quaternion_to_matrix,
                transform_mesh_around_center_w_scale=transform_mesh_around_center_w_scale,
            )

        moge_hoi_mask = moge_hand_mask | moge_obj_mask # combine hand and object masks
        moge_sil = moge_hoi_mask 
        moge_hand_sil = moge_hand_mask
        
        from pytorch3d.io.experimental_gltf_io import _read_header, MeshGlbFormat
        io = IO()
        io.register_meshes_format(MeshGlbFormat())
        moge_mesh = io.load_mesh(moge_mesh_path).to(device)
        with torch.cuda.amp.autocast(enabled=False):
            moge_normal, moge_disp = render_normal_and_disparity(renderer, moge_mesh)
        moge_normal = moge_normal[0] * moge_hoi_mask.float()[0][..., None] # apply mask to normal map
        moge_disp = moge_disp[0][..., None] * moge_hoi_mask.float()[0][..., None] # apply mask to depth map
        moge_normal = moge_normal.unsqueeze(0)
        moge_disp = moge_disp.unsqueeze(0).squeeze(-1)
        
        # make obj_alpha_ori same size as moge_hoi_mask
        obj_alpha_ori = obj_alpha_ori.unsqueeze(0).squeeze(-1) # (1,1,H, W)
        mask_shape = moge_obj_mask.shape[1]
        obj_alpha_ori = F.interpolate(
            obj_alpha_ori.float(),
            size=(mask_shape,mask_shape),
            mode='nearest'

        ).to(device).bool()
        obj_alpha_ori = obj_alpha_ori.squeeze(0).unsqueeze(-1) # (1, H, W, 1)

        for i, t in enumerate(tqdm(timesteps_obj, disable=not enable_pbar, desc="Diffusion Sampling:")):
            # expand the latents if we are doing classifier free guidance
            if do_classifier_free_guidance:
                latent_model_input_obj = torch.cat([obj_latents] * 2)
            else:
                latent_model_input_obj = obj_latents

            # NOTE: we assume model get timesteps ranged from 0 to 1
            timestep_obj = t.expand(latent_model_input_obj.shape[0]).to(
                obj_latents.dtype) / self.scheduler.config.num_train_timesteps
            
            noise_pred_obj = self.model(latent_model_input_obj, timestep_obj, cond_obj, guidance=guidance)

            if do_classifier_free_guidance:
                # rely more on learned prior early on, then gradually trust guidance as it denoises
                if i >= guidance_start_step + 1:
                    obj_guidance_scale_upt = obj_guidance_scale * (1 - i / num_inference_steps_obj)
                else:
                    obj_guidance_scale_upt = obj_guidance_scale
                # obj_guidance_scale_upt = obj_guidance_scale

                noise_pred_obj_cond, noise_pred_obj_uncond = noise_pred_obj.chunk(2)
                noise_pred_obj = noise_pred_obj_uncond + obj_guidance_scale_upt * (noise_pred_obj_cond - noise_pred_obj_uncond) # obj_guidance_scale
            
            if i >= handopt_start_step:
                with torch.enable_grad():
                    if _foho_f3_enabled and i == handopt_start_step:
                        # FOHO_F3_STRICT_ONE_RUN
                        print('[FOHO_F3_BYPASS] skipped phase-1 hand optimization')
                    elif _foho_f3_enabled and i == handopt_start_step + 1:
                        print('[FOHO_F3_BYPASS] skipped phase-1.5 object optimization')
                    elif i == handopt_start_step: # pre-guidance step: optimize hands while reconstructing the object separately
                        info_str = f'Pre-guidance step {i}, optimizing hands only'
                        if loss_log_file:
                            loss_log_file.write(info_str + '\n')
                        print(info_str)

                        params_guidance_hand, noise_pred_obj, scale_hand, trans_hand, rotation_hand, scale_obj, trans_obj, rotation_obj = get_guidance_params(
                            phase=1,
                            noise_pred_obj=noise_pred_obj,
                            scale_hand=scale_hand,
                            trans_hand=trans_hand,
                            rotation_hand=rotation_hand,
                            scale_obj=scale_obj,
                            trans_obj=trans_obj,
                            rotation_obj=rotation_obj,
                            device=device,
                            phase1_hand_lrs=phase1_hand_lrs,
                            phase2_hand_lrs=phase2_hand_lrs,
                            noise_obj_lr1=noise_obj_lr1,
                            noise_obj_lr2=noise_obj_lr2,
                            obj_lrs=obj_lrs,
                            obj_2half_lrs=obj_2half_lrs,
                        )
                        hand_optimizer = torch.optim.Adam(params_guidance_hand, eps=1e-4)
                        
                        for k in range(0 if _foho_external_anchor_active else optimization_steps_hand):
                            hand_optimizer.zero_grad()

                            RT = torch.eye(4, device=device)
                            RT[:3, :3] = quaternion_to_matrix(rotation_hand).float().unsqueeze(0)
                            RT[:3, 3] = trans_hand
                            transformed_hand_mesh = transform_mesh_around_center_w_scale(mano_mesh_moge, RT, scale_hand)
                            with torch.cuda.amp.autocast(enabled=False):
                                rendered_normal_hand, rendered_disp_hand = render_normal_and_disparity(renderer, transformed_hand_mesh)
                                sil_mano_hand = sil_renderer(transformed_hand_mesh)[..., 3]

                                if debugging:
                                    if k % 10 == 0:
                                        plot_in_grid(rendered_normal_hand, moge_normal, save_path=f'{save_dir}/rendered_normal_hand_t{i}_opt{k}.png')

                            opt_3d_kps = mano_vert_to_3dkps(transformed_hand_mesh, J_regressor, device).unsqueeze(0) # (1,N,3)
                            opt_2d_kps_screen = renderer.rasterizer.cameras.transform_points_screen(opt_3d_kps, image_size=(H, W)).squeeze(0)  # (N,3)
                            opt_2d_kps = opt_2d_kps_screen[:, :2]  # (N, 2)
                            loss_2d_kps = F.mse_loss(opt_2d_kps, torch.tensor(hamer_2d_kps, device=device).float()) 
                            loss_normal_hand = normal_alignment_loss(rendered_normal_hand, moge_normal, valid_mask=moge_hand_mask)
                            loss_disp_hand = F.l1_loss(rendered_disp_hand, moge_disp * moge_hand_mask)
                            loss_silhouette_hand = F.binary_cross_entropy(sil_mano_hand.float(), moge_hand_sil.float()) #F.l1_loss(sil_mano_hand, moge_hand_sil) #F.binary_cross_entropy(sil_mano_hand, moge_hand_sil, reduction='none')
                            loss_hand_trans = (trans_hand ** 2).mean() # regularization on hand translation to prevent exploding translation
                            total_hand_loss = (
                                1e-2 * loss_2d_kps +
                                1 * loss_normal_hand +
                                10 * loss_disp_hand +
                                1 * loss_silhouette_hand +
                                1e-2 * loss_hand_trans 
                            )
                            
                            if k % 10 == 0:
                                loss_str = f'Opt step {k}, loss_2d_kps: {loss_2d_kps.item()}, loss_normal_hand: {loss_normal_hand.item()}, loss_disp_hand: {loss_disp_hand.item()}'
                                if loss_log_file:
                                    loss_log_file.write(loss_str + '\n')
                                print(loss_str)
                            
                            total_hand_loss.backward()
                            hand_optimizer.step()

                    
                    elif i == handopt_start_step + 1: # optimize the object mesh transformation
                        if os.environ.get("FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "0") == "1" and foho_obj_state_before_phase42 is None:
                            foho_obj_state_before_phase42 = {
                                "scale_obj": scale_obj.clone().detach(),
                                "trans_obj": trans_obj.clone().detach(),
                                "rotation_obj": rotation_obj.clone().detach(),
                                "obj_latents": obj_latents.clone().detach(),
                            }
                            # Mesh clone is saved later, after transformed_obj_mesh exists.
                            print(f"[FOHO_INTERNAL_SELECTOR] saved before_phase42 state at step {i}")
                        info_str = f'Object optimization step {i}, optimizing object transformation'
                        if loss_log_file:
                            loss_log_file.write(info_str + '\n')
                        print(info_str)

                        if _foho_external_anchor_active:
                            transformed_hand_mesh = _foho_helper.restore_external_anchor(
                                _foho_anchor_state,
                                torch_module=torch,
                                device=device,
                                mano_mesh_moge=mano_mesh_moge,
                                scale_hand=scale_hand,
                                trans_hand=trans_hand,
                                rotation_hand=rotation_hand,
                                quaternion_to_matrix=quaternion_to_matrix,
                                transform_mesh_around_center_w_scale=transform_mesh_around_center_w_scale,
                            )
                        params_guidance_obj, noise_pred_obj, scale_hand, trans_hand, rotation_hand, scale_obj, trans_obj, rotation_obj = get_guidance_params(
                            phase=1.5,
                            noise_pred_obj=noise_pred_obj,
                            scale_hand=scale_hand,
                            trans_hand=trans_hand,
                            rotation_hand=rotation_hand,
                            scale_obj=scale_obj,
                            trans_obj=trans_obj,
                            rotation_obj=rotation_obj,
                            device=device,
                            phase1_hand_lrs=phase1_hand_lrs,
                            phase2_hand_lrs=phase2_hand_lrs,
                            noise_obj_lr1=noise_obj_lr1,
                            noise_obj_lr2=noise_obj_lr2,
                            obj_lrs=obj_lrs,
                            obj_2half_lrs=obj_2half_lrs,
                        )
                        if _foho_external_anchor_active:
                            _foho_helper.assert_object_guidance_excludes_frozen_hand(
                                params_guidance_obj, scale_hand, trans_hand, rotation_hand
                            )
                            transformed_hand_mesh = _foho_helper.restore_external_anchor(
                                _foho_anchor_state,
                                torch_module=torch,
                                device=device,
                                mano_mesh_moge=mano_mesh_moge,
                                scale_hand=scale_hand,
                                trans_hand=trans_hand,
                                rotation_hand=rotation_hand,
                                quaternion_to_matrix=quaternion_to_matrix,
                                transform_mesh_around_center_w_scale=transform_mesh_around_center_w_scale,
                            )
                        object_optimizer = torch.optim.AdamW(params_guidance_obj, eps=1e-4)
                        print(f"[FOHO_DEBUG_OBJ_INIT] phase entry scale_obj={scale_obj.item():.4f} trans_obj={trans_obj.detach().cpu().tolist()}") 

                        for k in range(5 if _foho_external_anchor_active else optimization_steps_scale): # optimization_steps_joint
                            object_optimizer.zero_grad()

                            # object refinement starts
                            # obj_latent_x1 = self.scheduler.step_final(noise_pred_obj, t, obj_latents)
                            # FOHO_GATE_A_FIXED_OBJECT_PATCH_APPLIED
                            _foho_fixed_obj_ply = os.environ.get("FOHO_GATE_A_FIXED_OBJECT_PLY", "")
                            if _foho_fixed_obj_ply:
                                obj_mesh = _foho_fixed_obj_mesh_cached
                                moge_obj_mesh = transform_hunyuan2moge(obj_mesh, T_h2m)
                            else:
                                obj_latent_x1 = self.scheduler.step_final(noise_pred_obj, t, obj_latents)
                                obj_pred_sdf = latent2sdf(obj_latent_x1, xyz_samples, grid_size, self.vae, device)
                                obj_verts, obj_faces, _ = flexi(xyz_samples, obj_pred_sdf[0].flatten(), cube_indices, octree_res)

                                if obj_verts.shape[0] == 0:
                                    print('Invalid mesh detected, aborting step!')
                                    continue # skip step

                                # additional: define obj texture for consistency in join_meshes_as_scene
                                tex_obj = torch.zeros_like(obj_verts) # add texture to the obj mesh for silhoutte loss
                                tex_obj[:, 2] = 1.0 # blue
                                tex_obj = TexturesVertex(verts_features=[tex_obj])
                                obj_mesh = Meshes(verts=[obj_verts], faces=[obj_faces], textures=tex_obj).to(device)

                                # transform object mesh to moge space and rotate/scale/translate it in mofe space
                                moge_obj_mesh = transform_hunyuan2moge(obj_mesh, T_h2m) # putting the obj in moge space
                            RT_obj = torch.eye(4, device=device)
                            RT_obj[:3, :3] = quaternion_to_matrix(rotation_obj).float().unsqueeze(0)
                            RT_obj[:3, 3] = trans_obj
                            transformed_obj_mesh = transform_mesh_around_center_w_scale(moge_obj_mesh, RT_obj, scale_obj) 

                            if os.environ.get("FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "0") == "1" and foho_obj_mesh_before_phase42 is None:
                                try:
                                    foho_obj_mesh_before_phase42 = foho_clone_p3d_mesh(transformed_obj_mesh)
                                    if debugging and save_dir:
                                        foho_save_native_obj_render(
                                            renderer,
                                            foho_obj_mesh_before_phase42,
                                            moge_normal * moge_obj_mask[..., None],
                                            f"{save_dir}/foho_selector_before_phase42_native.png",
                                        )
                                    before_score_dbg = foho_score_p3d_mesh(foho_obj_mesh_before_phase42)
                                    print(
                                        f"[FOHO_INTERNAL_SELECTOR_AUTO] saved before_phase42 mesh "
                                        f"at step {i}; frag={before_score_dbg['fragmentation_score']:.6f}, "
                                        f"comp={before_score_dbg['components']}"
                                    )
                                except Exception as e:
                                    foho_obj_mesh_before_phase42 = None
                                    print(f"[FOHO_INTERNAL_SELECTOR_AUTO] failed to save before_phase42 mesh after transform: {e}")

                            # rendering normal and disparity maps
                            with torch.cuda.amp.autocast(enabled=False):
                                rendered_obj_normal, rendered_obj_disp = render_normal_and_disparity(renderer, transformed_obj_mesh)
                                rendered_obj_sil = sil_renderer(transformed_obj_mesh)[..., 3]

                                if debugging:
                                    if k % 10 == 0:
                                        plot_in_grid(rendered_obj_normal, moge_normal * moge_obj_mask[..., None], save_path=f'{save_dir}/rendered_obj_normal_t{i}_opt{k}.png')
                            
                            loss_normal = normal_alignment_loss(rendered_obj_normal, moge_normal, valid_mask=moge_obj_mask) 
                            loss_disp = F.l1_loss(rendered_obj_disp, moge_disp * moge_obj_mask)
                            loss_silhouette = torch.nn.functional.binary_cross_entropy(rendered_obj_sil.float(), moge_obj_mask.float()) 
                            obj_verts_loss = transformed_obj_mesh.verts_packed().pow(2).mean() # regularization on object mesh verts
                            loss_obj_trans_reg = (trans_obj ** 2).mean() # regularization on object translation to prevent exploding translation
                            
                            # add additional object mesh losses from pytorch
                            w_edge = 1.0 
                            w_normal = 0.01
                            obj_loss_edge = mesh_edge_loss(transformed_obj_mesh)
                            obj_loss = obj_loss_edge * w_edge 
                            
                            total_obj_loss = (
                                1 * obj_loss +
                                10 * loss_normal + 
                                10 * loss_disp +
                                100 * loss_silhouette +
                                1e-3 * obj_verts_loss +
                                1e-2 * loss_obj_trans_reg 
                            )

                            if torch.isnan(total_obj_loss):
                                print('Total loss is NaN') # investigate from which loss NaN comes and why that loss is NaN
                                return None

                            if k % 10 == 0:
                                loss_str = f'Opt step {k}, object loss: {obj_loss.item()}, loss_normal_obj: {loss_normal.item()}, loss_disp: {loss_disp.item()}'
                                if loss_log_file:
                                    loss_log_file.write(loss_str + '\n')
                                print(loss_str)                            
                            
                            total_obj_loss.backward()
                            object_optimizer.step()
                            try:
                                _foho_dbg = {}
                                for _name in ["scale_obj", "trans_obj", "rotation_obj", "loss", "loss_normal_obj", "loss_normal_hoi", "loss_disp", "loss_intersection"]:
                                    if _name in locals():
                                        _v = locals()[_name]
                                        try:
                                            _foho_dbg[_name] = _v.detach().cpu().tolist()
                                        except Exception:
                                            _foho_dbg[_name] = str(_v)
                                print("[FOHO_DEBUG_OBJ_TRAJ] " + __import__("json").dumps({"k": locals().get("k", "NA"), "i": locals().get("i", "NA"), "values": _foho_dbg}))
                            except Exception as _e:
                                print(f"[FOHO_DEBUG_OBJ_TRAJ_FAIL] {repr(_e)}")
                        if _foho_external_anchor_active:
                            _foho_helper.write_post_object_checkpoint(
                                _foho_anchor_state,
                                torch_module=torch,
                                transformed_hand_mesh=transformed_hand_mesh,
                                transformed_object_mesh=transformed_obj_mesh,
                                scale_hand=scale_hand,
                                trans_hand=trans_hand,
                                rotation_hand=rotation_hand,
                                object_RT=RT_obj,
                                object_scale=scale_obj,
                                runtime_locals=locals(),
                            )
                        # FOHO_EXTERNAL_S100_UP_SEAM_V99_11_7_13_3_13_4_1_END
                    elif (
                        handopt_start_step + 2 <= i <= guidance_end_step
                        and (
                            not _foho_f3_enabled
                            or i == handopt_start_step + 2
                        )
                    ): # joint optimization step: optimize hands and object together
                        if os.environ.get("FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "0") == "1" and not foho_phase42_selector_applied:
                            choice = os.environ.get("FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE", "phase42_before_joint")

                            selected_name = "phase42_before_joint"

                            if choice == "auto_fragmentation":
                                if debugging and save_dir:
                                    try:
                                        foho_save_native_obj_render(
                                            renderer,
                                            transformed_obj_mesh,
                                            moge_normal * moge_obj_mask[..., None],
                                            f"{save_dir}/foho_selector_phase42_before_joint_native.png",
                                        )
                                    except Exception as e:
                                        print(f"[FOHO_SELECTOR_RENDER] failed phase42 render: {e}")

                                # FOHO_F3_1_TRANSFORMED_OBJ_MESH_SCORE_GUARD_V1
                                _foho_score_base_obj_mesh = None
                                for _foho_score_obj_name in (
                                    'obj_mesh_moge',
                                    'obj_mesh',
                                    'object_mesh_moge',
                                    'object_mesh',
                                ):
                                    _foho_score_base_obj_mesh = locals().get(
                                        _foho_score_obj_name, None
                                    )
                                    if _foho_score_base_obj_mesh is not None:
                                        break
                                if _foho_score_base_obj_mesh is None:
                                    raise RuntimeError(
                                        'F3.1 could not locate an object mesh before scoring'
                                    )
                                if (
                                    'rotation_obj' not in locals()
                                    or 'trans_obj' not in locals()
                                    or 'scale_obj' not in locals()
                                ):
                                    raise RuntimeError(
                                        'F3.1 requires rotation_obj/trans_obj/scale_obj before scoring'
                                    )
                                _foho_score_RT_obj = torch.eye(4, device=device)
                                _foho_score_RT_obj[:3, :3] = quaternion_to_matrix(
                                    rotation_obj
                                ).float().squeeze(0)
                                _foho_score_RT_obj[:3, 3] = trans_obj
                                transformed_obj_mesh = transform_mesh_around_center_w_scale(
                                    _foho_score_base_obj_mesh,
                                    _foho_score_RT_obj,
                                    scale_obj,
                                )
                                current_score = foho_score_p3d_mesh(transformed_obj_mesh)
                                before_score = foho_score_p3d_mesh(foho_obj_mesh_before_phase42) if foho_obj_mesh_before_phase42 is not None else {
                                    "fragmentation_score": 999.0,
                                    "components": 999,
                                    "largest_face_ratio": 0.0,
                                    "watertight": False,
                                }

                                current_frag = float(current_score["fragmentation_score"])
                                before_frag = float(before_score["fragmentation_score"])
                                margin = float(os.environ.get("FOHO_INTERNAL_SELECTOR_MARGIN", "0.0"))

                                # FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5B_TRUE_PHASE42
                                # Save/export the true Phase 4.2 candidate before selector overwrite.
                                try:
                                    _foho_os = __import__("os")
                                    _foho_export_dir = _foho_os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "") or _foho_os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")

                                    foho_obj_mesh_phase42_before_joint = foho_clone_p3d_mesh(transformed_obj_mesh)

                                    if _foho_export_dir:
                                        _foho_os.makedirs(_foho_export_dir, exist_ok=True)
                                        foho_export_p3d_mesh(
                                            foho_obj_mesh_phase42_before_joint,
                                            _foho_os.path.join(_foho_export_dir, "selector_candidate_phase42_before_joint.ply"),
                                        )
                                        print(
                                            f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5B] "
                                            f"true_phase42_candidate={_foho_os.path.join(_foho_export_dir, 'selector_candidate_phase42_before_joint.ply')}"
                                        )
                                    else:
                                        print("[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5B] skipped true phase42 export: export dir empty")
                                except Exception as e:
                                    print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5B] true phase42 export failed: {e}")

                                # FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5C_TRUE_PHASE42_UNIQUE
                                # Save the true Phase 4.2 candidate to a unique filename before selector overwrite.
                                try:
                                    _foho_os = __import__("os")
                                    _foho_export_dir = _foho_os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "") or _foho_os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")
                                    if _foho_export_dir:
                                        _foho_os.makedirs(_foho_export_dir, exist_ok=True)
                                        _foho_true_path = _foho_os.path.join(
                                            _foho_export_dir,
                                            "selector_candidate_phase42_before_joint_true.ply",
                                        )
                                        foho_export_p3d_mesh(transformed_obj_mesh, _foho_true_path)
                                        print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5C] true_phase42_candidate={_foho_true_path}")
                                    else:
                                        print("[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5C] skipped true phase42 export: export dir empty")
                                except Exception as e:
                                    print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5C] true phase42 export failed: {e}")

                                if before_frag + margin < current_frag and foho_obj_state_before_phase42 is not None:
                                    scale_obj = foho_obj_state_before_phase42["scale_obj"].clone().to(device)
                                    trans_obj = foho_obj_state_before_phase42["trans_obj"].clone().to(device)
                                    rotation_obj = foho_obj_state_before_phase42["rotation_obj"].clone().to(device)
                                    obj_latents = foho_obj_state_before_phase42["obj_latents"].clone().to(device)
                                    if foho_obj_mesh_before_phase42 is not None:
                                        transformed_obj_mesh = foho_obj_mesh_before_phase42.to(device)
                                    selected_name = "before_phase42"
                                else:
                                    selected_name = "phase42_before_joint"

                                print(
                                    f"[FOHO_INTERNAL_SELECTOR_AUTO] "
                                    f"before_frag={before_frag:.6f}, current_frag={current_frag:.6f}, "
                                    f"margin={margin:.6f}, selected={selected_name}"
                                )

                            elif choice in ["before_phase42", "pre_phase42", "initial"]:
                                if foho_obj_state_before_phase42 is None:
                                    print("[FOHO_INTERNAL_SELECTOR] before_phase42 state missing; keeping phase42_before_joint")
                                    selected_name = "phase42_before_joint"
                                else:
                                    scale_obj = foho_obj_state_before_phase42["scale_obj"].clone().to(device)
                                    trans_obj = foho_obj_state_before_phase42["trans_obj"].clone().to(device)
                                    rotation_obj = foho_obj_state_before_phase42["rotation_obj"].clone().to(device)
                                    obj_latents = foho_obj_state_before_phase42["obj_latents"].clone().to(device)
                                    if foho_obj_mesh_before_phase42 is not None:
                                        transformed_obj_mesh = foho_obj_mesh_before_phase42.to(device)
                                    selected_name = "before_phase42"

                            elif choice in ["phase42_before_joint", "phase42", "current"]:
                                selected_name = "phase42_before_joint"

                            else:
                                selected_name = "phase42_before_joint"
                                print(f"[FOHO_INTERNAL_SELECTOR] unknown choice={choice}; keeping phase42_before_joint")

                            # FOHO DEBUG: export exact selector candidates in the same runtime frame.
                            try:
                                export_dir = os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "")
                                if export_dir:
                                    os.makedirs(export_dir, exist_ok=True)

                                    if foho_obj_mesh_before_phase42 is not None:
                                        foho_export_p3d_mesh(
                                            foho_obj_mesh_before_phase42,
                                            os.path.join(export_dir, "selector_candidate_before_phase42.ply"),
                                        )

                                    foho_export_p3d_mesh(
                                        transformed_obj_mesh,
                                        os.path.join(export_dir, "selector_selected_before_joint.ply"),
                                    )

                                    # This file name is intentionally written after selection.
                                    # If selected_name == phase42_before_joint, this is the Phase 4.2 candidate.
                                    # If selected_name == before_phase42, this is the restored before-Phase-4.2 candidate.
                                    print(
                                        f"[FOHO_INTERNAL_SELECTOR_EXPORT] export_dir={export_dir}; "
                                        f"selected={selected_name}"
                                    )
                            except Exception as e:
                                print(f"[FOHO_INTERNAL_SELECTOR_EXPORT] failed: {e}")

                            foho_phase42_selector_applied = True
                            # FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3_SELECTED
                            try:
                                _foho_os = __import__("os")
                                _foho_export_dir = _foho_os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "") or _foho_os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")
                                if _foho_export_dir:
                                    _foho_os.makedirs(_foho_export_dir, exist_ok=True)
                                    if "foho_obj_mesh_before_phase42" in locals() and foho_obj_mesh_before_phase42 is not None:
                                        foho_export_p3d_mesh(foho_obj_mesh_before_phase42, _foho_os.path.join(_foho_export_dir, "selector_candidate_before_phase42.ply"))
                                    foho_export_p3d_mesh(transformed_obj_mesh, _foho_os.path.join(_foho_export_dir, "selector_selected_before_joint.ply"))
                                    print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3] export_dir={_foho_export_dir}; selected={selected_name}")
                                else:
                                    print("[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3] skipped selected export: export dir empty")
                            except Exception as e:
                                print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3] selected export failed: {e}")
                            # FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3_SELECTED
                            try:
                                _foho_os = __import__("os")
                                _foho_export_dir = _foho_os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "") or _foho_os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")
                                if _foho_export_dir:
                                    _foho_os.makedirs(_foho_export_dir, exist_ok=True)
                                    if "foho_obj_mesh_before_phase42" in locals() and foho_obj_mesh_before_phase42 is not None:
                                        foho_export_p3d_mesh(foho_obj_mesh_before_phase42, _foho_os.path.join(_foho_export_dir, "selector_candidate_before_phase42.ply"))
                                    foho_export_p3d_mesh(transformed_obj_mesh, _foho_os.path.join(_foho_export_dir, "selector_selected_before_joint.ply"))
                                    print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3] export_dir={_foho_export_dir}; selected={selected_name}")
                                else:
                                    print("[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3] skipped selected export: export dir empty")
                            except Exception as e:
                                print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3] selected export failed: {e}")
                            # FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4_SELECTED
                            try:
                                _foho_os = __import__("os")
                                _foho_export_dir = _foho_os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "") or _foho_os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")
                                if _foho_export_dir:
                                    _foho_os.makedirs(_foho_export_dir, exist_ok=True)
                                    if "foho_obj_mesh_before_phase42" in locals() and foho_obj_mesh_before_phase42 is not None:
                                        foho_export_p3d_mesh(
                                            foho_obj_mesh_before_phase42,
                                            _foho_os.path.join(_foho_export_dir, "selector_candidate_before_phase42.ply"),
                                        )
                                    foho_export_p3d_mesh(
                                        transformed_obj_mesh,
                                        _foho_os.path.join(_foho_export_dir, "selector_selected_before_joint.ply"),
                                    )
                                    print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4] export_dir={_foho_export_dir}; selected={selected_name}")
                                else:
                                    print("[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4] skipped selected export: export dir empty")
                            except Exception as e:
                                print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4] selected export failed: {e}")

                            print(f"[FOHO_INTERNAL_SELECTOR] selected={selected_name}; applied before joint step {i}")
                        info_str = f'Joint optimization step {i}, optimizing hands and object together'
                        if loss_log_file:
                            loss_log_file.write(info_str + '\n')
                        print(info_str)

                        params_guidance_hoi, noise_pred_obj, scale_hand, trans_hand, rotation_hand, scale_obj, trans_obj, rotation_obj = get_guidance_params(
                            phase=2,
                            noise_pred_obj=noise_pred_obj,
                            scale_hand=scale_hand,
                            trans_hand=trans_hand,
                            rotation_hand=rotation_hand,
                            scale_obj=scale_obj,
                            trans_obj=trans_obj,
                            rotation_obj=rotation_obj,
                            device=device,
                            phase1_hand_lrs=phase1_hand_lrs,
                            phase2_hand_lrs=phase2_hand_lrs,
                            noise_obj_lr1=noise_obj_lr1,
                            noise_obj_lr2=noise_obj_lr2,
                            obj_lrs=obj_lrs,
                            obj_2half_lrs=obj_2half_lrs,
                        )
                        if _foho_f3_enabled:
                            # FOHO_F3_FREEZE_OBJECT
                            if _foho_f3_trans_hand_anchor is None:
                                _foho_f3_trans_hand_anchor = (
                                    trans_hand.detach().clone()
                                )

                            noise_pred_obj = (
                                noise_pred_obj.detach().clone()
                            )
                            scale_obj = scale_obj.detach().clone()
                            rotation_obj = (
                                rotation_obj.detach().clone()
                            )
                            trans_obj = trans_obj.detach().clone()
                            scale_hand = scale_hand.detach().clone()
                            rotation_hand = (
                                rotation_hand.detach().clone()
                            )
                            trans_hand = (
                                trans_hand.detach().clone()
                                .requires_grad_(True)
                            )

                            # FOHO_F3_OPTIMIZER
                            if _foho_f31_enabled:
                                _foho_f31_rotation_delta_hand = torch.zeros(
                                    3,
                                    device=device,
                                    dtype=trans_hand.dtype,
                                    requires_grad=True,
                                )
                                f3_optimizer = torch.optim.AdamW(
                                    [
                                        {
                                            "params": [trans_hand],
                                            "lr": _foho_f3_translation_lr,
                                        },
                                        {
                                            "params": [
                                                _foho_f31_rotation_delta_hand
                                            ],
                                            "lr": _foho_f31_rotation_lr,
                                        },
                                    ],
                                    eps=1e-4,
                                )
                                print(
                                    "[PASS] "
                                    "F3_1_RUNTIME_TRAINABLES_TRANS_PLUS_ROT_DELTA_ONLY"
                                )
                            else:
                                f3_optimizer = torch.optim.AdamW(
                                    [trans_hand],
                                    lr=_foho_f3_translation_lr,
                                    eps=1e-4,
                                )
                            _foho_active_optimizer = f3_optimizer
                            _foho_f3_steps_this_outer = (
                                0
                                if _foho_f3_preflight_only
                                else _foho_f3_steps
                            )
                            print(
                                '[FOHO_F3_RUNTIME_PLAN] '
                                f'outer_step={i}, '
                                f'inner_steps={_foho_f3_steps_this_outer}'
                            )
                            if _foho_f31_enabled:
                                print(
                                    '[FOHO_F3_1_RUNTIME_PLAN] '
                                    f'outer_step={i}, '
                                    f'inner_steps={_foho_f3_steps_this_outer}, '
                                    f'max_rotation_rad={_foho_f31_max_rotation_rad}'
                                )

                            if _foho_f32_enabled:
                                print(
                                    "[FOHO_F3_2_RUNTIME_PLAN] "
                                    f"outer_step={i}, "
                                    f"inner_steps={_foho_f3_steps_this_outer}, "
                                    f"stage_a_steps={_foho_f32_stage_a_steps}, "
                                    f"collision_weight={_foho_f32_collision_weight}, "
                                    f"mask_refresh={_foho_f32_mask_refresh}"
                                )

                            # FOHO_F3_1_AWARE_OPTIMIZER_CONTRACT_V2
                            _foho_f3_optimizer_ids = {
                                id(_parameter)
                                for _group in f3_optimizer.param_groups
                                for _parameter in _group["params"]
                            }

                            if _foho_f31_enabled:
                                if _foho_f31_rotation_delta_hand is None:
                                    raise RuntimeError(
                                        "F3.1 rotation delta is missing before the "
                                        "optimizer contract check."
                                    )
                                _foho_f3_expected_optimizer_ids = {
                                    id(trans_hand),
                                    id(_foho_f31_rotation_delta_hand),
                                }
                            else:
                                _foho_f3_expected_optimizer_ids = {id(trans_hand)}

                            if (
                                _foho_f3_optimizer_ids
                                != _foho_f3_expected_optimizer_ids
                            ):
                                raise RuntimeError(
                                    "F3/F3.1 optimizer trainable contract mismatch."
                                )

                            if not _foho_f31_enabled:
                                # FOHO_F3_TRAINABLES
                                print(
                                    "[FOHO_F3_TRAINABLES]",
                                    ["trans_hand"],
                                )
                                print(
                                    "[PASS] "
                                    "F3_RUNTIME_TRAINABLES_TRANS_HAND_ONLY"
                                )
                        else:
                            joint_optimizer = torch.optim.AdamW(
                                params_guidance_hoi, eps=1e-4
                            )
                            _foho_active_optimizer = joint_optimizer
                            _foho_f3_steps_this_outer = (
                                optimization_steps_joint
                            ) 

                        for k in range(_foho_f3_steps_this_outer):
                            _foho_active_optimizer.zero_grad()

                            RT_hand = torch.eye(4, device=device)
                            # FOHO_F3_1_ZERO_UPDATE_ROTATION_GUARD_V3
                            if _foho_f31_enabled and _foho_f31_rotation_delta_hand is None:
                                _foho_f31_rotation_delta_hand = torch.zeros(
                                    3,
                                    device=trans_hand.device,
                                    dtype=trans_hand.dtype,
                                    requires_grad=True,
                                )
                            if _foho_f31_enabled:
                                _foho_f31_base_rot = quaternion_to_matrix(
                                    rotation_hand
                                ).float().squeeze(0)
                                _foho_f31_delta_rot = axis_angle_to_matrix(
                                    _foho_f31_rotation_delta_hand.unsqueeze(0)
                                ).squeeze(0)
                                RT_hand[:3, :3] = (
                                    _foho_f31_delta_rot @ _foho_f31_base_rot
                                )
                            else:
                                RT_hand[:3, :3] = quaternion_to_matrix(rotation_hand).float().unsqueeze(0)
                            RT_hand[:3, 3] = trans_hand
                            transformed_hand_mesh = transform_mesh_around_center_w_scale(mano_mesh_moge, RT_hand, scale_hand)
                            with torch.cuda.amp.autocast(enabled=False):
                                rendered_normal_hand, rendered_disp_hand = render_normal_and_disparity(renderer, transformed_hand_mesh)

                            opt_3d_kps = mano_vert_to_3dkps(transformed_hand_mesh, J_regressor, device).unsqueeze(0) 
                            opt_2d_kps_screen = renderer.rasterizer.cameras.transform_points_screen(opt_3d_kps, image_size=(H, W)).squeeze(0)  # (N, 3)
                            opt_2d_kps = opt_2d_kps_screen[:, :2]  # (N, 2)

                            # hand losses
                            loss_2d_kps = F.mse_loss(opt_2d_kps, torch.tensor(hamer_2d_kps, device=device).float()) 
                            loss_normal_hand = normal_alignment_loss(rendered_normal_hand, moge_normal, valid_mask=moge_hand_mask)
                            loss_disp_hand = F.l1_loss(rendered_disp_hand, moge_disp * moge_hand_mask)
                            loss_hand_trans = (trans_hand ** 2).mean() # regularization on hand translation to prevent exploding translation
                            hand_loss = (
                                1e-4 * loss_2d_kps +
                                10 * loss_normal_hand +
                                10 * loss_disp_hand +
                                1e-2 * loss_hand_trans
                            )

                            # object refinement starts
                            _foho_fixed_obj_ply2 = os.environ.get("FOHO_GATE_A_FIXED_OBJECT_PLY", "")
                            if _foho_fixed_obj_ply2:
                                obj_mesh = _foho_fixed_obj_mesh_cached
                                moge_obj_mesh = transform_hunyuan2moge(obj_mesh, T_h2m)
                            else:
                                obj_latent_x1 = self.scheduler.step_final(noise_pred_obj, t, obj_latents)
                                obj_pred_sdf = latent2sdf(obj_latent_x1, xyz_samples, grid_size, self.vae, device)
                                obj_verts, obj_faces, _ = flexi(xyz_samples, obj_pred_sdf[0].flatten(), cube_indices, octree_res)

                                if obj_verts.shape[0] == 0:
                                    print('Invalid mesh detected, aborting step!')
                                    continue # skip step

                                # additional: define obj texture for consistency in join_meshes_as_scene
                                tex_obj = torch.zeros_like(obj_verts) # add texture to the obj mesh for silhoutte loss
                                tex_obj[:, 2] = 1.0 # blue
                                tex_obj = TexturesVertex(verts_features=[tex_obj]).to(device)
                                obj_mesh = Meshes(verts=[obj_verts], faces=[obj_faces], textures=tex_obj)
                                moge_obj_mesh = transform_hunyuan2moge(obj_mesh, T_h2m) # putting the obj in moge space

                            # transform object mesh to moge space and rotate/scale/translate it in moge space
                            RT_obj = torch.eye(4, device=device)
                            RT_obj[:3, :3] = quaternion_to_matrix(rotation_obj).float().unsqueeze(0)
                            RT_obj[:3, 3] = trans_obj
                            transformed_obj_mesh = transform_mesh_around_center_w_scale(moge_obj_mesh, RT_obj, scale_obj) 

                            # FOHO_F2_SCREEN_LID_TARGET_FROM_FIXED_OBJECT
                            transformed_screen_lid_points = None
                            if _foho_f2_target_obj_idx is not None:
                                transformed_screen_lid_points = (
                                    transformed_obj_mesh.verts_packed()[
                                        _foho_f2_target_obj_idx
                                    ].unsqueeze(0)
                                )

                            selector_debug_dir = os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")
                            if selector_debug_dir:
                                foho_export_p3d_mesh(obj_mesh, f"{selector_debug_dir}/phase42_obj_raw_hunyuan_space_t{i}_opt{k}.ply")
                                foho_export_p3d_mesh(moge_obj_mesh, f"{selector_debug_dir}/phase42_obj_moge_space_t{i}_opt{k}.ply")
                                foho_export_p3d_mesh(transformed_obj_mesh, f"{selector_debug_dir}/phase42_obj_transformed_before_joint_t{i}_opt{k}.ply")

                            # Hand to object. NOTE: gradients only flow through hand mesh, not obj mesh
                            dists_hand_to_obj, _, _ = knn_points(
                                transformed_hand_mesh.verts_padded(),
                                transformed_obj_mesh.verts_padded(), K=1
                            )
                            dists_ho = dists_hand_to_obj.squeeze(0).squeeze(-1)
                            # Object to hand
                            dists_obj_to_hand, _, _ = knn_points(
                                transformed_obj_mesh.verts_padded(),
                                transformed_hand_mesh.verts_padded(), K=1
                            )
                            margin = 0.01
                            attract = torch.clamp(dists_ho - margin, min=0)
                            distance_loss = attract.mean()

                            # FOHO_F2_SCREEN_LID_CONTACT_LOSS
                            screen_lid_contact_loss = torch.tensor(
                                0.0, device=device
                            )
                            screen_lid_patch_mean_m = torch.tensor(
                                0.0, device=device
                            )
                            screen_lid_patch_min_m = torch.tensor(
                                0.0, device=device
                            )

                            if transformed_screen_lid_points is not None:
                                _foho_f2_hand_to_lid_d2, _, _ = knn_points(
                                    transformed_hand_mesh.verts_padded(),
                                    transformed_screen_lid_points,
                                    K=1,
                                )

                                _foho_f2_hand_to_lid_m = torch.sqrt(
                                    torch.clamp(
                                        _foho_f2_hand_to_lid_d2
                                        .squeeze(0)
                                        .squeeze(-1),
                                        min=1e-12,
                                    )
                                )

                                if _foho_f2_hand_patch_idx is None:
                                    _foho_f2_patch_k = max(
                                        1,
                                        min(
                                            _foho_f2_hand_patch_size,
                                            _foho_f2_hand_to_lid_m.numel(),
                                        ),
                                    )
                                    with torch.no_grad():
                                        _foho_f2_hand_patch_idx = torch.topk(
                                            _foho_f2_hand_to_lid_m.detach(),
                                            k=_foho_f2_patch_k,
                                            largest=False,
                                        ).indices
                                    print(
                                        "[FOHO_F2] locked hand contact patch; "
                                        f"vertices={_foho_f2_patch_k}"
                                    )

                                _foho_f2_patch_dist_m = (
                                    _foho_f2_hand_to_lid_m[
                                        _foho_f2_hand_patch_idx
                                    ]
                                )
                                _foho_f2_target_dist = torch.full_like(
                                    _foho_f2_patch_dist_m,
                                    _foho_f2_target_distance_m,
                                )

                                # A small contact band is safer than pulling
                                # every vertex to zero distance. It can also
                                # discourage points already closer than the
                                # requested safety distance.
                                screen_lid_contact_loss = F.smooth_l1_loss(
                                    _foho_f2_patch_dist_m,
                                    _foho_f2_target_dist,
                                    beta=_foho_f2_huber_beta_m,
                                )
                                screen_lid_patch_mean_m = (
                                    _foho_f2_patch_dist_m.mean()
                                )
                                screen_lid_patch_min_m = (
                                    _foho_f2_patch_dist_m.min()
                                )

                            # FOHO_F3_LOCAL_CONTACT_LOSS
                            _foho_f3_contact_loss = torch.tensor(
                                0.0, device=device
                            )
                            _foho_f3_tip_mean_m = torch.tensor(
                                0.0, device=device
                            )
                            _foho_f3_tip_min_m = torch.tensor(
                                0.0, device=device
                            )
                            _foho_f3_translation_delta_loss = (
                                torch.tensor(0.0, device=device)
                            )

                            if _foho_f3_enabled:
                                if (
                                    _foho_f3_target_obj_idx is None
                                    or _foho_f3_tip_idx is None
                                ):
                                    raise RuntimeError(
                                        "F3 target/tip mapping is missing."
                                    )
                                if (
                                    int(
                                        _foho_f3_tip_idx.max().item()
                                    )
                                    >= transformed_hand_mesh
                                    .verts_packed()
                                    .shape[0]
                                ):
                                    raise RuntimeError(
                                        "F3 fingertip ID exceeds the "
                                        "runtime hand vertex count."
                                    )

                                _foho_f3_target_points = (
                                    transformed_obj_mesh
                                    .verts_packed()[
                                        _foho_f3_target_obj_idx
                                    ]
                                    .detach()
                                    .unsqueeze(0)
                                )
                                _foho_f3_tip_points = (
                                    transformed_hand_mesh
                                    .verts_packed()[
                                        _foho_f3_tip_idx
                                    ]
                                    .unsqueeze(0)
                                )
                                (
                                    _foho_f3_tip_d2,
                                    _,
                                    _,
                                ) = knn_points(
                                    _foho_f3_tip_points,
                                    _foho_f3_target_points,
                                    K=1,
                                )
                                _foho_f3_tip_distance_m = (
                                    torch.sqrt(
                                        torch.clamp(
                                            _foho_f3_tip_d2
                                            .squeeze(0)
                                            .squeeze(-1),
                                            min=1e-12,
                                        )
                                    )
                                )
                                _foho_f3_target_distance = (
                                    torch.full_like(
                                        _foho_f3_tip_distance_m,
                                        _foho_f3_target_distance_m,
                                    )
                                )
                                _foho_f3_contact_loss = (
                                    F.smooth_l1_loss(
                                        _foho_f3_tip_distance_m,
                                        _foho_f3_target_distance,
                                        beta=_foho_f3_huber_beta_m,
                                    )
                                )
                                _foho_f3_tip_mean_m = (
                                    _foho_f3_tip_distance_m.mean()
                                )
                                _foho_f3_tip_min_m = (
                                    _foho_f3_tip_distance_m.min()
                                )
                                _foho_f3_translation_delta_loss = (
                                    (
                                        trans_hand
                                        - _foho_f3_trans_hand_anchor
                                    )
                                    .pow(2)
                                    .mean()
                                )

                            # rendering normal and disparity maps
                            # FOHO_GATE_A_TEXTURE_SAFE_JOINT_JOIN
                            # Normal/disparity/silhouette/contact losses use
                            # geometry, not RGB textures. Ignore incompatible
                            # texture containers when forming the HOI scene.
                            hoi_mesh = join_meshes_as_scene(
                                [transformed_hand_mesh, transformed_obj_mesh],
                                include_textures=False,
                            )
                            with torch.cuda.amp.autocast(enabled=False):
                                rendered_hoi_normal, rendered_hoi_disp = render_normal_and_disparity(renderer, hoi_mesh)
                                rendered_hoi_sil = sil_renderer(hoi_mesh)[..., 3]
                                rendered_obj_normal, rendered_obj_disp = render_normal_and_disparity(renderer, transformed_obj_mesh)
                                rendered_obj_sil = sil_renderer(transformed_obj_mesh)[..., 3]

                            # SDF part for intersection
                            if use_intersection_loss:
                                SDF_t_hand, SDF_t_obj = kaolin_sdf.get_sdf_of_meshes(transformed_hand_mesh, transformed_obj_mesh, device, octree_res)
                                loss_intersection = honerf_intersection_loss(SDF_t_hand, SDF_t_obj)
                                if torch.isnan(loss_intersection):
                                    print('Intersection loss is NaN')
                                    loss_intersection = torch.tensor(0.0, device=device)
                            else:
                                loss_intersection = torch.tensor(0.0, device=device)

                            if dists_ho.mean() < 0.001 and i >= num_inference_steps - 3: # if the distance is smaller than 0.005 m, apply intersection loss
                                w_intersection = 1e-5
                            else:
                                w_intersection = 1e-9

                            # hoi losses
                            loss_normal_hoi = normal_alignment_loss(rendered_hoi_normal, moge_normal, valid_mask=moge_hoi_mask)
                            loss_disp_hoi = F.l1_loss(rendered_hoi_disp, moge_disp)
                            loss_silhouette_hoi = torch.nn.functional.binary_cross_entropy(rendered_hoi_sil, moge_sil.float())
                            obj_verts_loss_3 = transformed_obj_mesh.verts_packed().pow(2).mean() # regularization on object mesh verts
                            loss_obj_reg = (trans_obj ** 2).mean()
                            
                            # add additional object mesh losses from pytorch
                            w_edge = 1.0 
                            obj_loss_edge_3 = mesh_edge_loss(transformed_obj_mesh)
                            obj_loss_3 = obj_loss_edge_3 * w_edge 

                            # FOHO_F3_2_COLLISION_LOSS_V2
                            _foho_f32_collision_loss = torch.tensor(
                                0.0, device=device
                            )
                            _foho_f32_anchor_translation_loss = torch.tensor(
                                0.0, device=device
                            )
                            _foho_f32_anchor_rotation_loss = torch.tensor(
                                0.0, device=device
                            )
                            object_vertices_inside_hand = 0

                            if _foho_f32_enabled:
                                # Capture the Stage-A pose once cleanup begins.
                                if (
                                    k >= _foho_f32_stage_a_steps
                                    and _foho_f32_stage_a_trans_hand is None
                                ):
                                    _foho_f32_stage_a_trans_hand = (
                                        trans_hand.detach().clone()
                                    )
                                    if _foho_f31_rotation_delta_hand is not None:
                                        _foho_f32_stage_a_rotation_delta_hand = (
                                            _foho_f31_rotation_delta_hand
                                            .detach()
                                            .clone()
                                        )
                                    if _foho_f33_enabled and not _foho_f33_escape_applied:
                                        with torch.no_grad():
                                            trans_hand[..., 2].add_(_foho_f33_escape_z_m)
                                        _foho_f32_stage_a_trans_hand = trans_hand.detach().clone()
                                        _foho_f33_escape_applied = True
                                        print("[FOHO_F3_3_STAGE_B_ESCAPE] " f"k={k} z_m={_foho_f33_escape_z_m:.6f}")
                                    print(
                                        "[FOHO_F3_2_STAGE_A_ANCHOR] "
                                        f"k={k}"
                                    )

                                if k >= _foho_f32_stage_a_steps:
                                    if (
                                        _foho_f32_collision_mask is None
                                        or (
                                            (k - _foho_f32_stage_a_steps)
                                            % _foho_f32_mask_refresh
                                            == 0
                                        )
                                    ):
                                        _foho_f32_hand_np = (
                                            transformed_hand_mesh
                                            .verts_packed()
                                            .detach()
                                            .cpu()
                                            .numpy()
                                        )
                                        _foho_f32_hand_faces_np = (
                                            transformed_hand_mesh
                                            .faces_packed()
                                            .detach()
                                            .cpu()
                                            .numpy()
                                        )
                                        _foho_f32_obj_np = (
                                            transformed_obj_mesh
                                            .verts_packed()
                                            .detach()
                                            .cpu()
                                            .numpy()
                                        )
                                        try:
                                            _foho_f32_tri = trimesh.Trimesh(
                                                vertices=_foho_f32_hand_np,
                                                faces=_foho_f32_hand_faces_np,
                                                process=False,
                                            )
                                            _foho_f32_inside_np = (
                                                _foho_f32_tri.contains(
                                                    _foho_f32_obj_np
                                                )
                                            )
                                        except Exception as _foho_f32_exc:
                                            raise RuntimeError(
                                                "F3.2 object_vertices_inside_hand "
                                                "mask failed; do not replace this "
                                                "with open-lid signed distances: "
                                                f"{type(_foho_f32_exc).__name__}: "
                                                f"{_foho_f32_exc}"
                                            )

                                        _foho_f32_collision_mask = torch.as_tensor(
                                            _foho_f32_inside_np,
                                            dtype=torch.bool,
                                            device=device,
                                        )
                                        object_vertices_inside_hand = int(
                                            _foho_f32_collision_mask
                                            .sum()
                                            .item()
                                        )
                                        print(
                                            "[FOHO_F3_2_COLLISION_MASK] "
                                            f"k={k}, "
                                            "object_vertices_inside_hand="
                                            f"{object_vertices_inside_hand}"
                                        )
                                    else:
                                        object_vertices_inside_hand = int(
                                            _foho_f32_collision_mask
                                            .sum()
                                            .item()
                                        )

                                    if _foho_f32_collision_mask.any():
                                        _foho_f32_pen_obj = (
                                            transformed_obj_mesh
                                            .verts_packed()[
                                                _foho_f32_collision_mask
                                            ]
                                            .detach()
                                        )
                                        _foho_f32_hand_verts = (
                                            transformed_hand_mesh.verts_packed()
                                        )
                                        _foho_f32_dists = torch.cdist(
                                            _foho_f32_pen_obj,
                                            _foho_f32_hand_verts,
                                        )
                                        _foho_f32_min_dist = (
                                            _foho_f32_dists.min(dim=1)[0]
                                        )
                                        # Minimize negative distance so gradient
                                        # moves the hand surface away from
                                        # penetrating object vertices.
                                        _foho_f32_collision_loss = (
                                            -_foho_f32_min_dist.mean()
                                        )

                                    if _foho_f32_stage_a_trans_hand is not None:
                                        _foho_f32_anchor_translation_loss = (
                                            trans_hand
                                            - _foho_f32_stage_a_trans_hand
                                        ).pow(2).mean()

                                    if (
                                        _foho_f31_rotation_delta_hand is not None
                                        and _foho_f32_stage_a_rotation_delta_hand
                                        is not None
                                    ):
                                        _foho_f32_anchor_rotation_loss = (
                                            _foho_f31_rotation_delta_hand
                                            - _foho_f32_stage_a_rotation_delta_hand
                                        ).pow(2).mean()

                            if _foho_f32_enabled:
                                _foho_f32_contact_weight_now = (
                                    _foho_f3_contact_weight
                                    if k < _foho_f32_stage_a_steps
                                    else _foho_f32_contact_preserve_weight
                                )
                                total_loss = (
                                    _foho_f32_contact_weight_now
                                    * _foho_f3_contact_loss
                                    + _foho_f3_2d_weight
                                    * loss_2d_kps
                                    + _foho_f3_trans_reg_weight
                                    * _foho_f3_translation_delta_loss
                                    + _foho_f32_collision_weight
                                    * _foho_f32_collision_loss
                                    + _foho_f32_anchor_trans_weight
                                    * _foho_f32_anchor_translation_loss
                                    + _foho_f32_anchor_rot_weight
                                    * _foho_f32_anchor_rotation_loss
                                )
                                if k % _foho_f3_log_every == 0:
                                    print(
                                        "[FOHO_F3_2] "
                                        f"k={k}, "
                                        f"contact_loss={_foho_f3_contact_loss.item():.8f}, "
                                        f"collision_loss={_foho_f32_collision_loss.item():.8f}, "
                                        f"object_vertices_inside_hand={object_vertices_inside_hand}, "
                                        f"anchor_trans={_foho_f32_anchor_translation_loss.item():.8f}, "
                                        f"anchor_rot={_foho_f32_anchor_rotation_loss.item():.8f}, "
                                        f"total_loss={total_loss.item():.8f}"
                                    )
                            elif _foho_f3_enabled:
                                total_loss = (
                                    _foho_f3_contact_weight
                                    * _foho_f3_contact_loss
                                    + _foho_f3_2d_weight
                                    * loss_2d_kps
                                    + _foho_f3_trans_reg_weight
                                    * _foho_f3_translation_delta_loss
                                )
                            else:
                                total_loss = (
                                    w_intersection * loss_intersection +
                                    10 * distance_loss +
                                    _foho_f2_weight * screen_lid_contact_loss +
                                    10 * loss_normal_hoi +
                                    10 * loss_disp_hoi +
                                    10 * loss_silhouette_hoi +
                                    1e-3 * obj_verts_loss_3 +
                                    1 * obj_loss_3 +
                                    1e-3 * loss_obj_reg +
                                    1e-3 * hand_loss
                                )

                            if (
                                _foho_f3_enabled
                                and k % _foho_f3_log_every == 0
                            ):
                                print(
                                    "[FOHO_F3] "
                                    f"k={k}, "
                                    f"contact_loss="
                                    f"{_foho_f3_contact_loss.item():.8f}, "
                                    f"tip_mean_m="
                                    f"{_foho_f3_tip_mean_m.item():.6f}, "
                                    f"tip_min_m="
                                    f"{_foho_f3_tip_min_m.item():.6f}, "
                                    f"trans_delta_loss="
                                    f"{_foho_f3_translation_delta_loss.item():.8f}, "
                                    f"total_loss={total_loss.item():.8f}"
                                )

                            if torch.isnan(total_loss):
                                print('Total loss is NaN') # investigate from which loss NaN comes and why that loss is NaN
                                break

                            if k % 10 == 0:
                                loss_str = (
                                    f"Opt step {k}, object loss: {obj_loss_3.item()}, "
                                    f"loss_intersection: {loss_intersection.item()}, "
                                    f"loss_normal_hoi: {loss_normal_hoi.item()}, "
                                    f"loss_disp: {loss_disp_hoi.item()}, "
                                    f"distance_loss: {distance_loss.item()}, "
                                    f"screen_lid_contact_loss: "
                                    f"{screen_lid_contact_loss.item()}, "
                                    f"screen_lid_patch_mean_m: "
                                    f"{screen_lid_patch_mean_m.item()}, "
                                    f"screen_lid_patch_min_m: "
                                    f"{screen_lid_patch_min_m.item()}, "
                                    f"total_hand_loss: {hand_loss.item()}"
                                )
                                if loss_log_file:
                                    loss_log_file.write(loss_str + '\n')
                                print(loss_str)         

                            total_loss.backward()
                            _foho_active_optimizer.step()

                            if _foho_f31_enabled:
                                with torch.no_grad():
                                    _foho_f31_norm = torch.linalg.vector_norm(
                                        _foho_f31_rotation_delta_hand
                                    )
                                    if _foho_f31_norm > _foho_f31_max_rotation_rad:
                                        _foho_f31_rotation_delta_hand.mul_(
                                            _foho_f31_max_rotation_rad
                                            / _foho_f31_norm
                                        )

                            if _foho_f3_enabled:
                                with torch.no_grad():
                                    _foho_f3_delta = (
                                        trans_hand
                                        - _foho_f3_trans_hand_anchor
                                    )
                                    _foho_f3_delta_norm = (
                                        torch.linalg.vector_norm(
                                            _foho_f3_delta
                                        )
                                    )
                                    if (
                                        _foho_f3_delta_norm.item()
                                        > _foho_f3_max_translation_delta_m
                                    ):
                                        _foho_f3_scale = (
                                            _foho_f3_max_translation_delta_m
                                            / torch.clamp(
                                                _foho_f3_delta_norm,
                                                min=1e-12,
                                            )
                                        )
                                        trans_hand.copy_(
                                            _foho_f3_trans_hand_anchor
                                            + _foho_f3_delta
                                            * _foho_f3_scale
                                        )
                            # FOHO_F3_STAGE1_END

                    
                    noise_pred_obj = noise_pred_obj.detach().clone()
                    scale_hand = scale_hand.detach().clone()
                    trans_hand = trans_hand.detach().clone()
                    rotation_hand = rotation_hand.detach().clone()
                    scale_obj = scale_obj.detach().clone()
                    trans_obj = trans_obj.detach().clone()
                    rotation_obj = rotation_obj.detach().clone()

            obj_latents = self.scheduler.step(noise_pred_obj, t, obj_latents).prev_sample

            with torch.no_grad():
                if i >= handopt_start_step:
                    RT_debug = torch.eye(4, device=device)
                    # FOHO_F3_1_ZERO_UPDATE_ROTATION_GUARD_V3
                    if _foho_f31_enabled and _foho_f31_rotation_delta_hand is None:
                        _foho_f31_rotation_delta_hand = torch.zeros(
                            3,
                            device=trans_hand.device,
                            dtype=trans_hand.dtype,
                            requires_grad=True,
                        )
                    if _foho_f31_enabled:
                        _foho_f31_debug_base_rot = quaternion_to_matrix(
                            rotation_hand
                        ).float().squeeze(0)
                        _foho_f31_debug_delta_rot = axis_angle_to_matrix(
                            _foho_f31_rotation_delta_hand.unsqueeze(0)
                        ).squeeze(0)
                        RT_debug[:3, :3] = (
                            _foho_f31_debug_delta_rot @ _foho_f31_debug_base_rot
                        )
                    else:
                        RT_debug[:3, :3] = quaternion_to_matrix(rotation_hand).float().unsqueeze(0)
                    RT_debug[:3, 3] = trans_hand
                    debug_mano = transform_mesh_around_center_w_scale(mano_mesh_moge, RT_debug, scale_hand)

                debug_obj_latent_x1 = self.scheduler.step_final(noise_pred_obj, t, obj_latents)
                
                # if we are at the final step, decode the latents in a higher resolution
                if i == num_inference_steps - 1:
                    octree_res = int(os.environ.get("FOHO_FINAL_OCTREE_RES", "384"))
                    print(f"[FOHO_LOW_MEM] final octree_res={octree_res}")
                    bounds = 1.10
                    bounds = [-bounds, -bounds, -bounds, bounds, bounds, bounds]
                    bbox_min = np.array(bounds[0:3])
                    bbox_max = np.array(bounds[3:6])
                    xyz_samples, grid_size, _ = generate_dense_grid_points(
                        bbox_min=bbox_min,
                        bbox_max=bbox_max,
                        octree_depth=5,
                        octree_resolution=octree_res,
                        indexing="ij")
                    xyz_samples = torch.FloatTensor(xyz_samples)
                    xyz_samples = xyz_samples.to(device)
                    flexi = knc.FlexiCubes(device=device)
                    voxel_vertices, cube_indices = flexi.construct_voxel_grid(octree_res)

                debug_obj_pred_sdf = latent2sdf(debug_obj_latent_x1, xyz_samples, grid_size, self.vae, device)
                debug_obj_verts, debug_obj_faces, _ = flexi(xyz_samples, debug_obj_pred_sdf[0].flatten(), cube_indices, octree_res)

                if debug_obj_verts.shape[0] == 0:
                    print('Invalid mesh detected, aborting step!')
                    continue # skip step

                debug_tex_obj = torch.zeros_like(debug_obj_verts)
                debug_tex_obj[:, 2] = 1.0 # blue
                debug_tex_obj = TexturesVertex(verts_features=[debug_tex_obj])
                debug_obj_mesh = Meshes(verts=[debug_obj_verts], faces=[debug_obj_faces], textures=debug_tex_obj).to(device)
                debug_obj_mesh.textures = None
                try:
                    from pytorch3d.io import IO as _FOHO_IO
                    _foho_step_dir = save_dir if 'save_dir' in dir() else None
                    if _foho_step_dir:
                        _FOHO_IO().save_mesh(debug_obj_mesh, f"{_foho_step_dir}/FOHO_DEBUG_PERSTEP_OBJ_EXPORT_step{i}.ply")
                except Exception as _e:
                    print(f"[FOHO_DEBUG_PERSTEP_OBJ_EXPORT_FAIL] step {i}: {repr(_e)}")
                # FOHO debug: save raw final extracted object mesh before coordinate transforms.
                try:
                    IO().save_mesh(debug_obj_mesh, f"{save_dir}/debug_obj_before_hunyuan2moge.ply")
                except Exception as _e:
                    print("[FOHO_DEBUG] failed to save debug_obj_before_hunyuan2moge:", repr(_e))
                debug_transformed_obj_mesh = transform_hunyuan2moge(debug_obj_mesh, T_h2m) # putting the obj in moge space
                # FOHO debug: save after Hunyuan-to-MoGe transform.
                try:
                    IO().save_mesh(debug_transformed_obj_mesh, f"{save_dir}/debug_obj_after_hunyuan2moge.ply")
                except Exception as _e:
                    print("[FOHO_DEBUG] failed to save debug_obj_after_hunyuan2moge:", repr(_e))
                RT_obj_debug = torch.eye(4, device=device)
                RT_obj_debug[:3, :3] = quaternion_to_matrix(rotation_obj).float().unsqueeze(0)
                RT_obj_debug[:3, 3] = trans_obj
                debug_transformed_obj_mesh = transform_mesh_around_center_w_scale(debug_transformed_obj_mesh, RT_obj_debug, scale_obj) 
                
                # FOHO_GATE_A_FIXED_OBJECT_FINAL_EXPORT
                # The optimization used fixed Gate A geometry, so the returned
                # guidance object must use the same geometry rather than a fresh
                # latent decode.
                if _foho_fixed_obj_mesh_cached is not None:
                    _foho_final_fixed_moge = transform_hunyuan2moge(
                        _foho_fixed_obj_mesh_cached,
                        T_h2m,
                    )
                    debug_transformed_obj_mesh = transform_mesh_around_center_w_scale(
                        _foho_final_fixed_moge,
                        RT_obj_debug,
                        scale_obj,
                    )
                    print(
                        "[FOHO_GATE_A_FIXED_OBJECT] final export uses frozen Gate A mesh"
                    )
                # FOHO debug: save after final object RT/scale transform.
                try:
                    IO().save_mesh(debug_transformed_obj_mesh, f"{save_dir}/debug_obj_after_final_rt_scale.ply")
                except Exception as _e:
                    print("[FOHO_DEBUG] failed to save debug_obj_after_final_rt_scale:", repr(_e))

                # render normals and depth in moge space
                if i >= handopt_start_step:
                    # FOHO fix: join_meshes_as_batch requires matching texture
                    # types across meshes. Strip textures for this debug-only
                    # visualization join rather than crash the whole run --
                    # this scene is not used downstream for the actual
                    # guidance_out result, only for optional debug preview.
                    try:
                        debug_hoi_mesh = join_meshes_as_scene([debug_mano, debug_transformed_obj_mesh])
                    except ValueError as _e:
                        print(f"[FOHO_DEBUG] texture mismatch in debug join, "
                              f"stripping textures and retrying: {_e!r}")
                        debug_mano_notex = debug_mano.clone()
                        debug_mano_notex.textures = None
                        debug_obj_notex = debug_transformed_obj_mesh.clone()
                        debug_obj_notex.textures = None
                        debug_hoi_mesh = join_meshes_as_scene([debug_mano_notex, debug_obj_notex])
                else:
                    debug_hoi_mesh = debug_transformed_obj_mesh

                if debugging:
                    with torch.cuda.amp.autocast(enabled=False):
                        debug_rendered_normal, debug_rendered_disp = render_normal_and_disparity(renderer, debug_hoi_mesh)
                    plot_in_grid(debug_rendered_normal, moge_normal, save_path=f'{save_dir}/rendered_normal_t{i}.png')

                    if debugging and save_dir:
                        if i == num_inference_steps - 1:
                            IO().save_mesh(debug_mano, f"{save_dir}/final_hand_mesh.ply")
                            IO().save_mesh(debug_transformed_obj_mesh, f"{save_dir}/final_obj_mesh.ply")
                        elif i == 14:
                            IO().save_mesh(debug_mano, f"{save_dir}/guidance_step_{i}_hand_mesh.ply")
                            IO().save_mesh(debug_transformed_obj_mesh, f"{save_dir}/guidance_step_{i}_obj_mesh.ply")

        if loss_log_file:
            loss_log_file.close()
        return debug_transformed_obj_mesh, debug_mano
