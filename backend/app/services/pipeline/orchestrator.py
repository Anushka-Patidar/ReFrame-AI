"""Pipeline orchestrator: understand → reason → constrain → edit → validate → retry."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from PIL import Image

from app.core.config import settings
from app.services.design_brief import DesignBrief
from app.services.generation_runtime import USER_GENERIC_ERROR, generation_gate
from app.services.pipeline.constraints import build_constraints
from app.services.pipeline.design_reasoning import reason_design_brief
from app.services.pipeline.result_validation import (
    build_correction_instruction,
    validate_design_result,
)
from app.services.pipeline.room_understanding import analyze_room
from app.services.pipeline.segmentation import prepare_segmentation
from app.services.pipeline.structural_conditioning import prepare_structural_signals
from app.services.pipeline.types import (
    DesignValidationReport,
    GenerationMetadata,
    PipelineArtifacts,
)
from app.services.pipeline.types import ObjectMask
from app.services.providers import GenerationResult
from app.services.providers.local_diffusion import get_local_provider
from app.services.providers.local_inpainting import get_inpainting_provider

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 2


@dataclass
class PipelineRunResult:
    image: Image.Image
    brief: DesignBrief
    artifacts: PipelineArtifacts
    generation: GenerationResult
    relative_ready: bool = True


def run_redesign_pipeline(
    *,
    source_image: Image.Image,
    room: dict,
    requirements: dict | None,
    revision_note: str | None = None,
    memory_document: dict | None = None,
    user_region_masks: list[ObjectMask] | None = None,
    max_attempts: int | None = None,
) -> PipelineRunResult:
    """Execute the modular redesign pipeline with bounded generate→validate→retry."""
    attempts = max(1, min(int(max_attempts or settings.local_max_retries or DEFAULT_MAX_ATTEMPTS), 3))

    generation_gate.set_stage("analyzing")
    room_analysis = analyze_room(room, requirements)
    brief, memory, _enriched = reason_design_brief(
        room,
        requirements,
        revision_note,
        memory_document=memory_document,
    )
    constraints = build_constraints(brief, room_analysis)

    generation_gate.set_stage("preparing")
    segmentation = prepare_segmentation(
        source_image,
        room_analysis,
        enabled=False,
        user_region_masks=user_region_masks,
    )
    structure = prepare_structural_signals(source_image, compute_lightweight_edges=True)

    # Choose provider: inpainting when we have editable masks, else img2img preview.
    has_edit_mask = bool(segmentation.edit_mask_path)
    if has_edit_mask:
        try:
            provider = get_inpainting_provider()
            logger.info("REFRAME_PIPELINE using inpainting provider (edit mask available)")
        except Exception:
            logger.warning("Inpainting provider unavailable; falling back to img2img")
            provider = get_local_provider()
    else:
        provider = get_local_provider()
        logger.info("REFRAME_PIPELINE using img2img provider (no edit mask)")

    if settings.debug_mask_pipeline:
        try:
            room_id = str(room.get("_id") or room.get("id") or "")
            masks = list(getattr(segmentation, "masks", []) or [])
            total_constraints = len(masks)

            def _action_block(action: str) -> tuple[int, list[str], bool]:
                subset = [m for m in masks if str(getattr(m, "action", "")).strip().upper() == action]
                labels = sorted({str(getattr(m, "label", "")).strip() for m in subset if getattr(m, "label", None)})
                if not subset:
                    return 0, [], False
                mask_loaded = all(bool(getattr(m, "available", False)) and bool(getattr(m, "mask_path", None)) for m in subset)
                return len(subset), labels, mask_loaded

            keep_count, keep_labels, keep_loaded = _action_block("KEEP")
            change_count, change_labels, change_loaded = _action_block("CHANGE")
            remove_count, remove_labels, remove_loaded = _action_block("REMOVE")

            keep_mask_created = bool(getattr(segmentation, "keep_mask_path", None))
            edit_mask_created = bool(getattr(segmentation, "edit_mask_path", None))
            keep_dims = getattr(segmentation, "keep_mask_dimensions", None)
            edit_dims = getattr(segmentation, "edit_mask_dimensions", None)
            source_dims = list(source_image.size)

            keep_pct = getattr(segmentation, "keep_painted_pixel_percentage", None)
            edit_pct = getattr(segmentation, "edit_painted_pixel_percentage", None)
            overlap_pct = getattr(segmentation, "keep_edit_overlap_pixel_percentage", None)

            canny_created = bool(getattr(structure, "edges_available", False))
            canny_dims = list(source_image.size)
            canny_path = getattr(structure, "edges_path", None) or ""

            supports_masks = bool(getattr(provider, "supports_masks", False))
            supports_structure = bool(getattr(provider, "supports_structure", False))

            preview_path = getattr(segmentation, "debug_preview_path", None)

            logger.info(
                "REGION CONSTRAINTS\n"
                "------------------\n"
                f"room_id: {room_id}\n"
                f"total_constraints: {total_constraints}\n"
                "\n"
                f"KEEP:\n"
                f"count: {keep_count}\n"
                f"labels: {keep_labels}\n"
                f"mask_loaded: {keep_loaded}\n"
                "\n"
                f"CHANGE:\n"
                f"count: {change_count}\n"
                f"labels: {change_labels}\n"
                f"mask_loaded: {change_loaded}\n"
                "\n"
                f"REMOVE:\n"
                f"count: {remove_count}\n"
                f"labels: {remove_labels}\n"
                f"mask_loaded: {remove_loaded}\n"
                "\n"
                "COMBINED MASKS\n"
                "--------------\n"
                f"keep_mask_created: {keep_mask_created}\n"
                f"edit_mask_created: {edit_mask_created}\n"
                f"keep_mask_dimensions: {keep_dims}\n"
                f"edit_mask_dimensions: {edit_dims}\n"
                f"source_image_dimensions: {source_dims}\n"
                f"KEEP mask painted_pixel_percentage: {keep_pct}\n"
                f"EDIT mask painted_pixel_percentage: {edit_pct}\n"
                f"KEEP/EDIT overlap pixel percentage (pre-subtract): {overlap_pct}\n"
                "\n"
                "STRUCTURAL CONDITIONING\n"
                "-----------------------\n"
                f"canny_created: {canny_created}\n"
                f"canny_dimensions: {canny_dims}\n"
                f"canny_path: {canny_path}\n"
                "\n"
                "GENERATION PROVIDER\n"
                "-------------------\n"
                f"provider: {getattr(provider, 'name', 'local')}\n"
                f"supports_masks: {supports_masks}\n"
                f"supports_structure: {supports_structure}\n"
                + (f"debug_preview_path: {preview_path}\n" if preview_path else "")
            )
        except Exception:
            logger.exception("REFRAME_MASK_DEBUG logging failed")

    last_report: DesignValidationReport | None = None
    last_generation: GenerationResult | None = None
    active_brief = brief
    correction: str | None = None

    for attempt in range(1, attempts + 1):
        generation_gate.set_stage("redesigning")
        note = revision_note
        if correction:
            note = f"{revision_note + ' | ' if revision_note else ''}{correction}"
            # Rebuild brief with correction so prompt/negative update.
            active_brief, _, _ = reason_design_brief(
                room,
                requirements,
                note,
                memory_document=memory_document,
            )
            constraints = build_constraints(active_brief, room_analysis)

        try:
            generation = provider.generate_room(
                source_image,
                active_brief,
                active_brief.transformation_strength,
                constraints=constraints,
                segmentation=segmentation,
                structure=structure,
            )
        except TypeError:
            # Older provider signature without optional kwargs.
            generation = provider.generate_room(
                source_image,
                active_brief,
                active_brief.transformation_strength,
            )
        last_generation = generation

        generation_gate.set_stage("refining")
        report = validate_design_result(
            source_image,
            generation.image,
            active_brief,
            constraints,
            attempt=attempt,
            segmentation=segmentation,
        )
        last_report = report
        logger.info(
            "REFRAME_PIPELINE attempt=%s passed=%s violations=%s delta=%s structure=%s",
            attempt,
            report.overall_passed,
            report.violations,
            _metric_value(report, "mean_abs_delta"),
            _metric_value(report, "structure_similarity"),
        )

        if report.overall_passed:
            break

        if attempt < attempts:
            correction = build_correction_instruction(report, active_brief)
            try:
                generation.image.close()
            except Exception:
                pass
            continue

        # Final attempt still failed measurable checks.
        raise RuntimeError(USER_GENERIC_ERROR)

    assert last_generation is not None and last_report is not None

    metadata = GenerationMetadata(
        generation_id=uuid4().hex,
        source_image_url=room.get("original_image_url"),
        design_brief=active_brief.to_dict(),
        constraints=constraints.to_dict(),
        room_analysis=room_analysis.to_dict(),
        validation=last_report.to_dict(),
        model=last_generation.model,
        model_configuration={
            "provider": last_generation.provider,
            "device": last_generation.device,
            "steps": last_generation.steps,
            "strength": last_generation.strength,
            "resolution": list(last_generation.resolution),
            "elapsed_seconds": last_generation.elapsed_seconds,
            "seed": last_generation.seed,
            "attempts": last_report.attempt,
            "segmentation_available": segmentation.available,
            "structure": structure.to_dict(),
            "run_config": getattr(provider, "last_run_config", {}),
        },
        seed=last_generation.seed,
        attempts=last_report.attempt,
        provider=last_generation.provider,
        training_consent=False,
    )

    artifacts = PipelineArtifacts(
        room_analysis=room_analysis,
        constraints=constraints,
        segmentation=segmentation,
        structure=structure,
        validation=last_report,
        memory=memory,
        metadata=metadata,
        correction_note=correction,
    )
    return PipelineRunResult(
        image=last_generation.image,
        brief=active_brief,
        artifacts=artifacts,
        generation=last_generation,
    )


def _metric_value(report: DesignValidationReport, name: str) -> Any:
    for metric in report.metrics:
        if metric.name == name:
            return metric.value
    return None
