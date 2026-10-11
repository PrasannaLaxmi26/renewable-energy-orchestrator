import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ORCHESTRATOR_MODEL = os.getenv("ORCHESTRATOR_MODEL", "claude-sonnet-4-5")
SUBAGENT_MODEL = os.getenv("SUBAGENT_MODEL", "claude-haiku-4-5-20251001")

SIMULATION_CYCLES = 16        # 4-hour forward horizon at 15-min intervals
MONTE_CARLO_RUNS = 30

SOLAR_FARMS = 5
WIND_FARMS = 3
BATTERIES = 2

OBJECTIVE_WEIGHT_PRESETS = {
    "NORMAL":      {"cost": 0.25, "carbon": 0.20, "reliability": 0.25, "renewable_utilization": 0.20, "profit": 0.10},
    "STRESS":      {"cost": 0.15, "carbon": 0.10, "reliability": 0.50, "renewable_utilization": 0.10, "profit": 0.15},
    "EMERGENCY":   {"cost": 0.05, "carbon": 0.05, "reliability": 0.80, "renewable_utilization": 0.05, "profit": 0.05},
    "OPPORTUNITY": {"cost": 0.20, "carbon": 0.15, "reliability": 0.15, "renewable_utilization": 0.20, "profit": 0.30},
}
