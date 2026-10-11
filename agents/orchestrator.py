"""
LangGraph Orchestrator — the central state machine.

Graph flow:
  START → aggregate → classify → quantify → run_agents
        → resolve → simulate → report → END

Each node updates the shared EnergySystemState.
The 'run_agents' node executes all 7 sub-agents in parallel via asyncio.

Set DEMO_MODE=true in .env to run without any API calls (offline/backup mode).
"""
from __future__ import annotations
import os
from typing import Any

from langgraph.graph import StateGraph, START, END

from core.state import EnergySystemState
from agents.situation_classifier import classify_situation
from agents.uncertainty_quantifier import quantify_uncertainty
from agents.sub_agents import run_sub_agents_sync
from agents.conflict_resolver import resolve_conflicts
from agents.scenario_simulator import simulate_scenarios
from agents.reporting_agent import generate_report
import agents.demo_mode as demo

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"


# ── Node implementations ──────────────────────────────────────────────────────

def aggregate_node(state: EnergySystemState) -> dict[str, Any]:
    """Validate incoming data and compute summary metrics."""
    solar  = state["solar_data"]
    wind   = state["wind_data"]
    grid   = state["grid_data"]

    total_gen = solar["total_output_mw"] + wind["total_output_mw"]
    net_bal   = round(total_gen - grid["current_demand_mw"], 2)

    return {
        "system_summary": {
            "total_generation_mw": round(total_gen, 2),
            "net_balance_mw": net_bal,
            "surplus": net_bal > 0,
        },
        "agent_logs": [
            f"[Aggregator] Gen={total_gen:.1f} MW | Demand={grid['current_demand_mw']:.1f} MW "
            f"| Balance={net_bal:+.1f} MW"
        ],
        "hitl_approved": False,
        "hitl_override": "",
        "conflicts_detected": [],
        "conflict_reasoning": "",
        "resolved_actions": [],
        "simulation_scenarios": [],
        "recommended_scenario_index": 0,
        "decision_brief": "",
        "executive_summary": "",
        "agent_outputs": {},
        "uncertainties": {},
        "cycle_metrics": {},
    }


def classify_node(state: EnergySystemState) -> dict[str, Any]:
    if DEMO_MODE:
        return demo.get_demo_classifier(state["scenario"])
    return classify_situation(state)


def quantify_node(state: EnergySystemState) -> dict[str, Any]:
    result = quantify_uncertainty(state)
    return {
        "uncertainties": result["uncertainties"],
        "risk_appetite": result["risk_appetite"],
        "avg_confidence": result["avg_confidence"],
        "agent_logs": result["agent_logs"],
    }


def run_agents_node(state: EnergySystemState) -> dict[str, Any]:
    if DEMO_MODE:
        outputs = demo.get_demo_sub_agents(state["scenario"], state)
        logs = [f"[{k.upper()}] {v.get('summary','')}" for k, v in outputs.items()]
        return {"agent_outputs": outputs, "agent_logs": logs}
    return run_sub_agents_sync(state)


def resolve_node(state: EnergySystemState) -> dict[str, Any]:
    if DEMO_MODE:
        r = demo.get_demo_conflict(state["scenario"])
        n = len(r["conflicts_detected"])
        return {**r, "agent_logs": [f"[ConflictResolver] {n} conflict(s) resolved (DEMO MODE)."]}
    return resolve_conflicts(state)


def simulate_node(state: EnergySystemState) -> dict[str, Any]:
    return simulate_scenarios(state)   # pure NumPy — always runs


def report_node(state: EnergySystemState) -> dict[str, Any]:
    if DEMO_MODE:
        return demo.get_demo_report(state["scenario"], state)
    return generate_report(state)


# ── Graph construction ─────────────────────────────────────────────────────────

def build_graph() -> Any:
    builder = StateGraph(EnergySystemState)

    builder.add_node("aggregate",   aggregate_node)
    builder.add_node("classify",    classify_node)
    builder.add_node("quantify",    quantify_node)
    builder.add_node("run_agents",  run_agents_node)
    builder.add_node("resolve",     resolve_node)
    builder.add_node("simulate",    simulate_node)
    builder.add_node("report",      report_node)

    builder.add_edge(START,        "aggregate")
    builder.add_edge("aggregate",  "classify")
    builder.add_edge("classify",   "quantify")
    builder.add_edge("quantify",   "run_agents")
    builder.add_edge("run_agents", "resolve")
    builder.add_edge("resolve",    "simulate")
    builder.add_edge("simulate",   "report")
    builder.add_edge("report",     END)

    return builder.compile()


# ── Public entry point ────────────────────────────────────────────────────────

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_cycle(snapshot: dict) -> EnergySystemState:
    """Run one 15-minute orchestration cycle and return the final state."""
    graph = get_graph()
    initial: EnergySystemState = {
        "cycle_id":       snapshot["cycle_id"],
        "timestamp":      snapshot["timestamp"],
        "scenario":       snapshot["scenario"],
        "solar_data":     snapshot["solar_data"],
        "wind_data":      snapshot["wind_data"],
        "battery_data":   snapshot["battery_data"],
        "grid_data":      snapshot["grid_data"],
        "market_data":    snapshot["market_data"],
        "external_data":  snapshot["external_data"],
        "system_summary":  snapshot.get("system_summary", {}),
        # fields populated by nodes
        "operational_mode": "",
        "objective_weights": {},
        "situation_reasoning": "",
        "uncertainties": {},
        "risk_appetite": "MODERATE",
        "avg_confidence": 0.8,
        "agent_outputs": {},
        "resolved_actions": [],
        "conflicts_detected": [],
        "conflict_reasoning": "",
        "simulation_scenarios": [],
        "recommended_scenario_index": 0,
        "decision_brief": "",
        "executive_summary": "",
        "agent_logs": [],
        "cycle_metrics": {},
        "hitl_approved": False,
        "hitl_override": "",
    }
    return graph.invoke(initial)
