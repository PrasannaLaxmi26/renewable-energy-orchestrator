"""
Conflict Resolution Engine — Step 4.
Applies a priority stack to reconcile contradictions between sub-agent recommendations
and produces a single coherent action set.

Priority stack (descending):
  1. Safety & Grid Stability
  2. Emergency Reserve (battery floor)
  3. Objective-weighted cost/carbon tradeoff
  4. Profit optimisation
"""
from __future__ import annotations
import json
import anthropic
import config


_SYSTEM = """You are the Conflict Resolution Engine for a Renewable Energy Orchestrator.

You receive recommendations from 7 specialist agents and must reconcile any conflicts
using the following priority stack (highest first):
  1. Safety & Grid Stability — always wins
  2. Emergency Battery Reserve — maintain ≥15% SOC on at least one BESS
  3. Objective-weighted optimisation (cost, carbon, reliability, renewable utilisation)
  4. Profit maximisation — lowest priority

Rules:
- If Battery says CHARGE but Market says SELL surplus: check net balance. If surplus >50 MW, allow partial sell + charge with remainder. If surplus <50 MW, prioritise charge for reliability.
- If Generation wants to curtail but Market wants full output: check transmission headroom. Curtail only if headroom <20 MW.
- Never recommend actions that violate the emergency reserve rule.
- If Maintenance says PROCEED during EMERGENCY mode: override to DEFER unless safety-critical.

Return ONLY valid JSON:
{
  "resolved_actions": [
    {
      "category": "BATTERY|MARKET|GENERATION|DEMAND|MAINTENANCE",
      "action": "<specific action>",
      "value_mw_or_usd": <float or null>,
      "priority": <1-4>,
      "rationale": "<one sentence>"
    }
  ],
  "conflicts_detected": ["<description of each conflict found>"],
  "conflict_reasoning": "<2-3 sentences explaining how conflicts were resolved>",
  "safety_check_passed": <bool>
}"""


def resolve_conflicts(state: dict) -> dict:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    payload = {
        "operational_mode": state["operational_mode"],
        "objective_weights": state["objective_weights"],
        "net_balance_mw": state["system_summary"]["net_balance_mw"],
        "transmission_headroom_mw": state["grid_data"]["transmission_headroom_mw"],
        "battery_avg_soc_pct": state["battery_data"]["average_soc_pct"],
        "battery_online_units": state["battery_data"]["online_units"],
        "agent_recommendations": state["agent_outputs"],
    }

    response = client.messages.create(
        model=config.ORCHESTRATOR_MODEL,
        max_tokens=900,
        system=_SYSTEM,
        messages=[{"role": "user", "content": f"Agent recommendations:\n{json.dumps(payload, indent=2)}"}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    result = json.loads(text)

    n_conflicts = len(result.get("conflicts_detected", []))
    logs = [f"[ConflictResolver] {n_conflicts} conflict(s) detected and resolved. Safety check: {'PASSED' if result.get('safety_check_passed') else 'FAILED'}"]

    return {
        "resolved_actions": result["resolved_actions"],
        "conflicts_detected": result.get("conflicts_detected", []),
        "conflict_reasoning": result.get("conflict_reasoning", ""),
        "agent_logs": logs,
    }
