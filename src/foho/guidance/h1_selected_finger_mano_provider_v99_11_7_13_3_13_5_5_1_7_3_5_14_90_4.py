import hashlib
import torch
from torch import nn
from pytorch3d.transforms import axis_angle_to_matrix

class H1SelectedFingerMANOProvider(nn.Module):
    SELECTED_ROWS=(0,1,2,3,4,5)
    PARAMETER_NAME='selected_so3_residual'

    def __init__(self, mano_layer, base_global_orient, base_hand_pose, betas, bridge_linear, bridge_translation):
        super().__init__()
        if tuple(base_hand_pose.shape)!=(1,15,3,3): raise ValueError('base_hand_pose_must_be_1x15x3x3')
        if tuple(base_global_orient.shape)!=(1,1,3,3): raise ValueError('global_orient_must_be_1x1x3x3')
        if tuple(betas.shape)!=(1,10): raise ValueError('betas_must_be_1x10')
        self.mano_layer=mano_layer
        for p in self.mano_layer.parameters(): p.requires_grad_(False)
        self.register_buffer('base_global_orient',base_global_orient.detach().clone())
        self.register_buffer('base_hand_pose',base_hand_pose.detach().clone())
        self.register_buffer('base_betas',betas.detach().clone())
        self.register_buffer('bridge_linear',bridge_linear.detach().clone().reshape(3,3))
        self.register_buffer('bridge_translation',bridge_translation.detach().clone().reshape(3))
        self.selected_so3_residual=nn.Parameter(torch.zeros(6,3,dtype=base_hand_pose.dtype,device=base_hand_pose.device))

    def trainable_named_parameters_exact(self):
        return [(self.PARAMETER_NAME,self.selected_so3_residual)]

    def composed_hand_pose(self):
        residual_R=axis_angle_to_matrix(self.selected_so3_residual.reshape(-1,3)).reshape(6,3,3)
        pose=self.base_hand_pose.clone()
        pose[:,self.SELECTED_ROWS]=residual_R @ self.base_hand_pose[:,self.SELECTED_ROWS]
        return pose

    def local_vertices(self):
        return self.mano_layer(global_orient=self.base_global_orient,hand_pose=self.composed_hand_pose(),
            betas=self.base_betas,pose2rot=False).vertices

    def forward(self):
        local=self.local_vertices()
        return local @ self.bridge_linear.transpose(0,1) + self.bridge_translation

    def snapshot(self):
        return {'selected_so3_residual':self.selected_so3_residual.detach().clone(),
            'requires_grad':bool(self.selected_so3_residual.requires_grad)}

    def restore(self,snapshot):
        with torch.no_grad(): self.selected_so3_residual.copy_(snapshot['selected_so3_residual'])
        self.selected_so3_residual.requires_grad_(bool(snapshot['requires_grad']))

    def frozen_digest(self):
        h=hashlib.sha256()
        for value in (self.base_global_orient,self.base_hand_pose,self.base_betas,self.bridge_linear,self.bridge_translation):
            h.update(value.detach().cpu().contiguous().numpy().tobytes())
        return h.hexdigest()
