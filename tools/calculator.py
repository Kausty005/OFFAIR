"""
tools/calculator.py
Deterministic engineering calculation tool.
The agent calls this for numerical calculations instead of asking the LLM.
Results are 100% accurate — not LLM-generated.
"""

import math
import os
import sys
from dataclasses import dataclass
from typing import Optional, Union

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log


@dataclass
class CalcResult:
    formula: str
    inputs: dict
    result: float
    unit: str
    explanation: str
    source: str = "Deterministic local calculation"


def pump_efficiency(
    input_power_kw: float,
    output_power_kw: float,
) -> CalcResult:
    """Calculate pump mechanical efficiency."""
    if input_power_kw <= 0:
        raise ValueError("Input power must be > 0")
    efficiency = (output_power_kw / input_power_kw) * 100
    return CalcResult(
        formula="η = (P_out / P_in) × 100%",
        inputs={"input_power_kw": input_power_kw, "output_power_kw": output_power_kw},
        result=round(efficiency, 2),
        unit="%",
        explanation=f"Pump efficiency = ({output_power_kw} / {input_power_kw}) × 100 = {efficiency:.2f}%",
    )


def pressure_drop(
    flow_rate_lpm: float,
    pipe_length_m: float,
    pipe_diameter_mm: float,
    friction_factor: float = 0.02,
    fluid_density_kgm3: float = 1000.0,
) -> CalcResult:
    """
    Calculate pressure drop using Darcy-Weisbach equation.
    ΔP = f × (L/D) × (ρ × v²) / 2
    """
    D = pipe_diameter_mm / 1000  # m
    A = math.pi * (D / 2) ** 2  # m²
    Q = flow_rate_lpm / 60000  # m³/s
    v = Q / A  # m/s
    delta_p = friction_factor * (pipe_length_m / D) * (fluid_density_kgm3 * v**2) / 2
    delta_p_bar = delta_p / 1e5

    return CalcResult(
        formula="ΔP = f × (L/D) × (ρ × v²) / 2",
        inputs={
            "flow_rate_lpm": flow_rate_lpm,
            "pipe_length_m": pipe_length_m,
            "pipe_diameter_mm": pipe_diameter_mm,
            "friction_factor": friction_factor,
            "fluid_density_kgm3": fluid_density_kgm3,
        },
        result=round(delta_p_bar, 4),
        unit="bar",
        explanation=(
            f"Flow velocity = {v:.3f} m/s, "
            f"ΔP = {friction_factor} × ({pipe_length_m}/{D:.4f}) × "
            f"({fluid_density_kgm3} × {v:.3f}²) / 2 = {delta_p_bar:.4f} bar"
        ),
    )


def temperature_conversion(value: float, from_unit: str, to_unit: str) -> CalcResult:
    """Convert temperature between Celsius, Fahrenheit, and Kelvin."""
    from_unit = from_unit.upper()
    to_unit = to_unit.upper()

    # Convert to Celsius first
    if from_unit in ("C", "CELSIUS"):
        celsius = value
    elif from_unit in ("F", "FAHRENHEIT"):
        celsius = (value - 32) * 5 / 9
    elif from_unit in ("K", "KELVIN"):
        celsius = value - 273.15
    else:
        raise ValueError(f"Unknown unit: {from_unit}")

    # Convert from Celsius to target
    if to_unit in ("C", "CELSIUS"):
        result = celsius
    elif to_unit in ("F", "FAHRENHEIT"):
        result = celsius * 9 / 5 + 32
    elif to_unit in ("K", "KELVIN"):
        result = celsius + 273.15
    else:
        raise ValueError(f"Unknown unit: {to_unit}")

    return CalcResult(
        formula=f"{from_unit} → {to_unit}",
        inputs={"value": value, "from_unit": from_unit, "to_unit": to_unit},
        result=round(result, 2),
        unit=to_unit,
        explanation=f"{value} {from_unit} = {result:.2f} {to_unit}",
    )


def power_from_efficiency(
    input_power_kw: float,
    efficiency_percent: float,
) -> CalcResult:
    """Calculate output power given input power and efficiency."""
    output = input_power_kw * (efficiency_percent / 100)
    return CalcResult(
        formula="P_out = P_in × η",
        inputs={"input_power_kw": input_power_kw, "efficiency_percent": efficiency_percent},
        result=round(output, 2),
        unit="kW",
        explanation=f"Output power = {input_power_kw} kW × {efficiency_percent}% = {output:.2f} kW",
    )


def bearing_temperature_risk(temperature_celsius: float) -> CalcResult:
    """
    Assess bearing temperature risk level.
    Standard ranges:
    < 70°C: Normal
    70–85°C: Elevated — monitor closely
    85–95°C: Warning — schedule inspection
    > 95°C: Critical — immediate action required
    """
    if temperature_celsius < 70:
        risk = "NORMAL"
        score = 1.0
    elif temperature_celsius < 85:
        risk = "ELEVATED"
        score = 2.0
    elif temperature_celsius < 95:
        risk = "WARNING"
        score = 3.0
    else:
        risk = "CRITICAL"
        score = 4.0

    return CalcResult(
        formula="Bearing temperature risk assessment (ISO 10816)",
        inputs={"temperature_celsius": temperature_celsius},
        result=score,
        unit=f"Risk Level: {risk}",
        explanation=f"Bearing temperature {temperature_celsius}°C → {risk}. "
                   f"Threshold: <70°C Normal, 70-85°C Elevated, 85-95°C Warning, >95°C Critical.",
    )


import ast
import operator

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCS = {
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "pow": pow,
    "floor": math.floor,
    "ceil": math.ceil,
}

_SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _eval_ast_node(node: ast.AST, variables: dict) -> float:
    """Recursively evaluate an AST expression safely without eval()."""
    if isinstance(node, ast.Expression):
        return _eval_ast_node(node.body, variables)

    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"Disallowed constant value: {node.value}")

    elif isinstance(node, ast.Name):
        if node.id in variables:
            return float(variables[node.id])
        elif node.id in _SAFE_CONSTANTS:
            return _SAFE_CONSTANTS[node.id]
        raise ValueError(f"Undefined variable or constant: '{node.id}'")

    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in _SAFE_OPS:
            operand = _eval_ast_node(node.operand, variables)
            return float(_SAFE_OPS[op_type](operand))
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in _SAFE_OPS:
            left = _eval_ast_node(node.left, variables)
            right = _eval_ast_node(node.right, variables)
            return float(_SAFE_OPS[op_type](left, right))
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")

    elif isinstance(node, ast.Call):
        func = node.func
        func_name = ""
        if isinstance(func, ast.Name):
            func_name = func.id
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id == "math":
                func_name = func.attr
        if func_name in _SAFE_FUNCS:
            args = [_eval_ast_node(arg, variables) for arg in node.args]
            return float(_SAFE_FUNCS[func_name](*args))
        raise ValueError(f"Disallowed or unsupported function call: '{ast.dump(func)}'")

    raise ValueError(f"Disallowed AST expression element: {type(node).__name__}")


def evaluate_expression(expr: str, variables: dict = None) -> CalcResult:
    """
    Safely evaluate a mathematical expression using AST-based parsing.
    NO Python eval() is used. Only whitelisted math operations and functions are allowed.
    """
    cleaned = expr.strip().replace("^", "**")
    vars_dict = dict(variables or {})

    try:
        parsed_ast = ast.parse(cleaned, mode="eval")
        result = _eval_ast_node(parsed_ast, vars_dict)
        log("CALCULATION", expr=expr, result=result)
        return CalcResult(
            formula=expr,
            inputs=variables or {},
            result=round(result, 6),
            unit="",
            explanation=f"{expr} = {result}",
        )
    except Exception as e:
        raise ValueError(f"Could not evaluate expression '{expr}': {e}")

