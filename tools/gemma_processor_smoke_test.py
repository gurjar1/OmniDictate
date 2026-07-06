from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.base import PromptMode, TargetAppContext, TranscriptionRequest, VisualContextSnapshot, VisualSource
from engines.prompt_modes import build_gemma_messages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Processor-only Gemma 4 multimodal smoke test.")
    parser.add_argument(
        "--model-ref",
        default=str(ROOT / "smoke_test_assets" / "models" / "gemma-4-E2B-it"),
        help="Local processor directory or model id.",
    )
    parser.add_argument("--allow-remote", action="store_true", help="Allow downloading processor metadata.")
    return parser.parse_args()


def build_request(include_image: bool) -> TranscriptionRequest:
    visual_context = VisualContextSnapshot()
    if include_image:
        visual_context = VisualContextSnapshot(
            source=VisualSource.ATTACHED_IMAGE,
            images=[Image.new("RGB", (128, 96), "white")],
            description="Images: synthetic.png",
            metadata={"attachment_names": "synthetic.png"},
        )

    return TranscriptionRequest(
        audio=np.zeros(16000, dtype=np.float32),
        sample_rate=16000,
        language="en",
        prompt_mode=PromptMode.CONTEXT if include_image else PromptMode.PURE,
        visual_context=visual_context,
        target_app=TargetAppContext(title="Processor smoke", process_name="test"),
        max_new_tokens=32,
    )


def run_case(processor, include_image: bool) -> None:
    request = build_request(include_image)
    messages = build_gemma_messages(request)
    prompt_text = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    if "<|audio|>" not in prompt_text:
        raise AssertionError("Gemma prompt did not include the audio token.")

    kwargs = {
        "text": prompt_text,
        "audio": np.expand_dims(request.audio, axis=0),
        "return_tensors": "pt",
    }
    if include_image:
        kwargs["images"] = request.visual_context.images

    inputs = processor(**kwargs)
    for required_key in ["input_ids", "attention_mask", "input_features"]:
        if required_key not in inputs:
            raise AssertionError(f"Processor output missing {required_key}.")
    if include_image and "pixel_values" not in inputs:
        raise AssertionError("Processor output missing pixel_values for image case.")


def main() -> int:
    args = parse_args()
    model_ref = Path(args.model_ref)
    if not args.allow_remote and not model_ref.exists():
        print(f"SKIP: local Gemma processor metadata not found at {model_ref}")
        return 0

    from transformers import AutoProcessor

    processor = AutoProcessor.from_pretrained(
        str(model_ref) if model_ref.exists() else args.model_ref,
        local_files_only=not args.allow_remote,
    )
    run_case(processor, include_image=False)
    run_case(processor, include_image=True)
    print("Gemma processor smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
