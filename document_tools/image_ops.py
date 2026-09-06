"""
document_tools/image_ops.py
Local image operations: resize, convert, compress, crop, rotate, flip, batch.
Uses Pillow. Air-gap ready, no external services.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from PIL import Image, ImageOps

from document_tools.common import safe_filename, validate_image


def _open_image(data: bytes) -> Image.Image:
    validate_image(data)
    try:
        img = Image.open(io.BytesIO(data))
        return img
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot open image: {exc}")


def _save_image(img: Image.Image, fmt: str, quality: int = 85) -> bytes:
    fmt = fmt.upper()
    if fmt in ("JPG", "JPEG"):
        pil_fmt = "JPEG"
        if img.mode in ("RGBA", "LA", "P"):
            rgb = Image.new("RGB", img.size, (255, 255, 255))
            rgb.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = rgb
        elif img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    elif fmt == "PNG":
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    elif fmt == "WEBP":
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=quality)
        return buf.getvalue()
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported target format '{fmt}'. Choose JPG, PNG, or WEBP.")


def resize_image(
    data: bytes,
    width: Optional[int] = None,
    height: Optional[int] = None,
    scale_pct: Optional[float] = None,
    keep_aspect: bool = True,
) -> Tuple[bytes, Dict[str, Any]]:
    """Resize image with exact dimensions or scaling percentage."""
    img = _open_image(data)
    orig_w, orig_h = img.size
    orig_size = len(data)

    if scale_pct is not None and scale_pct > 0:
        factor = scale_pct / 100.0
        new_w = max(1, int(orig_w * factor))
        new_h = max(1, int(orig_h * factor))
    elif width and height:
        new_w, new_h = width, height
    elif width and not height:
        new_w = width
        new_h = max(1, int(orig_h * (width / orig_w))) if keep_aspect else orig_h
    elif height and not width:
        new_h = height
        new_w = max(1, int(orig_w * (height / orig_h))) if keep_aspect else orig_w
    else:
        raise HTTPException(status_code=400, detail="Specify width/height or scaling percentage")

    if new_w > 10000 or new_h > 10000:
        raise HTTPException(status_code=400, detail="Target dimensions exceed 10,000 pixels limit")

    resized = img.resize((new_w, new_h), Image.LANCZOS)
    out_bytes = _save_image(resized, img.format or "PNG")
    out_size = len(out_bytes)

    stats = {
        "original_dimensions": f"{orig_w} × {orig_h}",
        "output_dimensions": f"{new_w} × {new_h}",
        "original_size": orig_size,
        "output_size": out_size,
    }
    return out_bytes, stats


def convert_image(data: bytes, target_fmt: str = "PNG", quality: int = 85) -> Tuple[bytes, str, Dict[str, Any]]:
    """Convert image between JPG, PNG, and WebP formats."""
    img = _open_image(data)
    orig_fmt = img.format or "Unknown"
    orig_size = len(data)
    out_bytes = _save_image(img, target_fmt, quality=quality)
    out_size = len(out_bytes)

    ext = "jpg" if target_fmt.upper() in ("JPG", "JPEG") else target_fmt.lower()
    stats = {
        "original_format": orig_fmt,
        "output_format": target_fmt.upper(),
        "original_size": orig_size,
        "output_size": out_size,
        "dimensions": f"{img.width} × {img.height}",
    }
    return out_bytes, ext, stats


def compress_image(data: bytes, quality: int = 70) -> Tuple[bytes, Dict[str, Any]]:
    """Compress image by re-encoding with optimized quality parameters."""
    if quality < 1 or quality > 100:
        raise HTTPException(status_code=400, detail="Quality must be between 1 and 100")

    img = _open_image(data)
    orig_size = len(data)

    # If PNG, try WebP or optimized PNG
    fmt = "JPEG" if img.format in ("JPEG", "JPG") else "PNG"
    out_bytes = _save_image(img, fmt, quality=quality)
    out_size = len(out_bytes)

    # If compression ended up larger, keep original
    if out_size >= orig_size:
        final_bytes = data
        final_size = orig_size
        pct = 0.0
    else:
        final_bytes = out_bytes
        final_size = out_size
        pct = round(((orig_size - final_size) / orig_size) * 100.0, 1)

    stats = {
        "original_size": orig_size,
        "output_size": final_size,
        "reduction_pct": pct,
        "dimensions": f"{img.width} × {img.height}",
    }
    return final_bytes, stats


def crop_image(data: bytes, left: int, top: int, right: int, bottom: int) -> Tuple[bytes, Dict[str, Any]]:
    """Crop image with box coordinates (left, top, right, bottom)."""
    img = _open_image(data)
    w, h = img.size

    if left < 0 or top < 0 or right > w or bottom > h or left >= right or top >= bottom:
        raise HTTPException(status_code=400, detail=f"Invalid crop box. Image bounds are 0,0 to {w},{h}")

    cropped = img.crop((left, top, right, bottom))
    out_bytes = _save_image(cropped, img.format or "PNG")

    stats = {
        "original_dimensions": f"{w} × {h}",
        "output_dimensions": f"{cropped.width} × {cropped.height}",
        "output_size": len(out_bytes),
    }
    return out_bytes, stats


def rotate_flip_image(data: bytes, angle: int = 0, flip_h: bool = False, flip_v: bool = False) -> Tuple[bytes, Dict[str, Any]]:
    """Rotate image by 90/180/270 and/or flip horizontally/vertically."""
    img = _open_image(data)

    if angle not in (0, 90, 180, 270):
        raise HTTPException(status_code=400, detail="Angle must be 0, 90, 180, or 270")

    if angle > 0:
        # Pillow rotate counter-clockwise by default, 360-angle gives clockwise
        img = img.rotate(360 - angle, expand=True)

    if flip_h:
        img = ImageOps.mirror(img)
    if flip_v:
        img = ImageOps.flip(img)

    out_bytes = _save_image(img, img.format or "PNG")
    stats = {
        "output_dimensions": f"{img.width} × {img.height}",
        "output_size": len(out_bytes),
    }
    return out_bytes, stats


def batch_convert_images(files: List[Tuple[bytes, str]], target_fmt: str = "PNG", quality: int = 85) -> Dict[str, bytes]:
    """Convert a batch of images to the chosen target format."""
    target_ext = "jpg" if target_fmt.upper() in ("JPG", "JPEG") else target_fmt.lower()
    results: Dict[str, bytes] = {}

    for idx, (data, filename) in enumerate(files):
        try:
            converted, ext, _ = convert_image(data, target_fmt=target_fmt, quality=quality)
            base_name = safe_filename(filename, default=f"image_{idx+1}")
            # Strip old extension
            if "." in base_name:
                base_name = base_name.rsplit(".", 1)[0]
            out_name = f"{base_name}.{target_ext}"
            results[out_name] = converted
        except Exception:
            continue

    if not results:
        raise HTTPException(status_code=400, detail="No images could be converted in the batch")
    return results
