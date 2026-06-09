"""Build radar_policy_impacts rows from reviewed impact_json."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable, Literal, TypedDict

ImpactedType = Literal[
    "deleted",
    "inserted",
    "measure_changed",
    "desc_changed",
    "rate_changed",
]

REVIEW_CHANGE_TYPES: set[ImpactedType] = {"desc_changed", "rate_changed"}


class RadarPolicyImpact(TypedDict):
    """Internal representation of one radar_policy_impacts insert row."""

    policy_update_id: int | None
    hts_number: str
    impacted_type: ImpactedType
    effective_time: str | None
    coos: list[str] | None
    row_desc: str | None


def build_radar_policy_impacts(
    impact_json: dict[str, Any],
    *,
    policy_update_id: int | None = None,
    policy_effective_date: str | None = None,
    policy_published_at: str | None = None,
) -> list[RadarPolicyImpact]:
    """Generate radar_policy_impacts rows from the reviewed JSON payload."""

    rows: list[RadarPolicyImpact] = []
    source = _as_dict(impact_json.get("source"))
    default_effective_date = (
        _normalize_date(policy_effective_date)
        or _normalize_date(policy_published_at)
        or _normalize_date(source.get("detected_at"))
    )

    scope_headings_by_id = _build_scope_heading_index(impact_json)

    for measure_value in _as_list(impact_json.get("measures")):
        measure = _as_dict(measure_value)
        one_line_summary = _optional_string(measure.get("one_line_summary"))
        heading = _first_string(
            measure.get("heading"),
            measure.get("hts_number"),
            measure.get("measure_heading"),
        )
        row_desc = _optional_string(measure.get("description"))
        effective_time = (
            _normalize_date(_optional_string(measure.get("effective_start_date")))
            or default_effective_date
        )

        if heading and is_chapter_one_to_ninety_eight(heading):
            for change_type in _review_change_types(measure.get("change_type")):
                rows.append(
                    _make_impact(
                        policy_update_id=policy_update_id,
                        hts_number=heading,
                        impacted_type=change_type,
                        effective_time=effective_time,
                        coos=None,
                        row_desc=row_desc,
                        one_line_summary=one_line_summary,
                    )
                )
            continue

        included_headings: set[str] = set(_string_list(measure.get("includes_headings")))
        scope_refs = [
            *_string_list(measure.get("affected_scope_refs")),
            *_string_list(measure.get("includes_scope_refs")),
        ]
        for scope_ref in scope_refs:
            included_headings.update(scope_headings_by_id.get(scope_ref, []))

        coos = _normalize_country_list(_optional_string(measure.get("country_iso2")))
        for hts_number in included_headings:
            if is_chapter_one_to_ninety_eight(hts_number):
                rows.append(
                    _make_impact(
                        policy_update_id=policy_update_id,
                        hts_number=hts_number,
                        impacted_type="measure_changed",
                        effective_time=effective_time,
                        coos=coos,
                        row_desc=row_desc,
                        one_line_summary=one_line_summary,
                    )
                )

    return _dedupe_impacts(rows)


def is_chapter_one_to_ninety_eight(hts_number: str) -> bool:
    """Return true when the HTS starts with chapter 01-98."""

    match = re.match(r"^(\d{2})", hts_number.strip())
    if not match:
        return False
    chapter = int(match.group(1))
    return 1 <= chapter <= 98


def _build_scope_heading_index(impact_json: dict[str, Any]) -> dict[str, list[str]]:
    scope_headings_by_id: dict[str, list[str]] = {}
    for scope_value in _as_list(impact_json.get("scope_sets")):
        scope = _as_dict(scope_value)
        scope_id = _optional_string(scope.get("id"))
        if not scope_id:
            continue
        scope_headings_by_id[scope_id] = _string_list(scope.get("headings"))
    return scope_headings_by_id


def _make_impact(
    *,
    policy_update_id: int | None,
    hts_number: str,
    impacted_type: ImpactedType,
    effective_time: str | None,
    coos: list[str] | None,
    row_desc: str | None,
    one_line_summary: str | None,
) -> RadarPolicyImpact:
    return {
        "policy_update_id": policy_update_id,
        "hts_number": hts_number.strip(),
        "impacted_type": impacted_type,
        "effective_time": effective_time,
        "coos": coos,
        "row_desc": row_desc,
        "one_line_summary": one_line_summary,
    }


def _review_change_types(value: Any) -> list[ImpactedType]:
    raw_values = value if isinstance(value, list) else [value] if value else []
    change_types: list[ImpactedType] = []
    for raw_value in raw_values:
        if raw_value in REVIEW_CHANGE_TYPES:
            change_types.append(raw_value)
    return list(dict.fromkeys(change_types))


def _dedupe_impacts(rows: Iterable[RadarPolicyImpact]) -> list[RadarPolicyImpact]:
    seen: set[str] = set()
    deduped: list[RadarPolicyImpact] = []
    for row in rows:
        key = json.dumps(
            [
                row["hts_number"],
                row["impacted_type"],
                row["effective_time"],
                row["coos"],
                row["row_desc"],
            ],
            sort_keys=True,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    return sorted(deduped, key=lambda row: (row["hts_number"], row["impacted_type"]))


def _normalize_country_list(country_iso2: str | None) -> list[str] | None:
    normalized = country_iso2.strip().upper() if country_iso2 else ""
    return [normalized] if normalized else None


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    return normalized[:10] if normalized else None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _first_string(*values: Any) -> str | None:
    for value in values:
        normalized = _optional_string(value)
        if normalized:
            return normalized
    return None
