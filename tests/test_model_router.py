import os
import sys
from pathlib import Path

# Add project root to path for tests
sys.path.insert(0, str(Path(__file__).parent.parent))

from router.model_router import classify

def test_coding_routing():
    decision = classify("Write a python script to process data")
    assert decision.task_type == "coding"
    assert decision.selected_role == "coding"

def test_vision_routing():
    decision = classify("What is in this image?", has_image=True)
    assert decision.task_type == "vision"
    assert decision.selected_role == "vision"
    
    # Text only but mentions image
    decision2 = classify("Analyze this photo of a pump")
    assert decision2.task_type == "vision"

def test_calculation_routing():
    decision = classify("Calculate the pressure drop if flow rate is 100")
    assert decision.task_type == "calculation"

def test_document_routing():
    decision = classify("Summarize the findings in this report")
    assert decision.task_type == "document"
    
    # Uploaded PDF boosts document score
    decision2 = classify("What does it say?", has_pdf=True)
    assert decision2.task_type == "document"

def test_general_routing():
    decision = classify("What is the capital of France?")
    assert decision.task_type == "general"
