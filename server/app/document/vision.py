"""
document/vision.py
Multimodal image understanding using local vision model via Ollama.
All processing is local — no cloud uploads.
"""

import os
import sys
from pathlib import Path
from typing import Optional

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log
from document.ocr import image_to_base64, image_file_to_base64
from models.model_registry import get_available_model
import models.ollama_client as ollama


VISION_SYSTEM_PROMPT = """You are an industrial inspection AI assistant analyzing images for maintenance and safety purposes.
Your analysis should be:
- Factual and observation-based
- Focused on maintenance-relevant details
- Conservative — do not speculate beyond what is visually evident
- Clearly structured

Always end your analysis with: "AI-generated observations — require human verification before any maintenance action."
"""


def analyze_image_file(
    image_path: str | Path,
    prompt: str = "Analyze this inspection image and identify visible maintenance observations.",
    model: Optional[str] = None,
) -> dict:
    """
    Analyze an image file using the local vision model.
    Returns structured analysis result.
    """
    model_name = model or get_available_model("vision") or "llava-phi3:latest"
    image_path = Path(image_path)

    if not image_path.exists():
        return {"error": f"Image file not found: {image_path}", "text": ""}

    # Convert to base64
    b64 = image_file_to_base64(image_path)
    if not b64:
        return {"error": "Could not read image file", "text": ""}

    log("VISION_ANALYSIS", model=model_name, file=image_path.name, local=True)

    try:
        response = ollama.generate(
            model=model_name,
            prompt=prompt,
            system=VISION_SYSTEM_PROMPT,
            images=[b64],
            temperature=0.1,
            max_tokens=1024,
        )
        log("VISION_DONE", model=model_name, chars=len(response))
        return {
            "model": model_name,
            "file": str(image_path),
            "prompt": prompt,
            "text": response,
            "local": True,
            "cloud": False,
        }
    except Exception as e:
        log("VISION_ERROR", model=model_name, error=str(e))
        return {
            "error": str(e),
            "text": f"Vision analysis failed: {e}",
            "model": model_name,
            "local": True,
        }


def analyze_pil_image(
    pil_image,
    prompt: str = "Analyze this image and describe what you observe.",
    model: Optional[str] = None,
) -> dict:
    """Analyze a PIL Image object using local vision model."""
    model_name = model or get_available_model("vision") or "llava-phi3:latest"

    b64 = image_to_base64(pil_image)
    if not b64:
        return {"error": "Could not encode image", "text": ""}

    log("VISION_ANALYSIS", model=model_name, source="pil_image", local=True)
    try:
        response = ollama.generate(
            model=model_name,
            prompt=prompt,
            system=VISION_SYSTEM_PROMPT,
            images=[b64],
            temperature=0.1,
            max_tokens=1024,
        )
        return {
            "model": model_name,
            "text": response,
            "local": True,
            "cloud": False,
        }
    except Exception as e:
        log("VISION_ERROR", model=model_name, error=str(e))
        return {"error": str(e), "text": f"Vision analysis failed: {e}"}


def analyze_scanned_pdf_page(
    page_dict: dict,
    prompt: str = "Extract all text and information from this document page.",
    model: Optional[str] = None,
) -> str:
    """
    Analyze a scanned PDF page using the vision model.
    page_dict: page object from pdf_processor with 'image' key.
    Returns extracted text.
    """
    img = page_dict.get("image")
    if img is None:
        return page_dict.get("text", "")

    result = analyze_pil_image(img, prompt=prompt, model=model)
    return result.get("text", page_dict.get("text", ""))
