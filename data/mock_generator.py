"""
Generates realistic energy system snapshots for every 15-minute cycle.
Supports 8 distinct scenarios that demonstrate different agent behaviours.
"""
from __future__ import annotations
import random
import uuid
from datetime import datetime
from enum import Enum


class Scenario(str, Enum):
    NORMAL           = "NORMAL"
    CLOUD_COVER      = "CLOUD_COVER"
    WIND_SURGE       = "WIND_SURGE"
    PRICE_SPIKE      = "PRICE_SPIKE"
    BATTERY_FAILURE  = "BATTERY_FAILURE"
    TRANSMISSION_CAP = "TRANSMISSION_CAP"
    DEMAND_SURGE     = "DEMAND_SURGE"
    CRISIS           = "CRISIS"          # battery failure + price spike combined


# ── helpers ──────────────────────────────────────────────────────────────────

def _jitter(value: float, pct: float = 0.05) -> float:
    return round(value * (1 + random.uniform(-pct, pct)), 2)


# ── per-scenario builders ─────────────────────────────────────────────────────

def _solar(scenario: Scenario) -> dict:
    farms = []
    capacities = [80, 95, 70, 110, 85]   # MW
    for i, cap in enumerate(capacities):
        if scenario == Scenario.CLOUD_COVER:
            output_pct = random.uniform(0.05, 0.20)
            forecast_pct = random.uniform(0.10, 0.30)
        elif scenario in (Scenario.PRICE_SPIKE, Scenario.DEMAND_SURGE, Scenario.CRISIS):
            output_pct = random.uniform(0.30, 0.55)
            forecast_pct = random.uniform(0.35, 0.60)
        else:
            output_pct = random.uniform(0.55, 0.85)
            forecast_pct = random.uniform(0.60, 0.88)

        farms.append({
            "id": f"SOLAR-{i+1}",
            "capacity_mw": cap,
            "output_mw": _jitter(cap * output_pct),
            "forecast_mw": _jitter(cap * forecast_pct),
            "irradiance_wm2": _jitter(800 * output_pct),
            "online": True,
        })
    return {
        "farms": farms,
        "total_output_mw": round(sum(f["output_mw"] for f in farms), 2),
        "total_forecast_mw": round(sum(f["forecast_mw"] for f in farms), 2),
        "total_capacity_mw": sum(capacities),
    }


def _wind(scenario: Scenario) -> dict:
    farms = []
    capacities = [120, 150, 100]   # MW
    for i, cap in enumerate(capacities):
        if scenario == Scenario.WIND_SURGE:
            output_pct = random.uniform(0.80, 0.98)
            forecast_pct = random.uniform(0.82, 0.99)
        elif scenario == Scenario.CLOUD_COVER:
            output_pct = random.uniform(0.60, 0.80)
            forecast_pct = random.uniform(0.62, 0.82)
        elif scenario == Scenario.CRISIS:
            output_pct = random.uniform(0.20, 0.40)
            forecast_pct = random.uniform(0.18, 0.38)
        else:
            output_pct = random.uniform(0.45, 0.75)
            forecast_pct = random.uniform(0.48, 0.78)

        farms.append({
            "id": f"WIND-{i+1}",
            "capacity_mw": cap,
            "output_mw": _jitter(cap * output_pct),
            "forecast_mw": _jitter(cap * forecast_pct),
            "wind_speed_ms": _jitter(12 * output_pct),
            "online": True,
        })
    return {
        "farms": farms,
        "total_output_mw": round(sum(f["output_mw"] for f in farms), 2),
        "total_forecast_mw": round(sum(f["forecast_mw"] for f in farms), 2),
        "total_capacity_mw": sum(capacities),
    }


def _battery(scenario: Scenario) -> dict:
    batteries = []
    for i in range(2):
        failed = (scenario in (Scenario.BATTERY_FAILURE, Scenario.CRISIS) and i == 0)
        soc = 0.0 if failed else random.uniform(0.25, 0.85)
        cap = [300, 200][i]  # MWh
        max_rate = [75, 50][i]  # MW

        batteries.append({
            "id": f"BESS-{i+1}",
            "capacity_mwh": cap,
            "soc_pct": round(soc * 100, 1),
            "soc_mwh": round(soc * cap, 1),
            "max_charge_mw": max_rate,
            "max_discharge_mw": max_rate,
            "charging_efficiency": 0.92,
            "degradation_pct": round(random.uniform(1.5, 4.5), 1),
            "online": not failed,
            "temperature_c": round(random.uniform(22, 38), 1),
        })
    return {
        "units": batteries,
        "total_capacity_mwh": sum(b["capacity_mwh"] for b in batteries),
        "total_soc_mwh": round(sum(b["soc_mwh"] for b in batteries), 1),
        "average_soc_pct": round(
            sum(b["soc_pct"] for b in batteries if b["online"]) /
            max(sum(1 for b in batteries if b["online"]), 1), 1
        ),
        "online_units": sum(1 for b in batteries if b["online"]),
    }


def _grid(scenario: Scenario) -> dict:
    base_demand = 420.0
    if scenario == Scenario.DEMAND_SURGE:
        demand = _jitter(base_demand * 1.35)
        forecast = _jitter(demand * 1.05)
    elif scenario == Scenario.CRISIS:
        demand = _jitter(base_demand * 1.25)
        forecast = _jitter(demand * 1.10)
    elif scenario == Scenario.TRANSMISSION_CAP:
        demand = _jitter(base_demand * 0.95)
        forecast = _jitter(demand * 1.02)
    else:
        demand = _jitter(base_demand)
        forecast = _jitter(demand * 1.02)

    tx_limit = 800.0
    tx_used = _jitter(550.0 if scenario == Scenario.TRANSMISSION_CAP else 420.0)

    return {
        "current_demand_mw": demand,
        "demand_forecast_mw": forecast,
        "frequency_hz": _jitter(50.0, 0.003),
        "transmission_limit_mw": tx_limit,
        "transmission_used_mw": tx_used,
        "transmission_headroom_mw": round(tx_limit - tx_used, 1),
        "grid_stability": "CRITICAL" if scenario == Scenario.TRANSMISSION_CAP else "STABLE",
        "industrial_consumers": [
            {"id": "IND-1", "demand_mw": _jitter(80), "shiftable": True},
            {"id": "IND-2", "demand_mw": _jitter(60), "shiftable": False},
            {"id": "IND-3", "demand_mw": _jitter(45), "shiftable": True},
        ],
    }


def _market(scenario: Scenario) -> dict:
    if scenario in (Scenario.PRICE_SPIKE, Scenario.CRISIS):
        price = _jitter(random.uniform(110, 160))
        carbon = _jitter(random.uniform(55, 80))
    elif scenario == Scenario.DEMAND_SURGE:
        price = _jitter(random.uniform(80, 120))
        carbon = _jitter(random.uniform(45, 65))
    elif scenario == Scenario.WIND_SURGE:
        price = _jitter(random.uniform(20, 40))  # prices drop with surplus
        carbon = _jitter(random.uniform(15, 30))
    else:
        price = _jitter(random.uniform(45, 75))
        carbon = _jitter(random.uniform(28, 50))

    dr_incentive = _jitter(random.uniform(15, 35))
    return {
        "electricity_price_mwh": price,
        "carbon_price_tonne": carbon,
        "demand_response_incentive_mwh": dr_incentive,
        "day_ahead_price_mwh": _jitter(price * 0.92),
        "price_trend": "RISING" if scenario in (Scenario.PRICE_SPIKE, Scenario.CRISIS, Scenario.DEMAND_SURGE) else
                       "FALLING" if scenario == Scenario.WIND_SURGE else "STABLE",
        "forecast_peak_price_mwh": _jitter(price * 1.20),
        "forecast_peak_time": "14:00-16:00",
    }


def _external(scenario: Scenario) -> dict:
    storm = scenario in (Scenario.CLOUD_COVER, Scenario.CRISIS)
    return {
        "weather_condition": "STORM" if storm else ("WINDY" if scenario == Scenario.WIND_SURGE else "CLEAR"),
        "temperature_c": _jitter(22),
        "cloud_cover_pct": 85 if scenario == Scenario.CLOUD_COVER else (_jitter(20) if storm else _jitter(10)),
        "wind_speed_forecast_ms": _jitter(18 if scenario == Scenario.WIND_SURGE else 9),
        "storm_alert": storm,
        "storm_severity": "MODERATE" if storm else None,
        "maintenance_scheduled": [
            {"asset": "WIND-2", "start": "22:00", "duration_hours": 4, "deferrable": True},
        ] if scenario not in (Scenario.CRISIS, Scenario.BATTERY_FAILURE) else [],
        "uv_index": _jitter(6),
    }


# ── public API ────────────────────────────────────────────────────────────────

def generate_snapshot(scenario: str = "NORMAL") -> dict:
    s = Scenario(scenario)
    now = datetime.now()

    solar   = _solar(s)
    wind    = _wind(s)
    battery = _battery(s)
    grid    = _grid(s)
    market  = _market(s)
    external= _external(s)

    total_gen = solar["total_output_mw"] + wind["total_output_mw"]
    net_balance = round(total_gen - grid["current_demand_mw"], 2)

    return {
        "cycle_id": str(uuid.uuid4())[:8].upper(),
        "timestamp": now.isoformat(timespec="seconds"),
        "scenario": scenario,
        "solar_data": solar,
        "wind_data": wind,
        "battery_data": battery,
        "grid_data": grid,
        "market_data": market,
        "external_data": external,
        # pre-computed summary for prompts
        "system_summary": {
            "total_generation_mw": round(total_gen, 2),
            "net_balance_mw": net_balance,
            "surplus": net_balance > 0,
        },
    }


SCENARIO_DESCRIPTIONS = {
    "NORMAL":           "Balanced conditions — moderate solar, wind, and stable prices.",
    "CLOUD_COVER":      "Heavy cloud cover reduces solar output to 5-20% of capacity.",
    "WIND_SURGE":       "Wind output near maximum; electricity prices dropping due to surplus.",
    "PRICE_SPIKE":      "Electricity prices spike to $110-160/MWh — sell opportunity.",
    "BATTERY_FAILURE":  "BESS-1 goes offline unexpectedly; reserve capacity reduced.",
    "TRANSMISSION_CAP": "Transmission line approaching capacity limit — export constrained.",
    "DEMAND_SURGE":     "Industrial demand surges 35% above baseline unexpectedly.",
    "CRISIS":           "Combined crisis: BESS-1 offline + price spike + storm approaching.",
}
