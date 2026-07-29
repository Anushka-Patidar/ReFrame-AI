# ReFrame AI Architecture

ReFrame is being built as a **specialized AI interior-design system**, not as “an app that sends one prompt to an image model.”

Tiny-SD is only the current **development** image backend. The architecture is model-independent.

## Pipeline stages

```
RoomUnderstanding
      ↓
DesignReasoning
      ↓
DesignBrief + ConstraintEngine
      ↓
Segmentation (interface; optional)
      ↓
StructuralConditioning (interface; optional)
      ↓
ImageEditing (LocalGenerationProvider)
      ↓
ResultValidation
      ↓
Generate → Evaluate → Retry (bounded)
      ↓
DesignMemory + GenerationEvents
```

| Stage | Module | Status now |
|---|---|---|
| RoomUnderstanding | `pipeline/room_understanding.py` | User/requirements-derived `RoomAnalysis` (vision-ready) |
| DesignReasoning | `pipeline/design_reasoning.py` | Deterministic brief from requirements + memory |
| DesignBrief | `design_brief.py` | Structured keep/remove/add/change/palette/budget/strength |
| Constraints | `pipeline/constraints.py` | `ARCHITECTURE_LOCKED`, `OBJECT_*`, style/color |
| Segmentation | `pipeline/segmentation.py` | Schema + placeholders — **no large model downloaded** |
| StructuralConditioning | `pipeline/structural_conditioning.py` | Lightweight edges optional; depth/ControlNet later |
| ImageEditing | `providers/local_diffusion.py` | Model-independent provider API; Tiny-SD today |
| ResultValidation | `pipeline/result_validation.py` | Genuine measurable metrics only — **no invented scores** |
| DesignMemory | `pipeline/design_memory.py` + Mongo `design_memory` | Non-sensitive preferences |
| Orchestrator | `pipeline/orchestrator.py` | Bounded generate → validate → retry |

## Important design rules

1. Image generation never parses raw chat history. Chat → requirements → DesignBrief → constraints → provider.
2. KEEP is object-specific. Architecture preservation is separate (`ARCHITECTURE_LOCKED`).
3. Validation never invents object KEEP/REMOVE or style scores without a real evaluator. Those fields stay `null` / `measured=False` until vision exists.
4. `training_consent` defaults to `false`. Private images are not used for fine-tuning without explicit permission.
5. Development hardware constraints must not shrink the architecture — stronger local/hosted models plug into the same provider interface.

## Persistence

- `design_versions.pipeline_metadata` — brief, constraints, model config, validation
- `generation_events` — audit trail for future learning (opt-in)
- `design_memory` — per-user non-sensitive preferences

## Runtime entrypoint

`generate_design_image()` → `run_redesign_pipeline()` → provider → validator → save.

## Future high-quality path

```
Original Room → Room Analysis → Segmentation masks → Depth/Edge structure
→ Capable diffusion editor (Tiny-SD replaceable) → Inpainting
→ Photoreal candidate → Constraint validation → Optional retry → Final design
```

Interfaces already exist for `StructuralConditioner`, `ImageEditor`, segmentation, and provider swap via `LOCAL_MODEL_ID`.

See also: `docs/realism-benchmark.md`, `docs/future-lora-finetuning.md`.
