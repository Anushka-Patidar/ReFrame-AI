"""DesignResultValidator — only genuine measurable checks; never invent scores."""

from __future__ import annotations

import logging
from collections.abc import Mapping

import numpy as np
from PIL import Image, ImageFilter

from app.services import image_generation as ig
from app.services.media import UPLOADS_ROOT

logger = logging.getLogger(__name__)
from app.services.design_brief import DesignBrief
from app.services.pipeline.types import (
    ConstraintKind,
    ConstraintSet,
    DesignValidationReport,
    ValidationMetric,
)


def _add_mask_metrics(
    original: Image.Image,
    candidate: Image.Image,
    segmentation,
    metrics: list,
    violations: list[str],
) -> None:
    """Compute outside-mask similarity and inside-mask difference."""
    edit_path = UPLOADS_ROOT / segmentation.edit_mask_path
    with Image.open(edit_path) as m:
        mask_l = m.convert("RGBA").split()[-1]
    mask_l = mask_l.point(lambda p: 255 if p > 0 else 0)

    orig_resized = original.convert("RGB").resize(candidate.size, Image.Resampling.LANCZOS)
    mask_resized = mask_l.resize(candidate.size, Image.Resampling.NEAREST)

    orig_arr = np.array(orig_resized, dtype=np.float32)
    cand_arr = np.array(candidate.convert("RGB"), dtype=np.float32)
    mask_arr = np.array(mask_resized, dtype=np.float32) / 255.0
    mask_3 = np.stack([mask_arr] * 3, axis=-1)

    # Outside mask: should be VERY similar to original (preserved regions).
    outside_weight = 1.0 - mask_3
    outside_count = outside_weight.sum() / 3.0
    if outside_count > 100:
        outside_diff = np.abs(orig_arr - cand_arr) * outside_weight
        outside_mae = outside_diff.sum() / (outside_count * 3.0)
        outside_similarity = max(0.0, 1.0 - outside_mae / 255.0)
        outside_ok = outside_similarity >= 0.85
        metrics.append(ValidationMetric(
            name="outside_mask_similarity",
            measured=True,
            value=round(outside_similarity, 4),
            passed=outside_ok,
            detail="Regions outside the edit mask should remain close to the original.",
        ))
        if not outside_ok:
            violations.append(
                f"Outside-mask region changed too much (similarity={outside_similarity:.3f}, need >=0.85)."
            )

    # Inside mask: should have meaningful change.
    inside_count = mask_3.sum() / 3.0
    if inside_count > 100:
        inside_diff = np.abs(orig_arr - cand_arr) * mask_3
        inside_mae = inside_diff.sum() / (inside_count * 3.0)
        inside_change = inside_mae / 255.0
        inside_ok = inside_change >= 0.03
        metrics.append(ValidationMetric(
            name="inside_mask_difference",
            measured=True,
            value=round(inside_change, 4),
            passed=inside_ok,
            detail="Regions inside the edit mask should change meaningfully.",
        ))
        if not inside_ok:
            violations.append(
                f"Inside-mask region barely changed (change={inside_change:.3f}, need >=0.03)."
            )


def _sharpness_score(image: Image.Image) -> float:
    gray = image.convert("L").resize((192, 192), Image.Resampling.LANCZOS)
    edge = gray.filter(ImageFilter.FIND_EDGES)
    arr = np.array(edge, dtype=np.float32)
    return float(arr.std())


def _add_sharpness_metric(
    original: Image.Image,
    candidate: Image.Image,
    metrics: list[ValidationMetric],
    violations: list[str],
) -> None:
    before = _sharpness_score(original)
    after = _sharpness_score(candidate)
    minimum = max(6.0, before * 0.55)
    sharp_ok = after >= minimum
    metrics.append(
        ValidationMetric(
            name="sharpness_after",
            measured=True,
            value=round(after, 3),
            passed=sharp_ok,
            detail=f"Expected sharpness >= {minimum:.2f} based on source edge detail.",
        )
    )
    metrics.append(
        ValidationMetric(
            name="sharpness_before",
            measured=True,
            value=round(before, 3),
            passed=True,
            detail="Baseline source sharpness for development diagnostics.",
        )
    )
    if not sharp_ok:
        violations.append(f"Output is substantially blurrier than the source (sharpness={after:.2f}).")


def _add_structure_condition_metric(
    candidate: Image.Image,
    structure,
    metrics: list[ValidationMetric],
) -> None:
    condition_path = getattr(structure, "architecture_condition_path", None) if structure else None
    if not condition_path:
        return
    with Image.open(UPLOADS_ROOT / condition_path) as m:
        condition = m.convert("L")
    candidate_edges = candidate.convert("L").resize(condition.size, Image.Resampling.LANCZOS).filter(
        ImageFilter.FIND_EDGES
    )
    cond_arr = np.array(condition, dtype=np.float32)
    edge_arr = np.array(candidate_edges, dtype=np.float32)
    mask = cond_arr > 8.0
    if mask.sum() < 100:
        return
    similarity = 1.0 - (np.abs(cond_arr[mask] - edge_arr[mask]).mean() / 255.0)
    metrics.append(
        ValidationMetric(
            name="architecture_condition_similarity",
            measured=True,
            value=round(float(similarity), 4),
            passed=True,
            detail="Diagnostic only: candidate edge response on architecture-conditioned pixels.",
        )
    )


def validate_design_result(
    original: Image.Image,
    candidate: Image.Image,
    brief: DesignBrief,
    constraints: ConstraintSet,
    *,
    attempt: int = 1,
    segmentation=None,
    structure=None,
    mode: str = "automatic",
) -> DesignValidationReport:
    metrics: list[ValidationMetric] = []
    violations: list[str] = []
    constraint_results: dict[str, bool | None] = {}

    # --- Measurable image heuristics (genuine) ---
    identical = ig.images_byte_identical(original, candidate)
    metrics.append(
        ValidationMetric(
            name="byte_identity",
            measured=True,
            value=1.0 if identical else 0.0,
            passed=not identical,
            detail="Output must differ from the source photograph.",
        )
    )
    if identical:
        violations.append("Generated image matched the original photograph.")

    photoreal = ig.looks_photoreal_enough(candidate)
    metrics.append(
        ValidationMetric(
            name="photoreal_heuristic",
            measured=True,
            value=1.0 if photoreal else 0.0,
            passed=photoreal,
            detail="Reject extreme abstract / collapsed outputs.",
        )
    )
    if not photoreal:
        violations.append("Output failed photoreal / collapse heuristic.")

    faces = ig.contains_human_face(candidate)
    metrics.append(
        ValidationMetric(
            name="no_human_faces",
            measured=True,
            value=0.0 if faces else 1.0,
            passed=not faces,
        )
    )
    if faces:
        violations.append("Human faces detected in redesign.")

    delta = ig.mean_abs_delta(original, candidate)
    min_delta = ig.min_delta_for_strength(brief.transformation_strength)
    if mode == "precision":
        min_delta = min(min_delta, 8.0)
    delta_ok = delta >= min_delta
    metrics.append(
        ValidationMetric(
            name="mean_abs_delta",
            measured=True,
            value=round(delta, 3),
            passed=delta_ok,
            detail=f"Minimum required delta for '{brief.transformation_strength}' is {min_delta}.",
        )
    )
    if not delta_ok:
        violations.append(f"Visible change too small (delta={delta:.1f}, need ≥{min_delta}).")

    similarity = ig.structure_similarity(original, candidate)
    arch_ok = ig.architecture_ok(original, candidate, brief.transformation_strength)
    metrics.append(
        ValidationMetric(
            name="structure_similarity",
            measured=True,
            value=round(similarity, 3),
            passed=arch_ok,
            detail="Edge-map similarity used as a proxy for architecture preservation.",
        )
    )
    if not arch_ok:
        violations.append(f"Architecture preservation failed (structure={similarity:.2f}).")

    _add_sharpness_metric(original, candidate, metrics, violations)
    try:
        _add_structure_condition_metric(candidate, structure, metrics)
    except Exception:
        logger.debug("Structure-conditioned similarity metric failed", exc_info=True)

    # --- Mask-aware regional metrics ---
    if segmentation and getattr(segmentation, "edit_mask_path", None):
        try:
            _add_mask_metrics(original, candidate, segmentation, metrics, violations)
        except Exception:
            pass

    # --- Constraint compliance: only mark measured when we have a real checker ---
    for item in constraints.by_kind(ConstraintKind.ARCHITECTURE_LOCKED):
        # Shared architecture check applies to all locked anchors.
        constraint_results[f"architecture:{item.target}"] = arch_ok

    for item in constraints.by_kind(ConstraintKind.OBJECT_KEEP):
        # Object-level KEEP cannot be verified without segmentation / vision.
        constraint_results[f"keep:{item.target}"] = None
        metrics.append(
            ValidationMetric(
                name=f"keep:{item.target}",
                measured=False,
                value=None,
                passed=None,
                detail="Object KEEP compliance requires future vision/segmentation.",
            )
        )

    for item in constraints.by_kind(ConstraintKind.OBJECT_REMOVE):
        constraint_results[f"remove:{item.target}"] = None
        metrics.append(
            ValidationMetric(
                name=f"remove:{item.target}",
                measured=False,
                value=None,
                passed=None,
                detail="Object REMOVE compliance requires future vision/segmentation.",
            )
        )

    for item in constraints.by_kind(ConstraintKind.STYLE_CONSTRAINT):
        constraint_results[f"style:{item.target}"] = None
        metrics.append(
            ValidationMetric(
                name=f"style:{item.target}",
                measured=False,
                passed=None,
                detail="Style compliance scoring requires a future evaluator — not invented.",
            )
        )

    for item in constraints.by_kind(ConstraintKind.COLOR_CONSTRAINT):
        constraint_results[f"palette:{item.target}"] = None

    measurable_failed = any(
        metric.measured and metric.passed == False for metric in metrics
    )
    overall_passed = (not measurable_failed) and (not identical)

    return DesignValidationReport(
        architecture_preserved=arch_ok,
        constraints=constraint_results,
        metrics=metrics,
        violations=violations,
        overall_passed=overall_passed,
        style_score=None,
        overall_score=None,
        attempt=attempt,
    )


def build_correction_instruction(
    report: DesignValidationReport,
    brief: DesignBrief,
) -> str:
    """Deterministic correction note for a retry attempt — no invented claims."""
    parts: list[str] = [
        f"Correction pass for {brief.target_style} {brief.room_type}.",
        "Preserve architecture more carefully.",
    ]
    if any("delta" in v.lower() or "visible change" in v.lower() for v in report.violations):
        parts.append(
            "Increase visible furniture and wall redesign while keeping doors/windows fixed."
        )
    if any("architecture" in v.lower() for v in report.violations):
        parts.append("Do not warp walls, ceiling, or camera viewpoint.")
    if brief.keep_objects:
        parts.append("KEEP unchanged: " + ", ".join(brief.keep_objects[:4]) + ".")
    if brief.remove_objects:
        parts.append("REMOVE completely: " + ", ".join(brief.remove_objects[:4]) + ".")
    if brief.replace_or_add:
        parts.append("ADD/REPLACE: " + ", ".join(brief.replace_or_add[:4]) + ".")
    if report.violations:
        parts.append("Prior violations: " + "; ".join(report.violations[:3]) + ".")
    return " ".join(parts)


def build_retry_overrides(
    report: DesignValidationReport,
    *,
    has_mask: bool,
    current: Mapping[str, float | int | None] | None = None,
) -> dict[str, float | int | None]:
    """Deterministic retry settings keyed to measured failures."""
    current = dict(current or {})
    next_values: dict[str, float | int | None] = {
        "strength_override": current.get("strength_override"),
        "steps_override": current.get("steps_override"),
        "structure_strength_override": current.get("structure_strength_override"),
    }

    text = " ".join(report.violations).lower()
    if "visible change too small" in text or "inside-mask region barely changed" in text:
        base = float(next_values["strength_override"] or (0.84 if has_mask else 0.68))
        next_values["strength_override"] = min(0.98, base + 0.08)
    if "outside-mask region changed too much" in text:
        base = float(next_values["strength_override"] or 0.84)
        next_values["strength_override"] = max(0.55, base - 0.08)
    if "architecture" in text or "boundaries drifted" in text:
        base = float(next_values["structure_strength_override"] or 0.72)
        next_values["structure_strength_override"] = min(1.15, base + 0.12)
        if not has_mask:
            base_strength = float(next_values["strength_override"] or 0.68)
            next_values["strength_override"] = max(0.52, base_strength - 0.04)
    if "blurrier" in text or "photoreal" in text:
        base_steps = int(next_values["steps_override"] or 20)
        next_values["steps_override"] = min(32, base_steps + 4)

    return next_values
