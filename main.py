"""
CLI entry point — run one cycle or a multi-cycle 24-hour simulation.
Usage:
    python main.py                            # NORMAL scenario, single cycle
    python main.py --scenario CRISIS          # crisis demo, single cycle
    python main.py --scenario PRICE_SPIKE     # price spike, single cycle
    python main.py --simulate 96             # 24-hour simulation (96 x 15-min cycles)
    python main.py --simulate 4 --scenario CRISIS   # 1-hour crisis simulation
"""
from __future__ import annotations
import argparse
import sys

from data.mock_generator import generate_snapshot, Scenario, SCENARIO_DESCRIPTIONS
from agents.orchestrator import run_cycle


# ── single cycle print ────────────────────────────────────────────────────────

def print_cycle(result: dict, cycle_num: int = None, total: int = None) -> None:
    label = f"Cycle {cycle_num}/{total}" if cycle_num and total and total > 1 else "Cycle"
    print(f"\n{'─'*60}")
    print(f"  {label} | Mode: {result['operational_mode']} | "
          f"Balance: {result['system_summary']['net_balance_mw']:+.1f} MW | "
          f"Conflicts: {len(result['conflicts_detected'])}")
    print(f"{'─'*60}")
    if total == 1:
        print(f"\nExecutive Summary:\n  {result['executive_summary']}")
        print("\nResolved Actions:")
        for a in result["resolved_actions"]:
            print(f"  [{a['category']}] {a['action']} — {a['rationale']}")
        print("\nTop Scenario:")
        if result["simulation_scenarios"]:
            top = result["simulation_scenarios"][0]
            print(f"  Strategy    : {top['strategy']}")
            print(f"  Cost P50    : ${top['cost_p50']:,.0f}")
            print(f"  Reliability : {top['reliability_p50_pct']}%")
            print(f"  Carbon      : {top['carbon_p50_tonnes']:.1f} t")
        print("\nAgent Logs:")
        for log in result["agent_logs"]:
            print(f"  {log}")


# ── summary table ─────────────────────────────────────────────────────────────

def print_summary(results: list[dict]) -> None:
    print(f"\n{'='*90}")
    print(f"  24-HOUR SIMULATION SUMMARY — {len(results)} cycles x 15 min")
    print(f"{'='*90}")

    header = (
        f"  {'Cycle':>5}  {'Scenario':<16}  {'Mode':<11}  "
        f"{'Solar MW':>8}  {'Wind MW':>7}  {'Demand MW':>9}  "
        f"{'Price':>7}  {'SOC%':>5}  {'Conflicts':>9}  {'Best Strategy':<22}"
    )
    print(header)
    print(f"  {'-'*83}")

    mode_counts: dict[str, int] = {}
    total_conflicts = 0
    hitl_count = 0

    for i, r in enumerate(results):
        mode  = r["operational_mode"]
        solar = r["solar_data"]["total_output_mw"]
        wind  = r["wind_data"]["total_output_mw"]
        dem   = r["grid_data"]["current_demand_mw"]
        price = r["market_data"]["electricity_price_mwh"]
        soc   = r["battery_data"]["average_soc_pct"]
        scen  = r["scenario"]
        confs = len(r["conflicts_detected"])
        top_s = r["simulation_scenarios"][0]["strategy"] if r["simulation_scenarios"] else "-"
        hitl  = r.get("hitl_approved", False)

        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        total_conflicts += confs
        if hitl:
            hitl_count += 1

        print(
            f"  {i+1:>5}  {scen:<16}  {mode:<11}  "
            f"{solar:>8.1f}  {wind:>7.1f}  {dem:>9.1f}  "
            f"{price:>7.0f}  {soc:>5.1f}  {confs:>9}  {top_s:<22}"
        )

    print(f"\n{'='*90}")
    print(f"  Mode distribution : {dict(mode_counts)}")
    print(f"  Total conflicts   : {total_conflicts}")
    print(f"  HITL approvals    : {hitl_count}/{len(results)} cycles")
    if results and results[0]["simulation_scenarios"]:
        avg_cost = sum(
            r["simulation_scenarios"][0]["cost_p50"] for r in results
        ) / len(results)
        avg_carbon = sum(
            r["simulation_scenarios"][0]["carbon_p50_tonnes"] for r in results
        ) / len(results)
        print(f"  Avg cost P50      : ${avg_cost:,.0f}/cycle")
        print(f"  Avg carbon P50    : {avg_carbon:.1f} t/cycle")
    print(f"{'='*90}\n")


# ── SCENARIO ROTATION for multi-cycle ────────────────────────────────────────
# Mimics a realistic 24-hour day: morning surplus -> midday price spike ->
# afternoon demand surge -> evening normal -> night storm

_DAY_ROTATION = [
    "NORMAL",           # 00:00 - 01:00  (4 cycles)
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "WIND_SURGE",       # 01:00 - 03:00
    "WIND_SURGE",
    "WIND_SURGE",
    "WIND_SURGE",
    "NORMAL",           # 03:00 - 06:00
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "CLOUD_COVER",      # 06:00 - 08:00
    "CLOUD_COVER",
    "CLOUD_COVER",
    "CLOUD_COVER",
    "NORMAL",           # 08:00 - 10:00
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "PRICE_SPIKE",      # 10:00 - 12:00
    "PRICE_SPIKE",
    "PRICE_SPIKE",
    "PRICE_SPIKE",
    "DEMAND_SURGE",     # 12:00 - 14:00
    "DEMAND_SURGE",
    "DEMAND_SURGE",
    "DEMAND_SURGE",
    "NORMAL",           # 14:00 - 16:00
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "TRANSMISSION_CAP", # 16:00 - 18:00
    "TRANSMISSION_CAP",
    "TRANSMISSION_CAP",
    "TRANSMISSION_CAP",
    "BATTERY_FAILURE",  # 18:00 - 19:00
    "BATTERY_FAILURE",
    "BATTERY_FAILURE",
    "BATTERY_FAILURE",
    "CRISIS",           # 19:00 - 20:00  <- dramatic peak
    "CRISIS",
    "CRISIS",
    "CRISIS",
    "NORMAL",           # 20:00 - 24:00
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "WIND_SURGE",
    "WIND_SURGE",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
    "NORMAL",
]


def get_scenario_for_cycle(cycle: int, fixed_scenario: str, total: int) -> str:
    """Use day rotation for 96-cycle runs, fixed scenario for shorter runs."""
    if total == 96 and fixed_scenario == "NORMAL":
        return _DAY_ROTATION[cycle % 96]
    return fixed_scenario


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Renewable Energy Orchestrator CLI")
    parser.add_argument(
        "--scenario", default="NORMAL",
        choices=[s.value for s in Scenario],
        help="Energy system scenario (default: NORMAL)",
    )
    parser.add_argument(
        "--simulate", type=int, default=1, metavar="N",
        help="Number of 15-min cycles to run. Use 96 for a full 24-hour simulation.",
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Renewable Energy Orchestrator")
    print(f"  ET AI Hackathon - Problem 4")
    print(f"  Scenario : {args.scenario}  |  Cycles: {args.simulate}")
    if args.simulate == 96:
        print(f"  Mode     : 24-hour day simulation (scenario rotation enabled)")
    print(f"{'='*60}\n")

    results: list[dict] = []

    for cycle in range(args.simulate):
        scenario = get_scenario_for_cycle(cycle, args.scenario, args.simulate)

        if args.simulate > 1:
            print(f"  Running Cycle {cycle+1:>3}/{args.simulate}  [{scenario}]", end="\r", flush=True)

        snapshot = generate_snapshot(scenario)
        result   = run_cycle(snapshot)
        results.append(result)

        if args.simulate == 1:
            print_cycle(result, total=1)

    if args.simulate > 1:
        print()  # newline after \r
        print_summary(results)
    else:
        print(f"\n{'='*60}")
        print("  Cycle complete. Awaiting human approval (HITL).")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
