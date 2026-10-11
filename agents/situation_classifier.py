"""
Situation Classifier — Step 2a.
Reads the raw energy snapshot and classifies the operational mode,
then sets the objective weight vector accordingly.
"""
from __future__ import annotations
import json
import anthropic
import config
from config import OBJECTIVE_WEIGHT_PRESETS


_SYSTEM = """You are the Situation Classifier for a Renewable Energy Orchestrator.
Analyse the energy system snapshot and classify the operational mode.

Modes:
- NORMAL: balanced generation/demand, no alerts, stable prices
- STRESS: generation shortfall OR single asset failure OR moderate price pressure OR transmission approaching limits
- EMERGENCY: multiple simultaneous failures OR critical grid stability risk OR extreme price spikes with shortfall
- OPPORTUNITY: significant surplus renewable generation AND/OR very high prices that favour selling

Respond ONLY with valid JSON — no markdown, no extra text:
{
  "mode": "<NORMAL|STRESS|EMERGENCY|OPPORTUNITY>",
  "reasoning": "<2-3 concise sentences explaining the classification>",
  "key_drivers": ["<driver1>", "<driver2>"],
  "urgency_score": <1-10>
}"""


def classify_situation(state: dict) -> dict:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    summary = {
        "scenario": state["scenario"],
        "total_generation_mw": state["system_summary"]["total_generation_mw"],
        "total_demand_mw": state["grid_data"]["current_demand_mw"],
        "net_balance_mw": state["system_summary"]["net_balance_mw"],
        "battery_online_units": state["battery_data"]["online_units"],
        "battery_avg_soc_pct": state["battery_data"]["average_soc_pct"],
        "electricity_price_mwh": state["market_data"]["electricity_price_mwh"],
        "price_trend": state["market_data"]["price_trend"],
        "grid_stability": state["grid_data"]["grid_stability"],
        "transmission_headroom_mw": state["grid_data"]["transmission_headroom_mw"],
        "storm_alert": state["external_data"]["storm_alert"],
        "weather": state["external_data"]["weather_condition"],
    }

    response = client.messages.create(
        model=config.ORCHESTRATOR_MODEL,
        max_tokens=400,
        system=_SYSTEM,
        messages=[{"role": "user", "content": f"System snapshot:\n{json.dumps(summary, indent=2)}"}],
    )

    result = json.loads(response.content[0].text.strip())
    mode = result["mode"]
    weights = OBJECTIVE_WEIGHT_PRESETS.get(mode, OBJECTIVE_WEIGHT_PRESETS["NORMAL"])

    return {
        "operational_mode": mode,
        "objective_weights": weights,
        "situation_reasoning": result["reasoning"],
        "agent_logs": [f"[Classifier] Mode={mode} | Urgency={result['urgency_score']}/10 | Drivers: {result['key_drivers']}"],
    }
