"""
Seven parallel sub-agents — each specialised on one domain.
All use Claude Haiku for speed; all return structured JSON dicts.
"""
from __future__ import annotations
import asyncio
import json
import anthropic
import config

_HAIKU = config.SUBAGENT_MODEL


async def _call(client: anthropic.AsyncAnthropic, system: str, user: str) -> dict:
    resp = await client.messages.create(
        model=_HAIKU,
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = resp.content[0].text.strip()
    # strip accidental markdown fences
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


# ── 1. Monitor Agent ──────────────────────────────────────────────────────────

_MONITOR_SYS = """You are the Grid Monitor Agent. Detect anomalies and faults.
Return ONLY valid JSON:
{
  "anomalies": [{"asset": "...", "type": "...", "severity": "LOW|MEDIUM|HIGH|CRITICAL"}],
  "fault_count": <int>,
  "recommend_emergency": <bool>,
  "summary": "<one sentence>"
}"""

async def monitor_agent(client, state: dict) -> tuple[str, dict]:
    payload = {
        "battery_units": state["battery_data"]["units"],
        "grid_stability": state["grid_data"]["grid_stability"],
        "frequency_hz": state["grid_data"]["frequency_hz"],
        "transmission_headroom_mw": state["grid_data"]["transmission_headroom_mw"],
        "storm_alert": state["external_data"]["storm_alert"],
    }
    result = await _call(client, _MONITOR_SYS,
                         f"Current readings:\n{json.dumps(payload, indent=2)}")
    return "monitor", result


# ── 2. Forecast Agent ─────────────────────────────────────────────────────────

_FORECAST_SYS = """You are the Forecast Agent. Synthesise generation and demand outlook.
Return ONLY valid JSON:
{
  "next_15min_generation_mw": <float>,
  "next_4hr_avg_generation_mw": <float>,
  "demand_trend": "RISING|STABLE|FALLING",
  "expected_surplus_mw": <float>,
  "confidence": "<LOW|MEDIUM|HIGH>",
  "summary": "<one sentence>"
}"""

async def forecast_agent(client, state: dict) -> tuple[str, dict]:
    payload = {
        "solar_forecast_mw": state["solar_data"]["total_forecast_mw"],
        "wind_forecast_mw": state["wind_data"]["total_forecast_mw"],
        "demand_forecast_mw": state["grid_data"]["demand_forecast_mw"],
        "uncertainties": state.get("uncertainties", {}),
        "weather": state["external_data"]["weather_condition"],
    }
    result = await _call(client, _FORECAST_SYS,
                         f"Forecast inputs:\n{json.dumps(payload, indent=2)}")
    return "forecast", result


# ── 3. Battery Agent ──────────────────────────────────────────────────────────

_BATTERY_SYS = """You are the Battery Management Agent.
Decide optimal battery actions considering state-of-charge, market prices, and grid conditions.
Minimise battery degradation while maximising value.
Return ONLY valid JSON:
{
  "actions": [
    {
      "unit_id": "BESS-1",
      "action": "CHARGE|DISCHARGE|RESERVE|HOLD",
      "power_mw": <float>,
      "duration_min": <int>,
      "reasoning": "<brief>"
    }
  ],
  "degradation_risk": "LOW|MEDIUM|HIGH",
  "summary": "<one sentence>"
}"""

async def battery_agent(client, state: dict) -> tuple[str, dict]:
    payload = {
        "units": state["battery_data"]["units"],
        "electricity_price": state["market_data"]["electricity_price_mwh"],
        "price_trend": state["market_data"]["price_trend"],
        "net_balance_mw": state["system_summary"]["net_balance_mw"],
        "operational_mode": state["operational_mode"],
        "objective_weights": state["objective_weights"],
        "risk_appetite": state.get("risk_appetite", "MODERATE"),
    }
    result = await _call(client, _BATTERY_SYS,
                         f"Battery context:\n{json.dumps(payload, indent=2)}")
    return "battery", result


# ── 4. Market Agent ───────────────────────────────────────────────────────────

_MARKET_SYS = """You are the Energy Market Agent.
Decide whether to buy, sell, or delay based on prices, surplus, and forecasts.
Return ONLY valid JSON:
{
  "action": "BUY|SELL|DELAY_SELL|HOLD",
  "volume_mw": <float>,
  "duration_min": <int>,
  "expected_revenue_usd": <float>,
  "reasoning": "<brief>",
  "carbon_credit_action": "SELL|HOLD|BUY",
  "summary": "<one sentence>"
}"""

async def market_agent(client, state: dict) -> tuple[str, dict]:
    payload = {
        "electricity_price": state["market_data"]["electricity_price_mwh"],
        "carbon_price": state["market_data"]["carbon_price_tonne"],
        "dr_incentive": state["market_data"]["demand_response_incentive_mwh"],
        "day_ahead_price": state["market_data"]["day_ahead_price_mwh"],
        "forecast_peak_price": state["market_data"]["forecast_peak_price_mwh"],
        "price_trend": state["market_data"]["price_trend"],
        "net_balance_mw": state["system_summary"]["net_balance_mw"],
        "objective_weights": state["objective_weights"],
        "price_forecast_uncertainty": state.get("uncertainties", {}).get("price_forecast", {}),
    }
    result = await _call(client, _MARKET_SYS,
                         f"Market context:\n{json.dumps(payload, indent=2)}")
    return "market", result


# ── 5. Generation Agent ───────────────────────────────────────────────────────

_GENERATION_SYS = """You are the Generation Management Agent.
Decide curtailment or prioritisation for solar and wind farms.
Prefer cleaner/cheaper sources. Only curtail if grid constraints force it.
Return ONLY valid JSON:
{
  "curtail_solar_mw": <float>,
  "curtail_wind_mw": <float>,
  "priority_source": "SOLAR|WIND|BALANCED",
  "reasoning": "<brief>",
  "transmission_risk": "LOW|MEDIUM|HIGH",
  "summary": "<one sentence>"
}"""

async def generation_agent(client, state: dict) -> tuple[str, dict]:
    payload = {
        "solar_output_mw": state["solar_data"]["total_output_mw"],
        "wind_output_mw": state["wind_data"]["total_output_mw"],
        "total_generation_mw": state["system_summary"]["total_generation_mw"],
        "transmission_limit_mw": state["grid_data"]["transmission_limit_mw"],
        "transmission_used_mw": state["grid_data"]["transmission_used_mw"],
        "transmission_headroom_mw": state["grid_data"]["transmission_headroom_mw"],
        "net_balance_mw": state["system_summary"]["net_balance_mw"],
        "objective_weights": state["objective_weights"],
    }
    result = await _call(client, _GENERATION_SYS,
                         f"Generation context:\n{json.dumps(payload, indent=2)}")
    return "generation", result


# ── 6. Demand Agent ───────────────────────────────────────────────────────────

_DEMAND_SYS = """You are the Demand Management Agent.
Decide demand response actions — shifting industrial loads, reducing non-critical loads.
Minimise disruption to critical consumers.
Return ONLY valid JSON:
{
  "demand_response_trigger": <bool>,
  "load_shift_mw": <float>,
  "load_reduce_mw": <float>,
  "targeted_consumers": ["<IND-id>"],
  "dr_revenue_usd": <float>,
  "reasoning": "<brief>",
  "summary": "<one sentence>"
}"""

async def demand_agent(client, state: dict) -> tuple[str, dict]:
    payload = {
        "current_demand_mw": state["grid_data"]["current_demand_mw"],
        "demand_forecast_mw": state["grid_data"]["demand_forecast_mw"],
        "industrial_consumers": state["grid_data"]["industrial_consumers"],
        "dr_incentive_mwh": state["market_data"]["demand_response_incentive_mwh"],
        "net_balance_mw": state["system_summary"]["net_balance_mw"],
        "operational_mode": state["operational_mode"],
        "objective_weights": state["objective_weights"],
    }
    result = await _call(client, _DEMAND_SYS,
                         f"Demand context:\n{json.dumps(payload, indent=2)}")
    return "demand", result


# ── 7. Maintenance Agent ──────────────────────────────────────────────────────

_MAINTENANCE_SYS = """You are the Maintenance Scheduling Agent.
Review scheduled maintenance and decide to proceed, defer, or expedite.
Consider operational mode — never defer safety-critical work.
Return ONLY valid JSON:
{
  "actions": [
    {
      "asset": "<asset_id>",
      "decision": "PROCEED|DEFER|EXPEDITE",
      "new_start": "<HH:MM or null>",
      "reasoning": "<brief>"
    }
  ],
  "inspection_dispatch": <bool>,
  "dispatch_assets": ["<asset_id>"],
  "summary": "<one sentence>"
}"""

async def maintenance_agent(client, state: dict) -> tuple[str, dict]:
    payload = {
        "scheduled_maintenance": state["external_data"]["maintenance_scheduled"],
        "battery_units": state["battery_data"]["units"],
        "operational_mode": state["operational_mode"],
        "storm_alert": state["external_data"]["storm_alert"],
        "grid_stability": state["grid_data"]["grid_stability"],
    }
    result = await _call(client, _MAINTENANCE_SYS,
                         f"Maintenance context:\n{json.dumps(payload, indent=2)}")
    return "maintenance", result


# ── Parallel runner ───────────────────────────────────────────────────────────

async def run_all_sub_agents(state: dict) -> dict:
    client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

    tasks = [
        monitor_agent(client, state),
        forecast_agent(client, state),
        battery_agent(client, state),
        market_agent(client, state),
        generation_agent(client, state),
        demand_agent(client, state),
        maintenance_agent(client, state),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    agent_outputs: dict = {}
    logs: list[str] = []

    for res in results:
        if isinstance(res, Exception):
            logs.append(f"[SubAgent ERROR] {res}")
            continue
        name, output = res
        agent_outputs[name] = output
        summary = output.get("summary", "")
        logs.append(f"[{name.upper()}] {summary}")

    return {
        "agent_outputs": agent_outputs,
        "agent_logs": logs,
    }


def run_sub_agents_sync(state: dict) -> dict:
    """Synchronous wrapper for use inside LangGraph nodes and Streamlit."""
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(run_all_sub_agents(state))
