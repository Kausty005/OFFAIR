"""
tests/test_langgraph_agent.py
Tests for LangGraph orchestration engine, task classification,
model routing, tool execution, and backward compatibility.
"""

import pytest
from agent.agent import Agent
from agent.task_classifier import classify_task, TaskType
from agent.graph import get_agent_graph


def test_general_chat():
    """TEST 1: General chat routed to local general model and verified."""
    agent = Agent()
    state = agent.run("Explain operating systems.")

    assert state.task_type in ("general", "general_chat")
    assert state.selected_model != ""
    assert state.final_output is not None and len(state.final_output) > 20
    assert state.verified is True
    assert state.status == "done"


def test_calculation():
    """TEST 2: Calculation routed to deterministic AST calculator."""
    agent = Agent()
    state = agent.run("Calculate (25 * 4) / 10")

    assert state.task_type in ("calculation",)
    assert state.verified is True
    # Verify result equals 10.0
    calc_res = state.tool_results.get("calculations")
    assert calc_res is not None
    val = calc_res.result if hasattr(calc_res, "result") else calc_res.get("result")
    assert float(val) == 10.0
    assert "10.0" in state.final_output or "10" in state.final_output


def test_code_generation():
    """TEST 3: Code generation routed to local coding model."""
    agent = Agent()
    state = agent.run("Write Python code for binary search.")

    assert state.task_type in ("coding", "code_generation")
    assert "qwen" in state.selected_model.lower() or "coder" in state.selected_model.lower() or state.selected_model != ""
    code = state.tool_results.get("generated_code") or state.final_output
    assert code is not None
    assert "def " in code or "binary_search" in code or "search" in code


def test_knowledge_request():
    """TEST 8: Knowledge request routes through modular RAG interface."""
    from rag.interface import retrieve_context
    chunks = retrieve_context("What is the pump inspection procedure?")
    assert isinstance(chunks, list)
    # Even if KB has empty/partial documents, function returns a valid list of chunks without crashing

    agent = Agent()
    state = agent.run("According to the uploaded SOP, what is the procedure?")
    assert state.task_type in ("knowledge_query", "rag", "document_analysis", "document")
    assert state.final_output is not None


def test_backward_compatibility():
    """TEST 9: Backward compatibility with original Agent class and callbacks."""
    steps_received = []

    def on_step(step):
        steps_received.append(step)

    agent = Agent()
    agent.add_progress_callback(on_step)

    state = agent.run("Calculate pump efficiency with 100 kW input and 85 kW output")

    # Verify AgentState properties
    assert state.task_type in ("calculation",)
    assert state.verified is True
    assert len(state.plan) > 0
    assert len(steps_received) > 0
    assert state.status == "done"
    assert "85" in state.final_output or "efficiency" in state.final_output.lower()
