# SIH26117 Demo Data

## ⚠️ IMPORTANT: This is fictional data for demonstration only.

All documents, equipment names, measurements, personnel names, and findings
in this directory are **completely invented** and used solely to demonstrate
the SIH26117 Sovereign AI Workbench prototype.

### Files

| File | Description |
|------|-------------|
| `inspection_report.pdf` | Fictional inspection report for a non-existent pump "P-104" |
| `maintenance_sop.pdf` | Fictional maintenance standard operating procedure |
| `safety_manual.pdf` | Fictional plant safety manual (rotating equipment section) |
| `inspection_image.jpg` | Fictional pump inspection diagram with annotations |

### Regenerating

```powershell
cd sih26117
python demo_data/generate_demo.py
```

### What the demo demonstrates

1. **Scanned PDF OCR** — the inspection report PDF is processed by local OCR
2. **RAG retrieval** — the SOP and safety manual are ingested into the knowledge base
3. **Vision analysis** — the inspection image is analyzed by the local vision model
4. **Agent workflow** — the full Plan→OCR→Extract→RAG→Reason→DOCX pipeline
5. **Local sovereignty** — no data leaves the machine at any point

### Fictional equipment details

- **Equipment**: "Crude Oil Transfer Pump" — DOES NOT EXIST
- **Tag**: "P-104" — FICTIONAL
- **Organization**: "DEMO Refinery Corporation" — FICTIONAL
- **Measurements**: All numbers are invented for demonstration
- **Personnel**: All names are invented

This data may only be used for SIH26117 prototype demonstration.
