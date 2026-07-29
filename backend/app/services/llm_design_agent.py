"""Strong LLM-backed interior design agent.

Priority:
1. Anthropic Claude (best reasoning / structured briefs)
2. OpenAI GPT (strong fallback)
3. Local rule-based extractor
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

import httpx

from app.core.config import settings
from app.services.design_agent import build_assistant_reply, extract_requirement_updates
from app.services.design_knowledge import normalize_requirements, resolve_style


SYSTEM_PROMPT = """You are ReFrame's senior AI interior designer.
You help homeowners redesign an existing room with accuracy and restraint.

Rules:
- Preserve the same room identity: camera angle, architecture, windows, and scale.
- Prefer practical, budget-aware Indian home redesign advice.
- Extract precise Keep / Remove / Add / Colours / Avoid / Style / Budget signals.
- Be concise, specific, and confident.
- Never invent impossible construction changes.
- If information is missing, ask one focused follow-up question.

You MUST respond with valid JSON only in this shape:
{
  "reply": "natural assistant message to the user",
  "requirements": {
    "style": "one of: Warm Minimal Luxury, Scandinavian, Japandi, Modern Contemporary, Coastal Calm, Indian Contemporary",
    "budget": 80000,
    "keep": ["item"],
    "remove": ["item"],
    "add": ["item"],
    "colours": ["colour"],
    "avoid": ["item"],
    "notes": ["short note"]
  }
}

Merge new user intent into the current requirements instead of wiping unrelated fields.
Only change fields the user clearly implies.
"""


def _safe_json_load(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def _merge_requirements(current: dict, incoming: dict | None) -> dict:
    merged = deepcopy(current)
    if not incoming:
        return merged

    if incoming.get("style"):
        merged["style"] = resolve_style(str(incoming["style"]))
    if incoming.get("budget") is not None:
        try:
            merged["budget"] = int(incoming["budget"])
        except (TypeError, ValueError):
            pass

    for key in ("keep", "remove", "add", "colours", "avoid", "notes"):
        values = incoming.get(key)
        if not isinstance(values, list):
            continue
        cleaned = [str(item).strip() for item in values if str(item).strip()]
        if cleaned:
            # Prefer model output as the updated active brief for those fields.
            merged[key] = cleaned[:8]
    return merged


async def _call_claude(user_payload: dict) -> dict[str, Any] | None:
    if not settings.anthropic_api_key:
        return None

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": settings.anthropic_model,
        "max_tokens": 900,
        "temperature": 0.2,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": json.dumps(user_payload),
            }
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body,
            )
            if response.status_code >= 400:
                return None
            data = response.json()
            chunks = data.get("content") or []
            text = "".join(
                part.get("text", "")
                for part in chunks
                if isinstance(part, dict) and part.get("type") == "text"
            )
            return _safe_json_load(text)
    except Exception:
        return None


async def _call_openai(user_payload: dict) -> dict[str, Any] | None:
    api_key = getattr(settings, "openai_api_key", None)
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": getattr(settings, "openai_chat_model", "gpt-4o"),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload)},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=body,
            )
            if response.status_code >= 400:
                return None
            data = response.json()
            text = (
                ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
                or ""
            )
            return _safe_json_load(text)
    except Exception:
        return None


async def run_design_agent(
    room: dict,
    message: str,
    current_requirements: dict,
) -> tuple[dict, str, str]:
    """
    Returns (updated_requirements, assistant_reply, engine_label).
    """
    user_payload = {
        "room": {
            "room_type": room.get("room_type"),
            "dimensions": room.get("dimensions"),
            "match_home_style": room.get("match_home_style", True),
            "has_original_image": bool(room.get("original_image_url")),
        },
        "current_requirements": current_requirements,
        "user_message": message,
    }

    parsed = await _call_claude(user_payload)
    engine = "claude"
    if parsed is None:
        parsed = await _call_openai(user_payload)
        engine = "openai"

    if parsed is not None:
        updated = normalize_requirements(
            room,
            _merge_requirements(current_requirements, parsed.get("requirements")),
        )
        reply = str(parsed.get("reply") or "").strip()
        if not reply:
            reply = build_assistant_reply(room.get("room_type", "room"), updated, current_requirements)
        return updated, reply, engine

    # Local deterministic fallback.
    updated = normalize_requirements(
        room,
        extract_requirement_updates(message, current_requirements),
    )
    reply = build_assistant_reply(room.get("room_type", "room"), updated, current_requirements)
    return updated, reply, "local-rules"
