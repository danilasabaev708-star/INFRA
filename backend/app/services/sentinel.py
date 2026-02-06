from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.models.item import Item
from app.models.source import Source
from app.services.websearch import WebSearchError, web_search_client

_HYPE_MARKERS = ("шок", "сенсац", "breaking", "немыслим", "скандал", "слух")
_IMPACT_MARKERS = ("миллиард", "санкц", "банкрот", "поглощ", "ipo", "acquisition")


@dataclass
class SentinelArtifacts:
    trust_score: int
    trust_status: str
    impact: str
    artifacts: dict[str, Any]


async def _run_cross_check(item: Item) -> dict[str, Any]:
    query = item.title.strip() or item.text[:120]
    result: dict[str, Any] = {"status": "missing", "matches": [], "query": query}
    if not query:
        return result
    try:
        matches = await web_search_client.search(query)
    except WebSearchError as exc:
        return {"status": "error", "error": exc.message, "matches": [], "query": query}
    sample = [
        {"title": match.get("title"), "url": match.get("url")}
        for match in matches[:5]
        if isinstance(match, dict)
    ]
    status = "ok" if sample else "missing"
    return {"status": status, "matches": sample, "query": query}


def _run_logic_audit(item: Item) -> dict[str, Any]:
    text = f"{item.title} {item.text}".lower()
    flags = [marker for marker in _HYPE_MARKERS if marker in text]
    status = "warning" if flags else "ok"
    return {"status": status, "flags": flags}


def _run_entity_verify(item: Item) -> dict[str, Any]:
    candidates = set(re.findall(r"\b[А-ЯA-Z][\w-]{2,}\b", item.title + " " + item.text))
    entities = sorted(candidates)[:10]
    status = "ok" if entities else "limited"
    return {"status": status, "entities": entities}


def _run_trust_ledger(
    source: Source | None,
    cross_check: dict[str, Any],
    logic_audit: dict[str, Any],
    entity_verify: dict[str, Any],
    item: Item,
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

    text = f"{item.title} {item.text}".lower()
    if any(marker in text for marker in _IMPACT_MARKERS) or len(text) > 800:
        impact = "high"
    elif len(text) > 250:
        impact = "medium"
    else:
        impact = "low"

    return {"trust_score": score, "trust_status": trust_status, "impact": impact}


async def run_sentinel(item: Item, source: Source | None) -> SentinelArtifacts:
    cross_check = await _run_cross_check(item)
    logic_audit = _run_logic_audit(item)
    entity_verify = _run_entity_verify(item)
    trust_ledger = _run_trust_ledger(source, cross_check, logic_audit, entity_verify, item)
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
