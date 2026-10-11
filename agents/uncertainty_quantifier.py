"""
Uncertainty Quantifier — Step 2b.
Computes forecast confidence intervals for each data stream
and derives a risk-appetite flag used by sub-agents.
"""
from __future__ import annotations
import math


def _confidence(forecast: float, actual: float, base_sigma_pct: float) -> dict:
    error_pct = abs(forecast - actual) / max(actual, 1) * 100
    sigma = forecast * base_sigma_pct
    conf = max(0.30, min(0.99, 1.0 - (error_pct / 100)))
    return {
        "value": round(forecast, 2),
        "sigma": round(sigma, 2),
        "p10": round(forecast - 1.28 * sigma, 2),
        "p90": round(forecast + 1.28 * sigma, 2),
        "confidence": round(conf, 3),
    }


def quantify_uncertainty(state: dict) -> dict:
    solar  = state["solar_data"]
    wind   = state["wind_data"]
    grid   = state["grid_data"]
    market = state["market_data"]
    ext    = state["external_data"]

    storm_factor = 1.8 if ext["storm_alert"] else 1.0
    cloud_factor = 1.6 if ext["cloud_cover_pct"] > 60 else 1.0

    uncertainties = {
        "solar_forecast": _confidence(
            solar["total_forecast_mw"], solar["total_output_mw"],
            0.12 * storm_factor * cloud_factor
        ),
        "wind_forecast": _confidence(
            wind["total_forecast_mw"], wind["total_output_mw"],
            0.15 * storm_factor
        ),
        "demand_forecast": _confidence(
            grid["demand_forecast_mw"], grid["current_demand_mw"],
            0.08
        ),
        "price_forecast": _confidence(
            market["forecast_peak_price_mwh"], market["electricity_price_mwh"],
            0.20
        ),
    }

    avg_conf = sum(u["confidence"] for u in uncertainties.values()) / len(uncertainties)
    risk_appetite = "CONSERVATIVE" if avg_conf < 0.65 else ("MODERATE" if avg_conf < 0.82 else "AGGRESSIVE")

    return {
        "uncertainties": uncertainties,
        "agent_logs": [
            f"[Uncertainty] Avg confidence={avg_conf:.2f} → Risk appetite={risk_appetite}"
        ],
        # attach to state for sub-agents to use
        "risk_appetite": risk_appetite,
        "avg_confidence": avg_conf,
    }
