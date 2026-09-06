"""
agent/state.py
AgentState dataclass — the full execution context of a running agent task.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime, timezone


@dataclass
class AgentStep:
    """A single step in the agent's execution plan."""
    index: int
    description: str
    tool: Optional[str] = None
    status: str = "pending"   # pending | running | done | error | skipped
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def start(self):
        self.status = "running"
        self.started_at = datetime.now(timezone.utc).isoformat()

    def complete(self, result: Any = None):
        self.status = "done"
        self.result = result
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def fail(self, error: str):
        self.status = "error"
        self.error = error
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def skip(self, reason: str = ""):
        self.status = "skipped"
        self.error = reason
        self.completed_at = datetime.now(timezone.utc).isoformat()


@dataclass
class AgentState:
    """Complete state of an agent execution run."""

    # Input
    task: str = ""
    uploaded_files: list[str] = field(default_factory=list)

    # Planning
    plan: list[AgentStep] = field(default_factory=list)
    current_step_index: int = 0

    # Results
    tool_results: dict[str, Any] = field(default_factory=dict)
    extracted_data: dict[str, Any] = field(default_factory=dict)
    rag_sources: list[dict] = field(default_factory=list)
    final_output: Optional[str] = None
    output_files: list[str] = field(default_factory=list)

    # Routing
    task_type: str = "general"
    selected_model: str = ""
    routing_reason: str = ""

    # Status
    status: str = "idle"  # idle | planning | running | done | error
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Verification
    verified: bool = False
    verification_notes: list[str] = field(default_factory=list)

    def start(self):
        self.status = "running"
        self.started_at = datetime.now(timezone.utc).isoformat()

    def complete(self, output: str = ""):
        self.status = "done"
        self.final_output = output
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def fail(self, error: str):
        self.status = "error"
        self.error = error
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def add_step(self, description: str, tool: Optional[str] = None) -> AgentStep:
        step = AgentStep(
            index=len(self.plan),
            description=description,
            tool=tool,
        )
        self.plan.append(step)
        return step

    def current_step(self) -> Optional[AgentStep]:
        if self.current_step_index < len(self.plan):
            return self.plan[self.current_step_index]
        return None

    def advance(self):
        self.current_step_index += 1

    def get_completed_steps(self) -> list[AgentStep]:
        return [s for s in self.plan if s.status == "done"]

    def get_failed_steps(self) -> list[AgentStep]:
        return [s for s in self.plan if s.status == "error"]

    def to_summary(self) -> dict:
        return {
            "task": self.task[:100],
            "status": self.status,
            "steps_total": len(self.plan),
            "steps_done": len(self.get_completed_steps()),
            "steps_failed": len(self.get_failed_steps()),
            "task_type": self.task_type,
            "model": self.selected_model,
            "output_files": self.output_files,
            "verified": self.verified,
        }
