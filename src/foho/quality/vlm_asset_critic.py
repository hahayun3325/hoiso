from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from PIL import Image


def extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("VLM response did not contain a JSON object")
    return json.loads(cleaned[start:end + 1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    request_path = Path(args.request)
    output_path = Path(args.output)
    if not request_path.is_file():
        print(f"[HOLD] V3_VLM_REQUEST_MISSING={request_path}")
        return
    if not os.environ.get("GEMINI_API_KEY"):
        print("[HOLD] V3_VLM_API_KEY_NOT_AVAILABLE")
        return

    request = json.loads(request_path.read_text())
    image_paths = [Path(path) for path in request["images_in_order"]]
    missing = [str(path) for path in image_paths if not path.is_file()]
    if missing:
        print(f"[HOLD] V3_VLM_IMAGE_MISSING={missing}")
        return

    prompt = (
        "You are the strict visual asset critic in a 3D hand-object "
        "reconstruction pipeline. Evaluate the images in the listed order. "
        "Apply every veto rule before scoring. Return only one JSON object "
        "matching response_schema. Do not infer PASS when evidence is unclear.\n\n"
        + json.dumps(request, indent=2)
    )
    images = [Image.open(path).convert("RGB") for path in image_paths]
    raw_text = None
    backend = None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model=args.model,
            contents=[prompt, *images],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        raw_text = response.text
        backend = "google.genai"
    except ImportError:
        try:
            import google.generativeai as legacy_genai

            legacy_genai.configure(api_key=os.environ["GEMINI_API_KEY"])
            model = legacy_genai.GenerativeModel(
                model_name=args.model,
                generation_config={
                    "temperature": 0,
                    "response_mime_type": "application/json",
                },
            )
            response = model.generate_content([prompt, *images])
            raw_text = response.text
            backend = "google.generativeai"
        except ImportError:
            print("[HOLD] V3_VLM_GEMINI_SDK_NOT_AVAILABLE")
            return
    except Exception as error:
        print(f"[HOLD] V3_VLM_CALL_FAILED={type(error).__name__}: {error}")
        return

    try:
        result = extract_json(raw_text or "")
    except Exception as error:
        print(f"[HOLD] V3_VLM_RESPONSE_INVALID={type(error).__name__}: {error}")
        return

    result["_audit"] = {
        "model": args.model,
        "backend": backend,
        "request": str(request_path),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[PASS] V3_VLM_RESPONSE_WRITTEN={output_path}")
    print(f"[INFO] V3_VLM_RAW_DECISION={result.get('decision')}")


if __name__ == "__main__":
    main()
