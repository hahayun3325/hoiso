from pathlib import Path
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    source = Path(args.input)
    destination = Path(args.output)

    try:
        from PIL import Image
        from hy3dgen.rembg import BackgroundRemover

        if not source.is_file() or source.stat().st_size == 0:
            print(f'[HOLD] HUNYUAN_PREP_SOURCE_MISSING={source}')
            return

        image = Image.open(source).convert('RGB')
        prepared = BackgroundRemover()(image)
        destination.parent.mkdir(parents=True, exist_ok=True)
        prepared.save(destination)

        check = Image.open(destination)
        alpha_bbox = check.getchannel('A').getbbox() if 'A' in check.getbands() else None
        print(f'[INFO] HUNYUAN_PREP_MODE={check.mode}')
        print(f'[INFO] HUNYUAN_PREP_SIZE={check.size}')
        print(f'[INFO] HUNYUAN_PREP_ALPHA_BBOX={alpha_bbox}')
        if destination.is_file() and destination.stat().st_size > 0:
            print(f'[PASS] HUNYUAN_PREPARED_INPUT_WRITTEN={destination}')
        else:
            print(f'[HOLD] HUNYUAN_PREPARED_INPUT_EMPTY={destination}')
    except Exception as error:
        print(f'[HOLD] HUNYUAN_PREP_FAILED={type(error).__name__}: {error}')


if __name__ == '__main__':
    main()
