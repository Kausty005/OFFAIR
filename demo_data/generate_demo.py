"""
Generate demo data for SIH26117.
Creates fictional industrial documents for demonstration purposes.
Run: python demo_data/generate_demo.py
"""

import os
import sys
import random
from pathlib import Path
from datetime import datetime

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

DEMO_DIR = Path(__file__).parent

# ─── Try fpdf2 (already installed) for PDF generation ─────────────────────────
try:
    from fpdf import FPDF
    _FPDF_AVAILABLE = True
except ImportError:
    _FPDF_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    import io
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# ─── FICTIONAL INSPECTION REPORT ──────────────────────────────────────────────

INSPECTION_REPORT_TEXT = """
INSPECTION REPORT
=================

[FICTIONAL/DEMO DATA - NOT REAL EQUIPMENT]

Organization: DEMO Refinery Corporation (FICTIONAL)
Plant / Unit: Crude Distillation Unit (CDU) - DEMO
Report No: IR-2024-1047 (FICTIONAL)
Date of Inspection: 2024-11-15
Inspector: J. Sharma (FICTIONAL)
Witness: R. Verma (FICTIONAL)

EQUIPMENT DETAILS
-----------------
Equipment Name: Crude Oil Transfer Pump
Equipment ID / Tag: P-104
Equipment Type: Centrifugal Pump
Service: Crude Oil Transfer (FICTIONAL)
Rated Flow: 250 m3/hr
Rated Head: 45 m
Motor Power: 55 kW
Last Maintenance: 2024-06-10

INSPECTION FINDINGS
-------------------

1. VIBRATION - ABNORMAL
   Vibration readings at pump discharge end: 8.7 mm/s (RMS)
   Acceptable limit: 4.5 mm/s
   Status: EXCEEDS LIMIT - Requires immediate attention
   
2. SEAL LEAKAGE - DETECTED
   Mechanical seal showing minor leakage at drive end
   Estimated leakage rate: 3-4 drops/minute
   Seal type: Single mechanical seal, Type A
   Status: DEGRADED - Schedule seal replacement

3. BEARING TEMPERATURE - ELEVATED
   Drive end bearing: 86 degrees Celsius
   Non-drive end bearing: 79 degrees Celsius
   Normal operating range: 55-75 degrees Celsius
   Status: ABOVE NORMAL - Monitor and schedule inspection

4. OPERATING PRESSURE
   Suction pressure: 2.1 bar
   Discharge pressure: 17.2 bar
   Differential pressure: 15.1 bar
   Rated differential pressure: 16.0 bar
   Status: SLIGHTLY BELOW RATED - Acceptable

5. NOISE - ABNORMAL
   Unusual metallic noise detected at non-drive end bearing
   Possible causes: Bearing wear, cavitation, misalignment
   Status: INVESTIGATE

6. COUPLING CONDITION
   Flexible coupling shows signs of rubber element wear
   Estimated remaining life: 3-6 months
   Status: MONITOR

SUMMARY
-------
Equipment P-104 shows multiple concurrent issues requiring maintenance attention.
The combination of elevated bearing temperature, abnormal vibration, and seal
leakage suggests possible bearing wear or misalignment condition.

RECOMMENDATIONS
---------------
1. Immediate: Reduce load on pump and increase monitoring frequency
2. Short-term (within 7 days): Replace mechanical seal
3. Short-term (within 14 days): Inspect and replace bearings if confirmed worn
4. Short-term: Re-align pump-motor coupling
5. Long-term: Schedule complete pump overhaul during next planned shutdown

RISK ASSESSMENT
---------------
Risk Level: HIGH
Consequences if not addressed: Potential pump failure, process disruption,
environmental release, safety hazard to personnel.

Inspector Signature: ______________ Date: 2024-11-15
Supervisor Review: ______________ Date: ____________

[THIS IS FICTIONAL DEMO DATA - ALL EQUIPMENT, MEASUREMENTS, AND FINDINGS ARE INVENTED]
"""


MAINTENANCE_SOP_TEXT = """
MAINTENANCE STANDARD OPERATING PROCEDURE
=========================================

[FICTIONAL/DEMO DOCUMENT - NOT REAL PROCEDURE]

Document No: SOP-MECH-042 (FICTIONAL)
Title: Centrifugal Pump Maintenance and Inspection Procedure
Revision: 4
Date: 2024-01-15
Approved By: Chief Engineer (FICTIONAL)

1. PURPOSE
----------
This procedure provides guidelines for inspection, maintenance, and 
overhaul of centrifugal pumps in process plants. This is a fictional 
demonstration document for SIH26117.

2. SCOPE
--------
Applicable to all centrifugal pumps in the CDU, VDU, and utility sections.
Equipment classes: P-100 to P-200 series.

3. BEARING INSPECTION AND REPLACEMENT
--------------------------------------
Section 3.1 - Temperature Limits
- Normal operating temperature: 55-75 degrees Celsius
- Warning threshold: 75-85 degrees Celsius (increase monitoring, schedule inspection)
- Action threshold: Above 85 degrees Celsius (immediate inspection required)
- Critical threshold: Above 95 degrees Celsius (immediate shutdown required)

Section 3.2 - Vibration Limits
- Acceptable: Below 4.5 mm/s RMS
- Warning: 4.5 - 7.0 mm/s RMS (schedule maintenance)
- Action required: Above 7.0 mm/s RMS (maintenance within 48 hours)

Section 3.3 - Bearing Replacement Procedure
Step 1: Isolate pump from process (close suction/discharge valves, de-energize motor)
Step 2: Lock-out-tag-out (LOTO) all energy sources
Step 3: Cool down to ambient temperature (minimum 2 hours after shutdown)
Step 4: Remove coupling guard and disconnect coupling
Step 5: Remove bearing housing cover
Step 6: Extract bearing using appropriate puller (do not hammer)
Step 7: Inspect shaft for scoring or wear
Step 8: Install new bearing (clean shaft, correct orientation)
Step 9: Pack with approved grease (3/4 filled only)
Step 10: Reassemble and torque all fasteners to specification
Step 11: Re-align pump-motor coupling (tolerance: +/- 0.05 mm)
Step 12: Run-in period: 2 hours at 50% load, monitor temperature and vibration

4. MECHANICAL SEAL MAINTENANCE
--------------------------------
Section 4.1 - Seal Inspection
Inspect for: leakage, heat marks, face damage, spring condition
Acceptable leakage: Less than 1 drop per minute (for standard seals)
Action leakage: 3 or more drops per minute (schedule replacement within 7 days)

Section 4.2 - Seal Replacement Procedure
Step 1: LOTO and isolate pump as per Section 3.3 Steps 1-3
Step 2: Drain pump casing
Step 3: Remove impeller (note: left-hand thread on most pumps in this plant)
Step 4: Remove seal gland plate and spring
Step 5: Slide out rotating seal faces
Step 6: Remove stationary seat from gland
Step 7: Clean all surfaces thoroughly
Step 8: Install new stationary seat (use assembly lubricant)
Step 9: Install new rotating assembly
Step 10: Set correct spring compression per manufacturer spec
Step 11: Reassemble pump
Step 12: Flush seal before startup (flush for 5 minutes minimum)

5. APPROVAL REQUIREMENTS
--------------------------
Section 5.1 - Work Authorization
All maintenance activities on process-critical equipment require:
- Written Work Order signed by Maintenance Supervisor
- Approval from Section Head for planned shutdowns
- Plant Manager approval for unplanned emergency shutdowns
- Safety officer sign-off for hot work

Section 5.2 - Documentation Requirements
- Complete inspection checklist before and after maintenance
- Record all measurements (temperature, vibration, alignment)
- Photograph key components before disassembly
- Update equipment history card

6. SAFETY PRECAUTIONS
-----------------------
- Always use LOTO before working on rotating equipment
- Wear appropriate PPE (safety glasses, gloves, hearing protection)
- Never work on energized equipment
- Ensure area is properly ventilated for hydrocarbon service
- Have spill kit available for oil leaks
- Emergency shower and eyewash within 10 seconds travel

[THIS IS FICTIONAL DEMO DATA]
"""


SAFETY_MANUAL_TEXT = """
PLANT SAFETY MANUAL - SECTION 7: ROTATING EQUIPMENT
=====================================================

[FICTIONAL/DEMO DOCUMENT]

Document: HSE-MAN-007 (FICTIONAL)
Revision: 2
Date: 2024-03-01

7.1 ROTATING EQUIPMENT HAZARDS
--------------------------------
Key hazards associated with pumps and rotating equipment:
a) Entanglement in rotating parts
b) High pressure fluid release
c) High temperature surfaces
d) Electrical hazards
e) Hydrocarbon release and fire risk
f) Noise-induced hearing loss

7.2 EQUIPMENT OPERATING LIMITS
--------------------------------
Temperature Alarms:
- High temperature alarm (TA-High): 85 degrees Celsius
- High-high temperature alarm (TA-HH): 95 degrees Celsius
- Automatic trip on high-high alarm

Vibration Alarms:
- High vibration alarm (VA-High): 7.0 mm/s
- High-high vibration alarm (VA-HH): 11.0 mm/s
- Automatic trip on high-high alarm

Pressure Monitoring:
- Suction pressure low (PA-Low): 0.5 bar
- Discharge pressure high (PA-High): 20 bar

7.3 EMERGENCY PROCEDURES
--------------------------
Pump Failure Emergency Response:
1. Immediately activate standby pump (if available)
2. Notify control room operator
3. Isolate failed pump using emergency isolation valves
4. Initiate shutdown procedure per SOP-MECH-042
5. Assess for any fluid release and contain if necessary
6. Notify section head and safety officer
7. Complete incident report within 2 hours

7.4 PERMIT-TO-WORK
-------------------
Required for all maintenance activities:
- Hot Work Permit for welding, grinding, cutting
- Confined Space Entry Permit for enclosed vessels
- Electrical Isolation Permit for electrical work
- General Work Permit for mechanical maintenance

[THIS IS FICTIONAL DEMO DATA - FOR DEMONSTRATION ONLY]
"""


def create_scanned_pdf(output_path: Path, text: str, title: str):
    """Create a PDF that looks like a scanned document."""
    if not _FPDF_AVAILABLE:
        print(f"fpdf2 not available — creating text file instead: {output_path}")
        output_path.with_suffix(".txt").write_text(text)
        return

    pdf = FPDF()
    pdf.set_margins(20, 20, 20)

    # Split text into pages (~50 lines per page)
    lines = text.split("\n")
    pages = []
    page = []
    for line in lines:
        page.append(line)
        if len(page) >= 48:
            pages.append(page)
            page = []
    if page:
        pages.append(page)

    for page_lines in pages:
        pdf.add_page()
        pdf.set_font("Courier", size=9)

        # Add slight rotation to simulate scan (not supported in fpdf2 easily, skip)
        for line in page_lines:
            # Truncate very long lines
            if len(line) > 100:
                line = line[:97] + "..."
            try:
                pdf.cell(0, 4, txt=line, ln=True)
            except Exception:
                pdf.cell(0, 4, txt=line.encode('ascii', errors='replace').decode(), ln=True)

    pdf.output(str(output_path))
    print(f"  Created: {output_path}")


def create_inspection_image(output_path: Path):
    """Create a fictional inspection photograph (diagram)."""
    if not _PIL_AVAILABLE:
        print(f"PIL not available — skipping image creation")
        return

    # Create a simple pump schematic diagram image
    width, height = 800, 600
    img = Image.new("RGB", (width, height), color=(240, 240, 230))
    draw = ImageDraw.Draw(img)

    # Background texture (simulate aged paper)
    for i in range(0, width, 20):
        draw.line([(i, 0), (i, height)], fill=(235, 235, 225), width=1)
    for j in range(0, height, 20):
        draw.line([(0, j), (width, j)], fill=(235, 235, 225), width=1)

    # Title
    draw.rectangle([20, 20, 780, 80], outline=(0, 0, 0), width=2)
    draw.text((30, 30), "EQUIPMENT INSPECTION PHOTOGRAPH", fill=(0, 0, 0))
    draw.text((30, 50), "Pump P-104 - FICTIONAL DEMO DATA", fill=(100, 0, 0))
    draw.text((500, 50), "Date: 2024-11-15", fill=(0, 0, 0))

    # Pump body (rectangle)
    draw.rectangle([150, 180, 450, 380], outline=(50, 50, 100), width=3, fill=(200, 210, 220))
    draw.text((230, 270), "PUMP BODY", fill=(0, 0, 80))
    draw.text((210, 290), "Equipment: P-104", fill=(0, 0, 80))

    # Motor (rectangle)
    draw.rectangle([470, 200, 720, 360], outline=(80, 50, 50), width=3, fill=(220, 200, 200))
    draw.text((540, 270), "MOTOR", fill=(80, 0, 0))
    draw.text((520, 290), "55 kW", fill=(80, 0, 0))

    # Coupling
    draw.rectangle([440, 255, 480, 305], outline=(0, 100, 0), width=2, fill=(150, 200, 150))
    draw.text((443, 275), "CLP", fill=(0, 80, 0))

    # Suction pipe
    draw.rectangle([50, 260, 150, 300], outline=(0, 0, 0), width=2, fill=(180, 180, 200))
    draw.text((60, 275), "SUCTION 2.1 bar", fill=(0, 0, 0))

    # Discharge pipe
    draw.rectangle([450, 220, 550, 260], outline=(0, 0, 0), width=2, fill=(180, 180, 200))
    draw.text((460, 232), "DISCH 17.2 bar", fill=(0, 0, 0))

    # Seal leak indicator (red marking)
    draw.ellipse([380, 300, 420, 340], outline=(255, 0, 0), width=3)
    draw.text((385, 315), "SEAL", fill=(255, 0, 0))
    draw.line([(420, 320), (500, 400)], fill=(255, 0, 0), width=2)
    draw.text((500, 400), "SEAL LEAKAGE\nDETECTED", fill=(255, 0, 0))

    # Bearing temperature annotation
    draw.text((160, 180), "BEARING TEMP: 86°C ⚠", fill=(200, 100, 0))
    draw.line([(240, 190), (240, 205)], fill=(200, 100, 0), width=2)

    # Vibration annotation
    draw.text((155, 390), "VIBRATION: 8.7 mm/s [EXCEEDS LIMIT]", fill=(180, 0, 0))

    # Observations box
    draw.rectangle([20, 440, 780, 570], outline=(0, 0, 0), width=2)
    draw.text((30, 450), "INSPECTOR OBSERVATIONS:", fill=(0, 0, 0))
    draw.text((30, 470), "1. Mechanical seal showing 3-4 drops/min leakage at drive end", fill=(0, 0, 0))
    draw.text((30, 488), "2. Bearing temperature elevated (86°C) - above normal range", fill=(0, 0, 0))
    draw.text((30, 506), "3. Abnormal vibration 8.7 mm/s (limit 4.5 mm/s)", fill=(0, 0, 0))
    draw.text((30, 524), "4. Metallic noise at NDE bearing", fill=(0, 0, 0))
    draw.text((30, 542), "[FICTIONAL DATA - FOR DEMONSTRATION ONLY]", fill=(150, 0, 0))

    # Watermark
    draw.text((200, 120), "DEMO / FICTIONAL", fill=(220, 220, 220))

    img.save(str(output_path), "JPEG", quality=85)
    print(f"  Created: {output_path}")


def main():
    DEMO_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating SIH26117 demo data...")
    print(f"Output directory: {DEMO_DIR}")
    print()

    print("Creating inspection_report.pdf (fictional scanned document)...")
    create_scanned_pdf(
        DEMO_DIR / "inspection_report.pdf",
        INSPECTION_REPORT_TEXT,
        "Inspection Report - P104",
    )

    print("Creating maintenance_sop.pdf (fictional SOP)...")
    create_scanned_pdf(
        DEMO_DIR / "maintenance_sop.pdf",
        MAINTENANCE_SOP_TEXT,
        "Maintenance SOP",
    )

    print("Creating safety_manual.pdf (fictional safety document)...")
    create_scanned_pdf(
        DEMO_DIR / "safety_manual.pdf",
        SAFETY_MANUAL_TEXT,
        "Safety Manual",
    )

    print("Creating inspection_image.jpg (fictional pump diagram)...")
    create_inspection_image(DEMO_DIR / "inspection_image.jpg")

    print()
    print("Done! All demo files created.")
    print()
    print("IMPORTANT: All files contain FICTIONAL data for demonstration only.")
    print("No real equipment, measurements, or safety procedures are represented.")


if __name__ == "__main__":
    main()
