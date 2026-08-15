from pathlib import Path
import argparse
import inspect

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--model-path', default='tencent/Hunyuan3D-2')
    parser.add_argument('--subfolder', default='hunyuan3d-dit-v2-0')
    parser.add_argument('--device', default='cuda')
    parser.add_argument('--steps', type=int, default=6)
    parser.add_argument('--octree-resolution', type=int, default=192)
    parser.add_argument('--num-chunks', type=int, default=8000)
    parser.add_argument('--seed', type=int, default=1234)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()

    image_path = Path(args.image)
    output_path = Path(args.out)

    try:
        import torch
        from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

        call_signature = inspect.signature(
            Hunyuan3DDiTFlowMatchingPipeline.__call__
        )
        print(f'[INFO] HUNYUAN_CALL_SIGNATURE={call_signature}')

        if args.preflight_only:
            print('[PASS] HUNYUAN_DRYRUN_PREFLIGHT_ONLY')
            return

        if not image_path.is_file():
            print(f'[HOLD] HUNYUAN_INPUT_MISSING={image_path}')
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)

        pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
            args.model_path,
            subfolder=args.subfolder,
            use_safetensors=True,
            device=args.device,
        )
        generator = torch.Generator(device=args.device).manual_seed(args.seed)
        mesh = pipeline(
            image=str(image_path),
            num_inference_steps=args.steps,
            octree_resolution=args.octree_resolution,
            num_chunks=args.num_chunks,
            generator=generator,
            output_type='trimesh',
        )[0]
        mesh.export(output_path)

        if output_path.is_file() and output_path.stat().st_size > 0:
            print(f'[PASS] HUNYUAN_OBJECT_DRYRUN_WRITTEN={output_path}')
        else:
            print(f'[HOLD] HUNYUAN_OBJECT_DRYRUN_EMPTY={output_path}')
    except Exception as error:
        print(f'[HOLD] HUNYUAN_OBJECT_DRYRUN_FAILED={type(error).__name__}: {error}')

if __name__ == '__main__':
    main()
