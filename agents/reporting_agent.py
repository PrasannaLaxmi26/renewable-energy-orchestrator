"""
Reporting Agent — Step 6.
Synthesises all upstream outputs into a human-readable Decision Brief
for the HITL operator checkpoint.
"""
from __future__ import annotations
import json
import anthropic
import config


_SYSTEM = """You are the Reporting Agent for a Renewable Energy Orchestrator.
Produce a concise but complete Decision Brief for the human operator.

Format your response as JSON only:
{
  "executive_summary": "<2-3 sentence overview: situation, key actions, expected outcome>",
  "decision_brief": "<detailed markdown brief with sections: ## Situation, ## Recommended Actions, ## Top Strategy, ## Risk & Uncertainty, ## Key Trade-offs>"
}

The decision_brief must use markdown. Be specific — include MW values, USD amounts, % figures."""


def generate_report(state: dict) -> dict:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    top_scenario = (
        state["simulation_scenarios"][0]
        if state.get("simulation_scenarios") else {}
    )

    payload = {
        "cycle_id": state["cycle_id"],
        "timestamp": state["timestamp"],
        "scenario": state["scenario"],
        "operational_mode": state["operational_mode"],
        "situation_reasoning": state["situation_reasoning"],
        "objective_weights": state["objective_weights"],
        "total_generation_mw": state["system_summary"]["total_generation_mw"],
        "total_demand_mw": state["grid_data"]["current_demand_mw"],
        "net_balance_mw": state["system_summary"]["net_balance_mw"],
        "electricity_price_mwh": state["market_data"]["electricity_price_mwh"],
        "battery_soc_pct": state["battery_data"]["average_soc_pct"],
        "resolved_actions": state["resolved_actions"],
        "conflicts_detected": state["conflicts_detected"],
        "conflict_reasoning": state["conflict_reasoning"],
        "top_scenario": top_scenario,
        "uncertainties_summary": {
            k: {"confidence": v.get("confidence"), "p10": v.get("p10"), "p90": v.get("p90")}
            for k, v in state.get("uncertainties", {}).items()
        },
    }

    response = client.messages.create(
        model=config.ORCHESTRATOR_MODEL,
        max_tokens=1200,
        system=_SYSTEM,
        messages=[{"role": "user", "content": f"Full cycle data:\n{json.dumps(payload, indent=2)}"}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    result = json.loads(text)

    return {
        "executive_summary": result["executive_summary"],
        "decision_brief": result["decision_brief"],
        "agent_logs": ["[Reporter] Decision Brief generated. Awaiting HITL approval."],
    }
