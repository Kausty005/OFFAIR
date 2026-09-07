import os
import sys
from pathlib import Path

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath("."))

from tools.docx_generator import create_maintenance_approval_note, docx_available

def test_approval_note_creation():
    print("==================================================")
    print("Testing Project Approval Note DOCX Generation")
    print("==================================================")
    
    assert docx_available(), "python-docx library is required!"
    
    output_dir = Path("workspace/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    target_path = output_dir / "test_approval_note_output.docx"
    
    result = create_maintenance_approval_note(
        equipment_name="Centrifugal Feed Pump P-102B",
        equipment_id="EQ-P102B-2026",
        inspection_date="2026-09-07",
        findings=[
            "Severe bearing temperature rise detected (88°C vs 65°C standard threshold).",
            "High frequency vibration observed at non-drive end bearing (8.4 mm/s).",
            "Minor mechanical seal leak observed during peak load."
        ],
        measurements={
            "Bearing Temperature": "88 °C",
            "Vibration Level": "8.4 mm/s",
            "Discharge Pressure": "14.2 bar",
            "Suction Pressure": "2.1 bar"
        },
        recommendations="Immediate replacement of non-drive end bearing assembly (6314 C3), seal replacement, and alignment check before restart.",
        sop_references=[
            {
                "document": "SOP-PUMP-MAINT-2025.pdf",
                "page": 14,
                "text": "Vibration > 7.1 mm/s requires emergency shutdown within 24 hours."
            }
        ],
        ai_reasoning="Critical risk flagged due to concurrent high temperature and elevated vibration.",
        output_path=target_path,
        risk_level="CRITICAL"
    )
    
    print(f"Result Success: {result['success']}")
    print(f"Generated Path: {result['path']}")
    print(f"File Size: {result.get('size', 0)} bytes")
    
    assert result["success"], f"Failed with error: {result.get('error')}"
    assert Path(result["path"]).exists(), "File does not exist!"
    assert result["size"] > 1000, "Generated file size is too small!"
    
    print("\nSUCCESS: Project successfully generated the Approval Note (.docx) file!")

if __name__ == "__main__":
    test_approval_note_creation()
