"""Configuration for the FOHO guidance diffusion model."""

from __future__ import annotations

import os




def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return float(value)


class OptimizationConfig:
    def __init__(self):
        self.obj_guidance_scale = _env_float("FOHO_OBJ_GUIDANCE_SCALE", 5.0)
        self.batch_size = 1  # Not supporting batch processing for now

        # Optimization steps
        self.optimization_steps_hand = _env_int("FOHO_OPT_STEPS_HAND", 200)
        self.optimization_steps_joint = _env_int("FOHO_OPT_STEPS_JOINT", 50)
        self.optimization_steps_scale = _env_int("FOHO_OPT_STEPS_SCALE", 100)
        self.num_inference_steps = _env_int("FOHO_NUM_INFERENCE_STEPS", 20)
        self.guidance_start_step = self.num_inference_steps // 2
        self.handopt_start_step = self.guidance_start_step - 1
        self.guidance_end_step = self.num_inference_steps

        # Learning rates
        self.phase1_hand_lrs = {"scale": 1e-2, "trans": 1e-2, "rot": 0.5}
        self.phase2_hand_lrs = {"scale": 1e-4, "trans": 1e-4, "rot": 1e-2}
        self.obj_2half_lrs = {"scale": 1e-2, "trans": 1e-2, "rot": 1e-2}
        self.obj_lrs = {"scale": 5e-2, "trans": 1e-2, "rot": 1e-2}
        self.noise_obj_lr1 = 1e-4
        self.noise_obj_lr1 = float(os.environ.get('FOHO_NOISE_OBJ_LR1', self.noise_obj_lr1))
        self.noise_obj_lr2 = 1e-2
        self.noise_obj_lr2 = float(os.environ.get('FOHO_NOISE_OBJ_LR2', self.noise_obj_lr2))

        # Losses
        self.use_intersection_loss = True

    def __call__(self):
        return self

