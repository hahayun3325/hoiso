from pathlib import Path
import argparse

def to_numpy(value):
    if hasattr(value, 'detach'):
        value = value.detach().cpu()
    if hasattr(value, 'numpy'):
        value = value.numpy()
    return value

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    parser.add_argument('--out-mask', required=True)
    parser.add_argument('--out-overlay', required=True)
    parser.add_argument('--prompt', default='laptop')
    parser.add_argument('--sam-type', default='sam2.1_hiera_large')
    parser.add_argument('--box-threshold', type=float, default=0.30)
    parser.add_argument('--text-threshold', type=float, default=0.25)
    parser.add_argument('--positive-roi', nargs=4, type=int)
    args = parser.parse_args()

    try:
        import numpy as np
        from PIL import Image
        from lang_sam import LangSAM

        image_path = Path(args.image)
        mask_path = Path(args.out_mask)
        overlay_path = Path(args.out_overlay)

        if not image_path.is_file():
            print(f'[HOLD] LSAM_INPUT_MISSING={image_path}')
            return

        original = Image.open(image_path).convert('RGB')
        width, height = original.size
        roi = args.positive_roi or [0, 0, width, height]
        x1, y1, x2, y2 = roi

        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            print(f'[HOLD] LSAM_INVALID_POSITIVE_ROI={roi} image_size={(width, height)}')
            return

        cropped = original.crop((x1, y1, x2, y2))
        model = LangSAM(sam_type=args.sam_type)
        result = model.predict(
            [cropped],
            [args.prompt],
            box_threshold=args.box_threshold,
            text_threshold=args.text_threshold,
        )[0]

        masks = to_numpy(result.get('masks', []))
        if masks is None or len(masks) == 0:
            print('[HOLD] LSAM_NO_MASKS_RETURNED')
            return

        masks = np.asarray(masks)
        masks = np.squeeze(masks)
        if masks.ndim == 2:
            masks = masks[None, ...]

        scores = result.get('scores')
        if scores is not None and len(scores) == len(masks):
            scores = np.asarray(to_numpy(scores)).reshape(-1)
            selected_index = int(np.argmax(scores))
            selection = f'highest_score:{float(scores[selected_index]):.6f}'
        else:
            areas = masks.reshape(len(masks), -1).sum(axis=1)
            selected_index = int(np.argmax(areas))
            selection = f'largest_area:{int(areas[selected_index])}'

        selected = masks[selected_index].astype(bool)
        full_mask = np.zeros((height, width), dtype=np.uint8)
        full_mask[y1:y2, x1:x2] = selected.astype(np.uint8) * 255

        mask_path.parent.mkdir(parents=True, exist_ok=True)
        overlay_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(full_mask, mode='L').save(mask_path)

        image_array = np.asarray(original).copy()
        active = full_mask > 0
        image_array[active] = (
            0.55 * image_array[active] + 0.45 * np.array([0, 255, 0])
        ).astype(np.uint8)
        Image.fromarray(image_array).save(overlay_path)

        print(f'[PASS] LSAM_MASK_WRITTEN={mask_path}')
        print(f'[PASS] LSAM_OVERLAY_WRITTEN={overlay_path}')
        print(f'[INFO] LSAM_SELECTION={selection}')
        print(f'[INFO] LSAM_POSITIVE_ROI={roi}')
    except Exception as error:
        print(f'[HOLD] LSAM_MASK_GENERATION_FAILED={type(error).__name__}: {error}')

if __name__ == '__main__':
    main()
