from __future__ import annotations
import operator
from typing import Annotated, Any
from typing_extensions import TypedDict


class EnergySystemState(TypedDict):
    # ── Identity ──────────────────────────────────────────────────────────────
    cycle_id: str
    timestamp: str
    scenario: str

    # ── Layer 1: raw sensor data ───────────────────────────────────────────────
    solar_data: dict[str, Any]
    wind_data: dict[str, Any]
    battery_data: dict[str, Any]
    grid_data: dict[str, Any]
    market_data: dict[str, Any]
    external_data: dict[str, Any]

    # ── Step 2a: Situation classification ─────────────────────────────────────
    operational_mode: str          # NORMAL | STRESS | EMERGENCY | OPPORTUNITY
    objective_weights: dict[str, float]
    situation_reasoning: str

    # ── Step 2b: Uncertainty quantification ───────────────────────────────────
    uncertainties: dict[str, dict[str, float]]   # {stream: {value, sigma, confidence}}

    # ── Step 3: Sub-agent recommendations ────────────────────────────────────
    agent_outputs: dict[str, dict[str, Any]]

    # ── Step 4: Conflict resolution ───────────────────────────────────────────
    resolved_actions: list[dict[str, Any]]
    conflicts_detected: list[str]
    conflict_reasoning: str

    # ── Step 5: Scenario simulation ───────────────────────────────────────────
    simulation_scenarios: list[dict[str, Any]]   # Top-3 ranked
    recommended_scenario_index: int

    # ── Step 6: Reporting ─────────────────────────────────────────────────────
    decision_brief: str
    executive_summary: str

    # ── Internal computed summaries (set by aggregate_node, used by all agents) ─
    system_summary: dict[str, Any]      # total_generation_mw, net_balance_mw, surplus
    risk_appetite: str                  # CONSERVATIVE | MODERATE | AGGRESSIVE
    avg_confidence: float

    # ── Metadata ──────────────────────────────────────────────────────────────
    agent_logs: Annotated[list[str], operator.add]
    cycle_metrics: dict[str, float]
    hitl_approved: bool
    hitl_override: str
