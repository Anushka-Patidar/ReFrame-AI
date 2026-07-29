# Future LoRA / Fine-Tuning Pipeline (Optional)

**Do not train anything yet.**

This document only prepares the architecture for a later, optional fine-tuning step after:

1. The modular redesign pipeline works end-to-end
2. A capable open-source base model is selected (Tiny-SD is **not** assumed to be that base)
3. A high-quality **licensed / consenting** dataset exists
4. Appropriate GPU compute is available

## Goal

Teach a suitable open-source image model ReFrame’s interior-design behavior:

```
BEFORE room photo
+ DesignBrief / constraints
→ HIGH-QUALITY AFTER redesign of the SAME room
```

Preferred approach: **parameter-efficient fine-tuning** (LoRA / similar), not training a foundation model from scratch.

## Candidate training example schema

```json
{
  "example_id": "...",
  "source_image_uri": "...",
  "target_image_uri": "...",
  "design_brief": {},
  "constraints": {},
  "license": "explicit-consent | synthetic-licensed | public-domain",
  "training_consent": true,
  "quality_review": "accepted",
  "base_model_family": "sd15 | sdxl | other"
}
```

Only examples with `training_consent=true` and an acceptable license may enter a training set.

## Data sources (future)

- Opt-in user generations stored in `generation_events` **only when consent is recorded**
- Professionally produced before/after pairs with commercial rights
- Synthetic pairs generated under licenses that allow training

Never silently harvest private user photos.

## Suggested later workflow

1. Export consented `generation_events` + curated pairs
2. Filter by validation pass + human review
3. Choose base model independently of the current Tiny-SD dev model
4. Train LoRA on GPU
5. Register adapter id in `LOCAL_MODEL_ID` / provider config
6. Keep the same ReFrame pipeline; swap only the ImageEditing backend

## Non-goals for now

- No model downloads for fine-tuning
- No training jobs in CI
- No claim that Tiny-SD will be the production base
