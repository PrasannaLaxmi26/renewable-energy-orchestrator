"""
Demo Mode — pre-canned AI responses for offline/backup demos.
Activated by setting DEMO_MODE=true in .env or environment.
Produces realistic, scenario-aware outputs without any API calls.
"""
from __future__ import annotations
import random

_CLASSIFIER_RESPONSES = {
    "NORMAL": {
        "operational_mode": "NORMAL",
        "objective_weights": {"cost": 0.25, "carbon": 0.20, "reliability": 0.25, "renewable_utilization": 0.20, "profit": 0.10},
        "situation_reasoning": "System is balanced with healthy solar and wind generation meeting demand. Battery reserves are adequate and market prices are within normal range. No alerts active.",
        "agent_logs": ["[Classifier] Mode=NORMAL | Urgency=2/10 | Drivers: ['stable generation', 'normal prices']"],
    },
    "CLOUD_COVER": {
        "operational_mode": "STRESS",
        "objective_weights": {"cost": 0.15, "carbon": 0.10, "reliability": 0.50, "renewable_utilization": 0.10, "profit": 0.15},
        "situation_reasoning": "Heavy cloud cover has reduced solar output to below 20% capacity, creating a generation shortfall. Battery discharge and potential grid import required. System is under stress.",
        "agent_logs": ["[Classifier] Mode=STRESS | Urgency=6/10 | Drivers: ['solar output 18% of capacity', 'generation shortfall 85MW']"],
    },
    "WIND_SURGE": {
        "operational_mode": "OPPORTUNITY",
        "objective_weights": {"cost": 0.20, "carbon": 0.15, "reliability": 0.15, "renewable_utilization": 0.20, "profit": 0.30},
        "situation_reasoning": "Wind output near maximum capacity with significant surplus generation. Electricity prices falling due to surplus. Opportunity to charge batteries and sell excess at favourable rates.",
        "agent_logs": ["[Classifier] Mode=OPPORTUNITY | Urgency=1/10 | Drivers: ['wind at 92% capacity', 'surplus 180MW', 'falling prices']"],
    },
    "PRICE_SPIKE": {
        "operational_mode": "OPPORTUNITY",
        "objective_weights": {"cost": 0.20, "carbon": 0.15, "reliability": 0.15, "renewable_utilization": 0.20, "profit": 0.30},
        "situation_reasoning": "Electricity prices have spiked to $130/MWh — well above average. Significant revenue opportunity by discharging batteries and selling surplus to the grid at peak rates.",
        "agent_logs": ["[Classifier] Mode=OPPORTUNITY | Urgency=3/10 | Drivers: ['price $130/MWh (+90% above avg)', 'discharge opportunity']"],
    },
    "BATTERY_FAILURE": {
        "operational_mode": "STRESS",
        "objective_weights": {"cost": 0.15, "carbon": 0.10, "reliability": 0.50, "renewable_utilization": 0.10, "profit": 0.15},
        "situation_reasoning": "BESS-1 has gone offline unexpectedly, reducing total battery capacity by 60%. Emergency reserve buffer is now insufficient. Grid reliability is the primary concern.",
        "agent_logs": ["[Classifier] Mode=STRESS | Urgency=7/10 | Drivers: ['BESS-1 offline', 'reserve capacity -60%', 'single battery point of failure']"],
    },
    "TRANSMISSION_CAP": {
        "operational_mode": "STRESS",
        "objective_weights": {"cost": 0.15, "carbon": 0.10, "reliability": 0.50, "renewable_utilization": 0.10, "profit": 0.15},
        "situation_reasoning": "Transmission line approaching rated capacity limit. Export of surplus renewable energy is constrained. Curtailment or battery storage are the primary options to prevent overload.",
        "agent_logs": ["[Classifier] Mode=STRESS | Urgency=6/10 | Drivers: ['transmission 94% of limit', 'export constrained', 'curtailment required']"],
    },
    "DEMAND_SURGE": {
        "operational_mode": "STRESS",
        "objective_weights": {"cost": 0.15, "carbon": 0.10, "reliability": 0.50, "renewable_utilization": 0.10, "profit": 0.15},
        "situation_reasoning": "Industrial demand has surged 35% above baseline unexpectedly, creating a significant shortfall. Demand response activation and battery discharge required immediately.",
        "agent_logs": ["[Classifier] Mode=STRESS | Urgency=7/10 | Drivers: ['demand +35% above baseline', 'shortfall -145MW', 'demand response needed']"],
    },
    "CRISIS": {
        "operational_mode": "EMERGENCY",
        "objective_weights": {"cost": 0.05, "carbon": 0.05, "reliability": 0.80, "renewable_utilization": 0.05, "profit": 0.05},
        "situation_reasoning": "CRITICAL: Multiple simultaneous failures. BESS-1 offline, storm approaching reducing renewable output, prices spiking to $145/MWh with demand rising. Grid stability is the only priority.",
        "agent_logs": ["[Classifier] Mode=EMERGENCY | Urgency=9/10 | Drivers: ['BESS-1 offline', 'storm imminent', 'price spike $145/MWh', 'demand rising']"],
    },
}

_CONFLICT_RESPONSES = {
    "NORMAL": {
        "resolved_actions": [
            {"category": "BATTERY", "action": "CHARGE at 40 MW using surplus solar", "value_mw_or_usd": 40, "priority": 3, "rationale": "Prices low, surplus available — build reserve for peak period"},
            {"category": "MARKET", "action": "HOLD — await peak price window at 14:00", "value_mw_or_usd": None, "priority": 4, "rationale": "Day-ahead prices forecast $18/MWh higher at 14:00"},
            {"category": "GENERATION", "action": "BALANCED — no curtailment required", "value_mw_or_usd": 0, "priority": 3, "rationale": "Transmission headroom 380 MW — no constraint"},
            {"category": "DEMAND", "action": "HOLD — demand response not triggered", "value_mw_or_usd": None, "priority": 4, "rationale": "Net balance positive, no intervention needed"},
            {"category": "MAINTENANCE", "action": "DEFER WIND-2 maintenance to 22:00 as scheduled", "value_mw_or_usd": None, "priority": 3, "rationale": "Wind output healthy, safe to defer 4 hours"},
        ],
        "conflicts_detected": [],
        "conflict_reasoning": "No conflicts between agent recommendations. All agents agree on a charge-and-hold strategy given current surplus and low prices.",
    },
    "CRISIS": {
        "resolved_actions": [
            {"category": "BATTERY", "action": "RESERVE BESS-2 at minimum 30% SOC emergency floor", "value_mw_or_usd": None, "priority": 1, "rationale": "Safety rule: maintain emergency reserve with only one BESS online"},
            {"category": "BATTERY", "action": "DISCHARGE BESS-2 at 35 MW (capped to preserve reserve)", "value_mw_or_usd": 35, "priority": 1, "rationale": "Grid stability requires immediate discharge; capped to protect emergency floor"},
            {"category": "MARKET", "action": "SELL 60 MW surplus at $145/MWh", "value_mw_or_usd": 60, "priority": 3, "rationale": "Override: Battery reserve rule takes priority; only sell above the floor"},
            {"category": "DEMAND", "action": "TRIGGER demand response — shift IND-1 (80 MW) and IND-3 (45 MW)", "value_mw_or_usd": 125, "priority": 1, "rationale": "Demand response closes 125 MW of shortfall; IND-2 is non-shiftable critical load"},
            {"category": "GENERATION", "action": "PRIORITISE wind — curtail solar 15 MW (storm reducing irradiance anyway)", "value_mw_or_usd": 15, "priority": 2, "rationale": "Wind more reliable during storm; solar output already degraded"},
            {"category": "MAINTENANCE", "action": "DEFER all maintenance — dispatch inspection to BESS-1", "value_mw_or_usd": None, "priority": 1, "rationale": "EMERGENCY mode: no maintenance during active crisis; diagnose BESS-1 failure"},
        ],
        "conflicts_detected": [
            "Battery agent: DISCHARGE fully vs Market agent: SELL all surplus — resolved by applying emergency reserve floor (Priority 1 over Priority 4)",
            "Market agent: maximise sell volume vs Reliability objective: maintain grid stability — resolved by prioritising grid stability",
            "Maintenance agent: proceed with WIND-2 scheduled maintenance vs EMERGENCY mode — overridden: defer all maintenance during active crisis",
        ],
        "conflict_reasoning": "Three conflicts detected. All resolved using the priority stack: Safety/Grid Stability (P1) overrode Profit (P4) in battery and market decisions. Emergency mode overrode scheduled maintenance. The resolved action set maintains grid stability while extracting partial market value from the price spike.",
    },
}


def get_demo_classifier(scenario: str) -> dict:
    base = _CLASSIFIER_RESPONSES.get(scenario, _CLASSIFIER_RESPONSES["NORMAL"])
    return dict(base)


def get_demo_sub_agents(scenario: str, state: dict) -> dict:
    net = state.get("system_summary", {}).get("net_balance_mw", 0)
    price = state.get("market_data", {}).get("electricity_price_mwh", 60)
    mode = state.get("operational_mode", "NORMAL")

    is_crisis = scenario in ("CRISIS", "BATTERY_FAILURE", "EMERGENCY")
    is_opp    = scenario in ("PRICE_SPIKE", "WIND_SURGE")

    return {
        "monitor": {
            "anomalies": [{"asset": "BESS-1", "type": "OFFLINE", "severity": "CRITICAL"}] if is_crisis else [],
            "fault_count": 1 if is_crisis else 0,
            "recommend_emergency": is_crisis,
            "summary": "BESS-1 offline — CRITICAL fault detected. Grid stability at risk." if is_crisis else "No anomalies detected. All assets operating within normal parameters.",
        },
        "forecast": {
            "next_15min_generation_mw": round(state.get("system_summary", {}).get("total_generation_mw", 400) * 0.97, 1),
            "next_4hr_avg_generation_mw": round(state.get("system_summary", {}).get("total_generation_mw", 400) * 0.94, 1),
            "demand_trend": "RISING" if is_crisis else ("STABLE" if not is_opp else "STABLE"),
            "expected_surplus_mw": round(net * 0.9, 1),
            "confidence": "LOW" if is_crisis else "HIGH",
            "summary": f"Generation expected to {'decline further as storm develops' if is_crisis else 'remain stable'}. Demand forecast {'rising' if is_crisis else 'stable'} over 4-hour horizon.",
        },
        "battery": {
            "actions": [
                {"unit_id": "BESS-1", "action": "OFFLINE", "power_mw": 0, "duration_min": 15, "reasoning": "Unit unavailable"} if is_crisis else
                {"unit_id": "BESS-1", "action": "CHARGE" if net > 30 else "DISCHARGE", "power_mw": round(min(abs(net) * 0.6, 75), 1), "duration_min": 15, "reasoning": f"{'Surplus available — charge at off-peak prices' if net > 30 else 'Discharging to cover shortfall'}"},
                {"unit_id": "BESS-2", "action": "DISCHARGE", "power_mw": 35, "duration_min": 15, "reasoning": "Emergency discharge — limited to preserve 30% reserve floor"} if is_crisis else
                {"unit_id": "BESS-2", "action": "CHARGE" if net > 30 else "HOLD", "power_mw": round(min(abs(net) * 0.4, 50), 1), "duration_min": 15, "reasoning": "Supporting primary battery action"},
            ],
            "degradation_risk": "HIGH" if is_crisis else "LOW",
            "summary": "Emergency discharge initiated on BESS-2 with reserve floor enforced. BESS-1 offline." if is_crisis else f"{'Charging' if net > 30 else 'Discharging'} both units to {'store surplus' if net > 30 else 'cover demand'}.",
        },
        "market": {
            "action": "SELL" if (is_opp or (is_crisis and net > 0)) else ("BUY" if net < -50 else "DELAY_SELL"),
            "volume_mw": round(max(abs(net) * 0.7, 20), 1),
            "duration_min": 15,
            "expected_revenue_usd": round(price * max(abs(net) * 0.7, 20) * 0.25, 0),
            "reasoning": f"Price ${price:.0f}/MWh is {'elevated — sell opportunity' if price > 80 else 'low — delay sell to peak window'}",
            "carbon_credit_action": "SELL" if is_opp else "HOLD",
            "summary": f"{'Selling' if price > 80 else 'Delaying sale'} at ${price:.0f}/MWh. Expected revenue ${price * max(abs(net) * 0.7, 20) * 0.25:,.0f}.",
        },
        "generation": {
            "curtail_solar_mw": 15.0 if is_crisis else (0.0 if net < 50 else round(net * 0.1, 1)),
            "curtail_wind_mw": 0.0,
            "priority_source": "WIND" if is_crisis else "BALANCED",
            "reasoning": "Curtail solar — storm reducing irradiance, wind more reliable. Prioritise wind during storm." if is_crisis else "No significant curtailment needed. Transmission headroom adequate.",
            "transmission_risk": "LOW" if net < 200 else "MEDIUM",
            "summary": "Curtailing 15 MW solar, prioritising wind generation during storm." if is_crisis else "Generation balanced — no curtailment required.",
        },
        "demand": {
            "demand_response_trigger": is_crisis or (net < -80),
            "load_shift_mw": 80.0 if is_crisis else (0.0 if net >= 0 else round(min(abs(net) * 0.4, 60), 1)),
            "load_reduce_mw": 45.0 if is_crisis else 0.0,
            "targeted_consumers": ["IND-1", "IND-3"] if is_crisis else [],
            "dr_revenue_usd": round(state.get("market_data", {}).get("demand_response_incentive_mwh", 20) * 125 * 0.25, 0) if is_crisis else 0,
            "reasoning": "Emergency demand response: shift IND-1 (80 MW shiftable) and reduce IND-3 (45 MW). IND-2 is non-shiftable critical load." if is_crisis else "No demand response needed — system balanced.",
            "summary": "Triggering demand response: shifting 80 MW + reducing 45 MW from industrial consumers." if is_crisis else "No demand response action required.",
        },
        "maintenance": {
            "actions": [
                {"asset": "BESS-1", "decision": "EXPEDITE", "new_start": "NOW", "reasoning": "Critical failure — dispatch repair team immediately"},
                {"asset": "WIND-2", "decision": "DEFER", "new_start": "06:00", "reasoning": "EMERGENCY mode — defer all non-safety maintenance"},
            ] if is_crisis else [
                {"asset": "WIND-2", "decision": "PROCEED", "new_start": "22:00", "reasoning": "Scheduled maintenance window — safe to proceed as planned"},
            ],
            "inspection_dispatch": is_crisis,
            "dispatch_assets": ["BESS-1"] if is_crisis else [],
            "summary": "Dispatching inspection team to BESS-1. Deferring scheduled WIND-2 maintenance until crisis resolved." if is_crisis else "Proceeding with scheduled WIND-2 maintenance at 22:00 as planned.",
        },
    }


def get_demo_conflict(scenario: str) -> dict:
    if scenario == "CRISIS":
        return _CONFLICT_RESPONSES["CRISIS"]
    elif scenario in ("BATTERY_FAILURE", "DEMAND_SURGE", "TRANSMISSION_CAP"):
        resp = dict(_CONFLICT_RESPONSES["CRISIS"])
        resp["conflicts_detected"] = resp["conflicts_detected"][:1]
        resp["conflict_reasoning"] = "One conflict detected and resolved using the priority stack."
        return resp
    return _CONFLICT_RESPONSES["NORMAL"]


def get_demo_report(scenario: str, state: dict) -> dict:
    mode = state.get("operational_mode", "NORMAL")
    net  = state.get("system_summary", {}).get("net_balance_mw", 0)
    price= state.get("market_data", {}).get("electricity_price_mwh", 60)
    top  = state.get("simulation_scenarios", [{}])[0]

    if scenario == "CRISIS":
        summary = (
            f"EMERGENCY: BESS-1 offline + storm approaching + prices at ${price:.0f}/MWh. "
            f"Demand response activated (125 MW shifted), BESS-2 discharging at 35 MW with emergency reserve floor. "
            f"Dispatching inspection team to BESS-1. Grid stability maintained."
        )
        brief = f"""## Situation
**EMERGENCY** — Multiple simultaneous failures at cycle `{state.get('cycle_id','')}`.

| Metric | Value |
|---|---|
| Net Balance | {net:+.1f} MW |
| BESS-1 | 🔴 OFFLINE |
| BESS-2 SoC | {state.get('battery_data',{}).get('average_soc_pct',45):.1f}% |
| Price | ${price:.0f}/MWh (SPIKE) |
| Storm Alert | 🌩️ ACTIVE |

## Recommended Actions
1. **[P1] Demand Response** — Shift IND-1 (80 MW) + reduce IND-3 (45 MW) = 125 MW demand reduction
2. **[P1] BESS-2 Discharge** — 35 MW with 30% emergency reserve floor enforced
3. **[P1] Dispatch** — Inspection team to BESS-1 for immediate diagnosis
4. **[P2] Generation** — Curtail 15 MW solar, prioritise wind (more reliable in storm)
5. **[P3] Market** — Sell 60 MW at ${price:.0f}/MWh above the reserve floor

## Top Strategy
**{top.get('strategy','Reliability-First')}** — Cost P50: ${top.get('cost_p50',0):,.0f} | Reliability: {top.get('reliability_p50_pct',95):.1f}% | Carbon: {top.get('carbon_p50_tonnes',12):.1f} t

## Risk & Uncertainty
- Solar forecast confidence: **LOW** (storm variability ±40%)
- Wind forecast confidence: **MEDIUM** (storm tracking uncertain ±25%)
- Single BESS point-of-failure risk: **HIGH** until BESS-1 restored

## Key Trade-offs
Selling at peak prices (${ price:.0f}/MWh) conflicts with maintaining battery emergency reserve.
**Resolution**: Cap sell volume at 60 MW, preserve BESS-2 reserve floor at 30%. Safety overrides profit (Priority 1 > Priority 4).
"""
    else:
        summary = (
            f"System operating in {mode} mode. Net balance {net:+.1f} MW. "
            f"Price ${price:.0f}/MWh — {'charging batteries and holding for peak window' if net > 0 else 'discharging to cover shortfall'}. "
            f"No active conflicts between agent recommendations."
        )
        brief = f"""## Situation
**{mode}** — Balanced operations at cycle `{state.get('cycle_id','')}`.

| Metric | Value |
|---|---|
| Total Generation | {state.get('system_summary',{}).get('total_generation_mw',400):.1f} MW |
| Grid Demand | {state.get('grid_data',{}).get('current_demand_mw',420):.1f} MW |
| Net Balance | {net:+.1f} MW |
| Price | ${price:.0f}/MWh |
| Battery SoC | {state.get('battery_data',{}).get('average_soc_pct',65):.1f}% |

## Recommended Actions
1. **{'Charge' if net > 0 else 'Discharge'} batteries** at {min(abs(net)*0.6,75):.0f} MW using {'surplus' if net > 0 else 'stored'} energy
2. **{'Delay sell' if price < 80 else 'Sell surplus'}** — {'await peak price window at 14:00' if price < 80 else f'price ${price:.0f}/MWh is favourable'}
3. **Proceed** with scheduled WIND-2 maintenance at 22:00 as planned

## Top Strategy
**{top.get('strategy','Balanced')}** — Cost P50: ${top.get('cost_p50',0):,.0f} | Reliability: {top.get('reliability_p50_pct',98):.1f}% | Carbon: {top.get('carbon_p50_tonnes',5):.1f} t

## Risk & Uncertainty
- All forecasts high confidence (>0.80)
- No single-asset dependency risks

## Key Trade-offs
No significant trade-offs in current cycle. Cost and reliability objectives are aligned — charging at low prices now maximises value at peak.
"""
    return {"executive_summary": summary, "decision_brief": brief,
            "agent_logs": ["[Reporter] Decision Brief generated (DEMO MODE). Awaiting HITL approval."]}
