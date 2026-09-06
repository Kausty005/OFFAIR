import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.calculator import evaluate_expression, pump_efficiency, temperature_conversion

def test_pump_efficiency():
    result = pump_efficiency(input_power_kw=100, output_power_kw=85)
    assert result.result == 85.0
    assert result.unit == "%"

def test_evaluate_expression():
    result = evaluate_expression("10 * 5 + 2")
    assert result.result == 52.0
    
    result = evaluate_expression("math.sqrt(16)")
    assert result.result == 4.0

def test_temperature_conversion():
    result = temperature_conversion(100, "C", "F")
    assert result.result == 212.0
    
    result2 = temperature_conversion(32, "F", "C")
    assert result2.result == 0.0
