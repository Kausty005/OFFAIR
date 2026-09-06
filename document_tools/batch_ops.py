"""
document_tools/batch_ops.py
Reusable batch document processor with isolated per-file error handling.
Supports multi-file operations:
- pdf-to-txt
- compress-pdf
- pdf-to-images
- remove-metadata
- convert-images
- docx-to-txt
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Tuple

from fastapi import HTTPException

from document_tools.common import (
    create_zip_archive,
    safe_filename,
    validate_file_size,
)
from document_tools.image_ops import convert_image
from document_tools.office_ops import docx_to_text
from document_tools.pdf_ops import (
    compress_pdf,
    extract_text_from_pdf,
    remove_pdf_metadata,
    render_pdf_to_images,
)


def batch_process(
    files: List[Tuple[bytes, str]],
    operation: str,
    options: Dict[str, Any] = None,
) -> Tuple[Dict[str, bytes], Dict[str, Any]]:
    """
    Process a list of files sequentially.
    Never lets a single file failure crash the batch.
    Returns (output_files_dict, summary_stats).
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded for batch processing")

    opts = options or {}
    total_files = len(files)
    completed = 0
    failed = 0
    errors: List[Dict[str, str]] = []
    output_files: Dict[str, bytes] = {}

    for idx, (data, filename) in enumerate(files):
        safe_name = safe_filename(filename, default=f"file_{idx+1}")
        base_name = safe_name.rsplit(".", 1)[0] if "." in safe_name else safe_name

        try:
            validate_file_size(data, label=filename)

            if operation == "pdf-to-txt":
                text, _ = extract_text_from_pdf(data)
                out_name = f"{base_name}.txt"
                output_files[out_name] = text.encode("utf-8")

            elif operation == "compress-pdf":
                level = opts.get("level", "medium")
                compressed, _, _, _ = compress_pdf(data, level=level)
                out_name = f"{base_name}_compressed.pdf"
                output_files[out_name] = compressed

            elif operation == "remove-metadata":
                cleaned = remove_pdf_metadata(data)
                out_name = f"{base_name}_clean.pdf"
                output_files[out_name] = cleaned

            elif operation == "pdf-to-images":
                fmt = opts.get("format", "PNG")
                imgs = render_pdf_to_images(data, fmt=fmt, pages="all")
                for img_name, img_bytes in imgs.items():
                    output_files[f"{base_name}_{img_name}"] = img_bytes

            elif operation == "convert-images":
                target_fmt = opts.get("format", "PNG")
                quality = int(opts.get("quality", 85))
                converted, ext, _ = convert_image(data, target_fmt=target_fmt, quality=quality)
                out_name = f"{base_name}.{ext}"
                output_files[out_name] = converted

            elif operation == "docx-to-txt":
                text = docx_to_text(data)
                out_name = f"{base_name}.txt"
                output_files[out_name] = text.encode("utf-8")

            else:
                raise ValueError(f"Unknown batch operation: '{operation}'")

            completed += 1

        except Exception as exc:
            failed += 1
            errors.append({"file": filename, "error": str(exc)})

    summary = {
        "total_files": total_files,
        "completed": completed,
        "failed": failed,
        "operation": operation,
        "errors": errors,
    }

    return output_files, summary
