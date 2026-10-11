# Renewable Energy Orchestrator
### ET AI Hackathon: Agentic Edition — Problem 4

An AI-powered multi-agent system that orchestrates renewable energy assets (solar, wind, battery storage) in real time using LangGraph, Claude AI, and Monte Carlo simulation.

---

## Architecture

```
Sensor Data → [LangGraph State Machine]
                ├── Situation Classifier (Claude Sonnet)
                ├── Uncertainty Quantifier (P10/P50/P90)
                ├── 7 Parallel Sub-Agents (Claude Haiku)
                │     monitor · forecast · battery · market
                │     generation · demand · maintenance
                ├── Conflict Resolver (Safety > Grid > Cost > Carbon)
                ├── Monte Carlo Simulator (30 runs × 16 cycles)
                └── Reporting Agent → Decision Brief
                                   ↓
                         Human-in-the-Loop Approval
```

## Key Features

- **Multi-agent parallelism** — 7 sub-agents execute simultaneously via `asyncio.gather`
- **LangGraph orchestration** — typed shared state machine with 8 nodes
- **4 operational modes** — NORMAL / STRESS / EMERGENCY / OPPORTUNITY
- **Conflict resolution** — explicit priority stack: Safety > Grid Stability > Cost > Carbon
- **Monte Carlo simulation** — 480 simulations per decision cycle (pure NumPy, instant)
- **HITL checkpoint** — no action executes without human approval
- **Demo Mode** — fully offline, no API key required

## Scenarios Supported

| Scenario | Mode | Description |
|---|---|---|
| NORMAL | NORMAL | Baseline operation |
| CLOUD_COVER | STRESS | Solar drops 80% |
| WIND_SURGE | OPPORTUNITY | Wind overproduction |
| PRICE_SPIKE | OPPORTUNITY | Sell at peak $149/MWh |
| BATTERY_FAILURE | STRESS | BESS-1 offline |
| TRANSMISSION_CAP | STRESS | Grid export constrained |
| DEMAND_SURGE | STRESS | Load 40% above forecast |
| CRISIS | EMERGENCY | Battery failure + demand surge + price spike |

## Setup

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set your Anthropic API key (or leave `DEMO_MODE=true` for offline demo).

## Run

```bash
# Streamlit dashboard
python -m streamlit run dashboard/app.py --server.headless true --browser.gatherUsageStats false

# CLI
python main.py --scenario CRISIS
```

## Tech Stack

- **LangGraph** — agent state machine orchestration
- **Anthropic Claude** — Sonnet (orchestrator) + Haiku (sub-agents)
- **Streamlit + Plotly** — real-time dashboard
- **NumPy** — Monte Carlo simulation
- **Python 3.11+**

## Validation

269/269 end-to-end tests passing across all 8 scenarios.
