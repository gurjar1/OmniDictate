from __future__ import annotations

import json
import re
from typing import Any

from .base import PreviewPayload, PromptMode, TargetAppContext, TranscriptionRequest


PROMPT_MODE_LABELS = {
    PromptMode.PURE: "Pure transcription",
    PromptMode.CONTEXT: "Context-enhanced",
    PromptMode.REASONING: "Full reasoning",
}


def build_target_app_hint(target_app: TargetAppContext) -> str:
    process_name = (target_app.process_name or "").lower()
    title = target_app.title or ""

    if any(name in process_name for name in ["code", "devenv", "pycharm", "terminal", "cmd", "powershell"]):
        return "Target application looks like a code editor or terminal. Preserve casing, punctuation, file paths, stack traces, and code identifiers exactly."
    if any(name in process_name for name in ["outlook", "mail", "thunderbird"]):
        return "Target application looks like email. Favor polished complete sentences and professional tone."
    if any(name in process_name for name in ["slack", "teams", "discord", "whatsapp"]):
        return "Target application looks like chat. Favor concise natural messages unless speech clearly asks for a longer reply."
    if any(name in process_name for name in ["chrome", "msedge", "firefox", "acrobat"]):
        return "Target application looks like a browser or document viewer. Expect visible slide titles, PDFs, forms, or web UI labels to matter."
    if title:
        return f"Foreground window title: {title}"
    return ""


def _visual_metadata_hint(request: TranscriptionRequest) -> str:
    metadata = request.visual_context.metadata
    if not metadata:
        return ""
    details = []
    for key in ["window_title", "process_name", "attachment_names", "screen_target"]:
        value = metadata.get(key)
        if value:
            details.append(f"{key}: {value}")
    return "\n".join(details)


def build_system_prompt(request: TranscriptionRequest) -> str:
    app_hint = build_target_app_hint(request.target_app)
    visual_hint = _visual_metadata_hint(request)

    if request.prompt_mode == PromptMode.PURE:
        base = (
            "You are OmniDictate. Transcribe only the spoken audio in its original language. "
            "Ignore all visual input and prior assistant commentary. "
            "Output only the final transcription text. Use digits for numbers. "
            "Do not add explanations, labels, or summaries."
        )
    elif request.prompt_mode == PromptMode.CONTEXT:
        base = (
            "You are OmniDictate. Audio is the primary source of truth. "
            "Use visible context only to resolve ambiguity in names, numbers, dates, "
            "UI labels, filenames, technical terms, code identifiers, and visible document text. "
            "Do not add content not supported by speech or visible context. "
            "Output only the final transcription text."
        )
    else:
        base = (
            "You are OmniDictate Assist. Use audio and visual context together to produce the text "
            "the user most likely wants inserted into the active application. "
            "You may complete or reformulate unfinished speech only when strongly supported by speech and visible context. "
            "If confidence is low, stay close to the literal transcript. "
            "Return a JSON object with keys typed_text, suggestions, and rationale."
        )

    extras = [hint for hint in [app_hint, visual_hint] if hint]
    if extras:
        return base + "\n\n" + "\n".join(extras)
    return base


def build_user_instruction(request: TranscriptionRequest) -> str:
    if request.transcript_text:
        transcript_block = f"Draft transcript from faster-whisper:\n{request.transcript_text.strip()}\n\n"
        if request.prompt_mode == PromptMode.REASONING:
            return (
                transcript_block
                + "Use this transcript as the primary speech source and the visual context as supporting evidence. "
                "Respond with JSON only, for example: "
                '{"typed_text": "...", "suggestions": ["..."], "rationale": "..."}'
            )
        if request.prompt_mode == PromptMode.CONTEXT:
            return (
                transcript_block
                + "Correct or refine the transcript using visual context only when it resolves ambiguity in names, numbers, dates, filenames, code identifiers, or visible terms. "
                "Output only the final text with no labels or commentary."
            )
        return transcript_block + "Return only the final cleaned transcript text."

    if request.prompt_mode == PromptMode.REASONING:
        return (
            "Use the audio as the main instruction source and the visual context as supporting evidence. "
            "Respond with JSON only, for example: "
            '{"typed_text": "...", "suggestions": ["..."], "rationale": "..."}'
        )
    if request.prompt_mode == PromptMode.CONTEXT:
        return (
            "Transcribe this utterance. Use visuals only to resolve ambiguity in names, numbers, dates, or visible terminology. "
            "Output only the final text with no labels or commentary."
        )
    return (
        "Transcribe this utterance exactly. Ignore all visuals. Output only the final text with no labels or commentary."
    )


def build_gemma_messages(request: TranscriptionRequest) -> list[dict[str, Any]]:
    user_content: list[dict[str, Any]] = []
    for _ in request.visual_context.images:
        user_content.append({"type": "image"})
    for _ in request.visual_context.video_frames:
        user_content.append({"type": "image"})
    if not request.transcript_text:
        user_content.append({"type": "audio"})
    user_content.append({"type": "text", "text": build_user_instruction(request)})
    return [
        {"role": "system", "content": build_system_prompt(request)},
        {"role": "user", "content": user_content},
    ]


def clean_gemma_response(raw_text: str) -> str:
    cleaned = (raw_text or "").strip()
    if not cleaned:
        return ""

    patterns = [
        r"<\|channel\>thought\s*.*?<channel\|>",
        r"<\|channel\|>thought\s*.*?<\|channel\|>",
        r"<think>\s*.*?</think>",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL)

    cleaned = cleaned.replace("<|think|>", "")
    return cleaned.strip()


def parse_reasoning_output(raw_text: str) -> PreviewPayload:
    cleaned = clean_gemma_response(raw_text)
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        payload = json.loads(cleaned)
        typed_text = str(payload.get("typed_text", "")).strip()
        suggestions = payload.get("suggestions") or []
        if not isinstance(suggestions, list):
            suggestions = [str(suggestions)]
        suggestions = [str(item).strip() for item in suggestions if str(item).strip()]
        rationale = str(payload.get("rationale", "")).strip()
        if typed_text:
            return PreviewPayload(typed_text=typed_text, suggestions=suggestions, rationale=rationale)
    except json.JSONDecodeError:
        pass

    return PreviewPayload(typed_text=cleaned, suggestions=[], rationale="")
