"""Aspect-preserving image prep for diffusion — never stretch the room."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps


@dataclass(frozen=True)
class PreparedImage:
    image: Image.Image
    target_size: tuple[int, int]
    content_box: tuple[int, int, int, int]  # left, top, right, bottom inside padded canvas
    source_size: tuple[int, int]


def round_multiple(value: int, multiple: int = 8) -> int:
    return max(multiple, int(round(value / multiple) * multiple))


def compute_inference_size(
    width: int,
    height: int,
    max_side: int,
    *,
    multiple: int = 8,
) -> tuple[int, int]:
    """Scale longest side to max_side; keep aspect; snap to multiple (no forced square)."""
    if width <= 0 or height <= 0:
        return multiple, multiple
    scale = max_side / max(width, height)
    w = round_multiple(max(multiple, int(width * scale)), multiple)
    h = round_multiple(max(multiple, int(height * scale)), multiple)
    return w, h


def prepare_for_diffusion(
    source: Image.Image,
    max_side: int,
    *,
    multiple: int = 8,
    pad_color: tuple[int, int, int] = (0, 0, 0),
) -> PreparedImage:
    """Resize with aspect preserved, then letterbox-pad to exact WxH.

    Uses pad (not crop/stretch) so doors, TV, and walls are not distorted by
    forcing a fill crop.
    """
    src = source.convert("RGB")
    tw, th = compute_inference_size(src.width, src.height, max_side, multiple=multiple)

    # Fit inside target while preserving aspect (contain), then pad.
    contained = ImageOps.contain(src, (tw, th), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (tw, th), pad_color)
    left = (tw - contained.width) // 2
    top = (th - contained.height) // 2
    canvas.paste(contained, (left, top))
    box = (left, top, left + contained.width, top + contained.height)
    return PreparedImage(
        image=canvas,
        target_size=(tw, th),
        content_box=box,
        source_size=(src.width, src.height),
    )


def restore_from_diffusion(
    generated: Image.Image,
    prepared: PreparedImage,
    *,
    display_max_side: int,
) -> Image.Image:
    """Remove letterbox padding and restore to source aspect for display."""
    left, top, right, bottom = prepared.content_box
    cropped = generated.crop((left, top, right, bottom))
    # Return to original source proportions at a safe display size.
    sw, sh = prepared.source_size
    if max(sw, sh) > display_max_side:
        scale = display_max_side / max(sw, sh)
        sw = max(1, int(sw * scale))
        sh = max(1, int(sh * scale))
    return cropped.resize((sw, sh), Image.Resampling.LANCZOS)


def safe_postprocess(image: Image.Image, *, mild_sharpen: bool = True) -> Image.Image:
    """Safe color/mode cleanup. Mild sharpen only — never fake HD from mush."""
    out = image.convert("RGB")
    if mild_sharpen and min(out.size) >= 256:
        # Very light unsharp; does not invent detail lost at 320px.
        out = out.filter(ImageFilter.UnsharpMask(radius=0.8, percent=60, threshold=3))
    return out
