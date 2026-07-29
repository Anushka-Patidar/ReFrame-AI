# Local realism benchmark (Tiny-SD)

Dev-only outputs: `backend/uploads/generated/benchmark/`

## Phase 1 — measured baseline (this machine)

| Field | Value |
|---|---|
| MODEL | `segmind/tiny-sd` |
| DEVICE | `cpu` |
| DTYPE | `float32` |
| SCHEDULER | `ddim` |
| INPUT RES (typical) | 320×240 (aspect preserved, letterboxed) |
| OUTPUT DISPLAY | up to ~960×720 |
| PEAK RAM (process RSS) | ~2.5–2.7 GB |
| IDLE RSS (before load) | ~0.22 GB |

Positive prompt (dev log):

```
photorealistic professional interior photograph of the SAME living room, Indian Contemporary interior design, preserve original room geometry and camera, keep curtains, door, remove sofa, TV unit, paintings, add new seating, artwork, wall clock, palette blue, yellow, brown, realistic wood fabric materials, architectural lighting, sharp detail
```

## Sequential configs (seed=42)

| Config | Time | Delta | Structure | Sharpness proxy | Visual notes |
|---|---:|---:|---:|---:|---|
| strength 0.45 / 12 / 320 | ~65s | 16.8 | 0.917 | 21.7 | More structure, still muddy/blurry |
| strength 0.55 / 12 / 320 | ~33s | 22.4 | 0.898 | 23.0 | More change, melted furniture |
| strength 0.65 / 12 / 320 | ~41s | 27.6 | 0.876 | 25.8 | Strongest change, worst melt |
| strength 0.55 / 16 / 320 | ~34s | 23.4 | 0.896 | 23.0 | Slightly cleaner than 12 steps |
| strength 0.52 / 20 / 384 | ~39s | 18.9 | 0.914 | 21.9 | Mildly better geometry, still soft |

## Recommended Tiny-SD operating point

`profile=balanced`≈ **384 max side, 16 steps, strength 0.55, guidance 7.0, DDIM**

This is the least-bad local compromise. It does **not** reach photoreal success criteria.

## Bottleneck conclusion

After preprocessing, prompts, scheduler, strength/steps sweeps, and mild postprocess:

**Tiny-SD is now the quality bottleneck.**

Remaining blur, melted furniture, weak materials, and flat lighting are dominated by model capacity + low native resolution — not by missing adjectives in the prompt.
