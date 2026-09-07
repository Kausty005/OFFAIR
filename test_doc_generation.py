import os
import sys
from pathlib import Path

# Ensure root path in sys.path
sys.path.insert(0, os.path.abspath("."))

from agent.agent import Agent

def test_docx():
    print("\n--- Testing Word Document (.docx) Generation ---")
    agent = Agent()
    task = "Generate a word document summarizing standard industrial safety protocols"
    state = agent.run(task=task)
    print(f"Status: {state.status}")
    print(f"Output files: {state.output_files}")
    assert any(f.endswith(".docx") for f in state.output_files), "No .docx in output_files!"
    for f in state.output_files:
        if f.endswith(".docx"):
            p = Path(f)
            assert p.exists(), f"File {f} does not exist!"
            assert p.stat().st_size > 500, f"File {f} is too small ({p.stat().st_size} bytes)"
            print(f"Verified DOCX: {f} (Size: {p.stat().st_size} bytes)")

def test_pdf():
    print("\n--- Testing PDF Report (.pdf) Generation ---")
    agent = Agent()
    task = "Create a pdf report detailing boiler maintenance procedures"
    state = agent.run(task=task)
    print(f"Status: {state.status}")
    print(f"Output files: {state.output_files}")
    assert any(f.endswith(".pdf") for f in state.output_files), "No .pdf in output_files!"
    for f in state.output_files:
        if f.endswith(".pdf"):
            p = Path(f)
            assert p.exists(), f"File {f} does not exist!"
            assert p.stat().st_size > 500, f"File {f} is too small ({p.stat().st_size} bytes)"
            print(f"Verified PDF: {f} (Size: {p.stat().st_size} bytes)")

def test_pptx():
    print("\n--- Testing PowerPoint (.pptx) Generation ---")
    agent = Agent()
    task = "Create a ppt presentation about renewable energy transitions"
    state = agent.run(task=task)
    print(f"Status: {state.status}")
    print(f"Output files: {state.output_files}")
    assert any(f.endswith(".pptx") for f in state.output_files), "No .pptx in output_files!"
    for f in state.output_files:
        if f.endswith(".pptx"):
            p = Path(f)
            assert p.exists(), f"File {f} does not exist!"
            assert p.stat().st_size > 500, f"File {f} is too small ({p.stat().st_size} bytes)"
            print(f"Verified PPTX: {f} (Size: {p.stat().st_size} bytes)")

if __name__ == "__main__":
    test_docx()
    test_pdf()
    test_pptx()
    print("\nALL 3 DOCUMENT GENERATION TESTS PASSED SUCCESSFULLY!")
