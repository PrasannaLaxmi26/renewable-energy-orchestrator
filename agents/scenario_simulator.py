"""
Multi-Cycle Scenario Simulator — Step 5.
Runs a 4-hour forward Monte Carlo simulation (16 cycles × 30 runs)
and returns the Top-3 ranked action strategies.
Pure NumPy — no Claude call needed here.
"""
from __future__ import annotations
import numpy as np
import config

RNG = np.random.default_rng()


def _simulate_strategy(
    strategy_name: str,
    battery_action: str,   # "CHARGE" | "DISCHARGE" | "HOLD"
    sell_surplus: bool,
    curtail_pct: float,    # 0-1 fraction of surplus to curtail
    state: dict,
    n_cycles: int = config.SIMULATION_CYCLES,
    n_runs: int = config.MONTE_CARLO_RUNS,
) -> dict:
    price_base  = state["market_data"]["electricity_price_mwh"]
    demand_base = state["grid_data"]["current_demand_mw"]
    solar_base  = state["solar_data"]["total_output_mw"]
    wind_base   = state["wind_data"]["total_output_mw"]
    batt_soc    = state["battery_data"]["total_soc_mwh"]
    batt_cap    = state["battery_data"]["total_capacity_mwh"]
    batt_rate   = sum(b["max_discharge_mw"] for b in state["battery_data"]["units"] if b["online"])
    carbon_price = state["market_data"]["carbon_price_tonne"]

    costs_all = []
    carbon_all = []
    reliability_all = []
    curtailment_all = []

    for _ in range(n_runs):
        cost = 0.0
        carbon = 0.0
        shortfalls = 0
        curtailed = 0.0
        soc = batt_soc

        # random walk for each input
        solar_noise  = RNG.normal(1.0, 0.12, n_cycles)
        wind_noise   = RNG.normal(1.0, 0.15, n_cycles)
        price_noise  = RNG.normal(1.0, 0.18, n_cycles)
        demand_noise = RNG.normal(1.0, 0.08, n_cycles)

        for t in range(n_cycles):
            solar  = max(0, solar_base * solar_noise[t])
            wind   = max(0, wind_base  * wind_noise[t])
            price  = max(10, price_base * price_noise[t])
            demand = max(100, demand_base * demand_noise[t])

            gen = solar + wind
            surplus = gen - demand

            # apply curtailment
            if surplus > 0:
                curtail_mw = surplus * curtail_pct
                gen -= curtail_mw
                curtailed += curtail_mw
                surplus -= curtail_mw

            # battery action
            dt_h = 0.25  # 15 min in hours
            if battery_action == "CHARGE" and surplus > 0 and soc < batt_cap * 0.95:
                charge = min(surplus, batt_rate, (batt_cap - soc) / dt_h)
                soc = min(batt_cap, soc + charge * dt_h * 0.92)
                surplus -= charge
                cost -= 0  # using own generation

            elif battery_action == "DISCHARGE" and surplus < 0:
                discharge = min(abs(surplus), batt_rate, soc / dt_h)
                soc = max(0, soc - discharge * dt_h)
                surplus += discharge

            # sell remaining surplus
            if surplus > 0 and sell_surplus:
                revenue = surplus * price * dt_h
                cost -= revenue

            # buy shortfall from grid
            if surplus < 0:
                shortfalls += 1
                buy = abs(surplus) * price * dt_h
                cost += buy
                # carbon from grid purchase (avg 0.4 t/MWh)
                carbon += abs(surplus) * dt_h * 0.4

        costs_all.append(cost)
        carbon_all.append(carbon)
        reliability_all.append(1.0 - shortfalls / n_cycles)
        curtailment_all.append(curtailed)

    costs_arr     = np.array(costs_all)
    carbon_arr    = np.array(carbon_all)
    reliab_arr    = np.array(reliability_all)
    curtail_arr   = np.array(curtailment_all)

    weights = state.get("objective_weights", {})
    # normalised weighted score (lower is better for cost/carbon/curtailment, higher for reliability)
    score = (
        weights.get("cost", 0.25)                 * np.mean(costs_arr) / max(abs(np.mean(costs_arr)), 1)
        + weights.get("carbon", 0.20)             * np.mean(carbon_arr) / max(np.mean(carbon_arr), 1)
        - weights.get("reliability", 0.25)        * np.mean(reliab_arr)
        + weights.get("renewable_utilization", 0.20) * np.mean(curtail_arr) / max(solar_base + wind_base, 1)
    )

    return {
        "strategy": strategy_name,
        "battery_action": battery_action,
        "sell_surplus": sell_surplus,
        "curtail_pct": curtail_pct,
        "weighted_score": round(float(score), 4),
        "cost_p10": round(float(np.percentile(costs_arr, 10)), 0),
        "cost_p50": round(float(np.percentile(costs_arr, 50)), 0),
        "cost_p90": round(float(np.percentile(costs_arr, 90)), 0),
        "carbon_p50_tonnes": round(float(np.percentile(carbon_arr, 50)), 1),
        "reliability_p50_pct": round(float(np.percentile(reliab_arr, 50)) * 100, 1),
        "curtailment_p50_mwh": round(float(np.percentile(curtail_arr, 50)), 1),
        "horizon_hours": n_cycles * 0.25,
    }


def simulate_scenarios(state: dict) -> dict:
    strategies = [
        ("Cost-Optimised",        "DISCHARGE", True,  0.0),
        ("Reliability-First",     "CHARGE",    False, 0.0),
        ("Carbon-Minimal",        "CHARGE",    True,  0.1),
        ("Profit-Maximised",      "DISCHARGE", True,  0.0),
        ("Balanced",              "HOLD",      True,  0.05),
        ("Curtail & Store",       "CHARGE",    False, 0.20),
    ]

    results = [
        _simulate_strategy(name, bat, sell, curt, state)
        for name, bat, sell, curt in strategies
    ]

    # rank by weighted_score (lower = better)
    results.sort(key=lambda r: r["weighted_score"])
    top3 = results[:3]

    return {
        "simulation_scenarios": top3,
        "recommended_scenario_index": 0,
        "agent_logs": [
            f"[Simulator] {len(strategies)} strategies evaluated over 4h / {config.MONTE_CARLO_RUNS} Monte Carlo runs. "
            f"Best: '{top3[0]['strategy']}' (score={top3[0]['weighted_score']})"
        ],
    }
