from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.models.item import Item
from app.models.source import Source
from app.services.websearch import WebSearchError, web_search_client

_HYPE_MARKERS = ("шок", "сенсация", "breaking", "немыслимо", "скандал", "слух")
_IMPACT_MARKERS = ("миллиард", "санкции", "банкрот", "поглощение", "ipo", "acquisition")
_MAX_QUERY_LENGTH = 120
_MAX_CROSS_CHECK_MATCHES = 5
_ENTITY_PATTERN = re.compile(r"\b[А-ЯA-Z][\w-]{2,}\b")
_MAX_ENTITIES = 10
_HIGH_IMPACT_TEXT_LENGTH = 800
_MEDIUM_IMPACT_TEXT_LENGTH = 250
_HYPE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(marker) for marker in _HYPE_MARKERS) + r")\b"
)
_IMPACT_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(marker) for marker in _IMPACT_MARKERS) + r")\b"
)


@dataclass
class SentinelArtifacts:
    trust_score: int
    trust_status: str
    impact: str
    artifacts: dict[str, Any]


async def _run_cross_check(item: Item) -> dict[str, Any]:
    text = item.text or ""
    query = item.title.strip() or text[:_MAX_QUERY_LENGTH]
    result: dict[str, Any] = {
        "status": "missing",
        "matches": [],
        "query": query,
        "error": None,
    }
    if not query:
        return result
    try:
        matches = await web_search_client.search(query)
    except WebSearchError as exc:
        result["status"] = "error"
        result["error"] = exc.message
        return result
    sample = [
        {"title": match.get("title"), "url": match.get("url")}
        for match in matches[:_MAX_CROSS_CHECK_MATCHES]
        if isinstance(match, dict)
    ]
    status = "ok" if sample else "missing"
    return {"status": status, "matches": sample, "query": query}


def _run_logic_audit(text: str) -> dict[str, Any]:
    flags = sorted(set(_HYPE_PATTERN.findall(text)))
    status = "warning" if flags else "ok"
    return {"status": status, "flags": flags}


def _run_entity_verify(text: str) -> dict[str, Any]:
    candidates = set(_ENTITY_PATTERN.findall(text))
    entities = sorted(candidates)[:_MAX_ENTITIES]
    status = "ok" if entities else "limited"
    return {"status": status, "entities": entities}


def _run_trust_ledger(
    source: Source | None,
    cross_check: dict[str, Any],
    logic_audit: dict[str, Any],
    entity_verify: dict[str, Any],
    item_text: str,
) -> dict[str, Any]:
    score = source.trust_manual if source else 50
    if cross_check.get("status") == "ok":
        score += 10
    elif cross_check.get("status") == "missing":
        score -= 5
    if logic_audit.get("status") == "warning":
        score -= 10
    if entity_verify.get("status") == "ok":
        score += 5
    score = max(0, min(100, int(score)))

    if score >= 80:
        trust_status = "confirmed"
    elif score >= 55:
        trust_status = "mixed"
    elif score >= 30:
        trust_status = "unclear"
    else:
        trust_status = "hype"

    has_impact_marker = bool(_IMPACT_PATTERN.search(item_text))
    is_long_text = len(item_text) > _HIGH_IMPACT_TEXT_LENGTH
    if has_impact_marker or is_long_text:
        impact = "high"
    elif len(item_text) > _MEDIUM_IMPACT_TEXT_LENGTH:
        impact = "medium"
    else:
        impact = "low"

    return {"trust_score": score, "trust_status": trust_status, "impact": impact}


async def run_sentinel(item: Item, source: Source | None) -> SentinelArtifacts:
    raw_text = f"{item.title} {item.text or ''}"
    normalized_text = raw_text.lower()
    cross_check = await _run_cross_check(item)
    logic_audit = _run_logic_audit(normalized_text)
    entity_verify = _run_entity_verify(raw_text)
    trust_ledger = _run_trust_ledger(
        source, cross_check, logic_audit, entity_verify, normalized_text
    )
    artifacts = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cross_check": cross_check,
        "logic_audit": logic_audit,
        "entity_verify": entity_verify,
        "trust_ledger": trust_ledger,
    }
    return SentinelArtifacts(
        trust_score=trust_ledger["trust_score"],
        trust_status=trust_ledger["trust_status"],
        impact=trust_ledger["impact"],
        artifacts=artifacts,
    )


async def apply_sentinel(item: Item, source: Source | None) -> dict[str, Any]:
    result = await run_sentinel(item, source)
    item.trust_score = result.trust_score
    item.trust_status = result.trust_status
    item.impact = result.impact
    item.sentinel_json = result.artifacts
    return result.artifacts
