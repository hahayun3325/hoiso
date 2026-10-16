"""Build Hunyuan from explicit local safetensors and configuration files.

The three CPU component loads follow the Q9 diagnostic's load/convert/release
order. Pipeline assembly and inference require separate runtime validation.
"""
from __future__ import annotations

import copy
from pathlib import Path


TARGETS = {
    'model': 'hy3dgen.shapegen.models.Hunyuan3DDiT',
    'vae': 'hy3dgen.shapegen.models.ShapeVAE',
    'conditioner': 'hy3dgen.shapegen.models.SingleImageEncoder',
    'scheduler': 'hy3dgen.shapegen.schedulers.FlowMatchEulerDiscreteScheduler',
    'image_processor': 'hy3dgen.shapegen.preprocessors.ImageProcessorV2',
    'pipeline': 'hy3dgen.shapegen.pipelines.Hunyuan3DDiTFlowMatchingPipeline',
}


def local_inputs(config_path, checkpoint_path):
    """Accept cache symlinks, but require both resolved inputs to be nonempty files."""
    if not config_path or not checkpoint_path:
        raise ValueError('Local Hunyuan loading requires both config_path and checkpoint_path')
    result = []
    for name, value in [('configuration', config_path), ('checkpoint', checkpoint_path)]:
        path = Path(value).expanduser().resolve(strict=True)
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'Hunyuan {name} must be a nonempty local file: {path}')
        result.append(str(path))
    if Path(result[0]).stat().st_size > 65536:
        raise ValueError('Hunyuan configuration exceeds 64 KiB')
    return tuple(result)


def validate_config(config):
    if not isinstance(config, dict) or set(config) != set(TARGETS):
        raise ValueError('Expected the six Hunyuan model configuration sections')
    for name, target in TARGETS.items():
        section = config[name]
        if (not isinstance(section, dict) or section.get('target') != target
                or set(section) - {'target', 'params'}
                or not isinstance(section.get('params', {}), dict)):
            raise ValueError(f'Unsupported Hunyuan configuration section: {name}')
    if config['pipeline'].get('params'):
        raise ValueError('Pipeline parameter overrides are not supported')


def assemble(config, checkpoint_path, device, api):
    """Injectable core; fixed constructors, strict CPU loads, then pipeline assembly."""
    validate_config(config)
    torch = api['torch']
    weights = api['load_file'](checkpoint_path, device='cpu')
    objects = {}
    groups = ('model', 'vae', 'conditioner')
    try:
        if (not isinstance(weights, dict) or not weights
                or {name.partition('.')[0] for name in weights} != set(groups)):
            raise ValueError('Checkpoint must contain model, vae and conditioner tensors only')
        for name, tensor in weights.items():
            if (tensor.device.type != 'cpu' or tensor.dtype != torch.float16
                    or not bool(torch.isfinite(tensor).all().item())):
                raise ValueError(f'Expected finite CPU float16 checkpoint tensor: {name}')
        tensor = None
        with torch.no_grad():
            for group in groups:
                obj = api[group](**copy.deepcopy(config[group].get('params', {})))
                state = {name[len(group)+1:]:value for name, value in weights.items()
                         if name.startswith(group + '.')}
                actual = obj.state_dict()
                if (set(actual) != set(state) or any(
                        actual[name].shape != value.shape or actual[name].device.type != 'cpu'
                        for name, value in state.items())):
                    raise ValueError(f'Constructed checkpoint schema differs: {group}')
                actual = None
                receipt = obj.load_state_dict(state, strict=True)
                if receipt.missing_keys or receipt.unexpected_keys:
                    raise ValueError(f'Strict checkpoint load failed: {group}')
                obj.to(device='cpu', dtype=torch.float16)
                obj.eval()
                actual = obj.state_dict()
                if set(actual) != set(state) or any(
                    actual[name].device.type != 'cpu' or actual[name].dtype != torch.float16
                    or not torch.equal(actual[name], value) for name, value in state.items()
                ):
                    raise ValueError(f'Loaded checkpoint values differ: {group}')
                objects[group] = obj
                actual = None
                state.clear()
                for name in list(weights):
                    if name.startswith(group + '.'):
                        del weights[name]
            # Construct on CPU first. The installed pipeline's to() returns None.
            pipeline = api['pipeline'](
                **objects,
                scheduler=api['scheduler'](**copy.deepcopy(config['scheduler'].get('params', {}))),
                image_processor=api['image_processor'](**copy.deepcopy(config['image_processor'].get('params', {}))),
                device='cpu', dtype=torch.float16,
            )
            if device != 'cpu':
                pipeline.to(device=device)
            return pipeline
    finally:
        if isinstance(weights, dict):
            weights.clear()
        objects.clear()


def build_local_pipeline(config_path, checkpoint_path, *, device='cuda'):
    config_path, checkpoint_path = local_inputs(config_path, checkpoint_path)
    import yaml
    with open(config_path, encoding='utf-8') as handle:
        config = yaml.safe_load(handle)
    validate_config(config)
    import torch
    from safetensors.torch import load_file
    from hy3dgen.shapegen.models import Hunyuan3DDiT, ShapeVAE, SingleImageEncoder
    from hy3dgen.shapegen.schedulers import FlowMatchEulerDiscreteScheduler
    from hy3dgen.shapegen.preprocessors import ImageProcessorV2
    from hy3dgen.shapegen.pipelines import Hunyuan3DDiTFlowMatchingPipeline
    api = dict(torch=torch, load_file=load_file, model=Hunyuan3DDiT, vae=ShapeVAE,
               conditioner=SingleImageEncoder, scheduler=FlowMatchEulerDiscreteScheduler,
               image_processor=ImageProcessorV2, pipeline=Hunyuan3DDiTFlowMatchingPipeline)
    return assemble(config, checkpoint_path, device, api)
