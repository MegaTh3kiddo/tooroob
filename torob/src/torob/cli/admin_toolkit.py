"""Operations & Evaluation Toolkit CLI.

Provides command-line utilities for:
1. Snapshot ingestion and comparison.
2. Listing active quality alerts.
3. Inspecting shop reliability dimensions and Bayesian confidence intervals.
4. Explaining inquiry policy decisions.
5. Replaying offline verification policies.
6. Evaluating calibration metrics on test fixtures.
"""
import argparse
from datetime import datetime, timezone
import json
import sys
from typing import Optional

from torob.intelligence.calibration import CalibrationEvaluator
from torob.intelligence.policy_simulator import VerificationPolicySimulator
from torob.storage.db import db_manager
from torob.storage.repository_ledger import LedgerRepository


def print_header(title: str):
    print("=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)


def cmd_list_alerts(args):
    print_header("Active Quality Alerts")
    repo = LedgerRepository()
    alerts = repo.get_quality_alerts(unresolved_only=not args.all, limit=args.limit)
    if not alerts:
        print("No active alerts found.")
        return

    for a in alerts:
        status = "RESOLVED" if a.get("is_resolved") else "ACTIVE"
        print(f"[{a['severity'].upper()}] {a['alert_type']} | Entity: {a['entity_type']}:{a['entity_id']} | Status: {status}")
        print(f"  Created: {a['created_at']}")
        print(f"  Payload: {json.dumps(a['payload'], ensure_ascii=False)}")
        print("-" * 60)


def cmd_explain_decisions(args):
    print_header("Inquiry Policy Decisions Audit Trail")
    repo = LedgerRepository()
    decisions = repo.get_policy_decisions(limit=args.limit)
    if not decisions:
        print("No policy decisions recorded yet.")
        return

    for d in decisions:
        print(f"Decision ID: {d['decision_id']} | Action: {d['action_code']} | Trigger: {d['selection_trigger']}")
        print(f"  Created: {d['created_at']} | VoI Benefit: {d.get('expected_benefit')} | Cost: {d.get('expected_cost')}")
        print(f"  Reasons: {', '.join(d.get('reason_codes', []))}")
        print(f"  Scope: {json.dumps(d.get('scope', {}), ensure_ascii=False)}")
        print("-" * 60)


def cmd_simulate_policies(args):
    print_header("Verification Policy Offline Replay Simulation")
    sim = VerificationPolicySimulator(simulation_horizon_hours=args.hours)
    results = sim.evaluate_policies()

    print(f"{'Policy Name':<26} | {'Inquiries':<9} | {'Burden':<8} | {'Useful':<6} | {'Missed':<6} | {'Delay(h)':<8} | {'Eff(%)':<6}")
    print("-" * 80)
    for name, m in results.items():
        print(
            f"{m.policy_name:<26} | {m.total_inquiries:<9} | {m.seller_burden_score:<8.1f} | "
            f"{m.useful_confirmations_count:<6} | {m.simulated_missed_mismatches:<6} | "
            f"{m.mean_detection_delay_hours:<8.1f} | {m.efficiency_useful_per_100_inquiries:<6.1f}"
        )
    print("=" * 80)
    print("Note: Results generated from deterministic synthetic simulation; do not represent live traffic.")


def cmd_evaluate_calibration(args):
    print_header("Binary Calibration Evaluation Benchmark")
    # Synthetic fixture for well-calibrated vs miscalibrated
    preds = [0.1, 0.12, 0.15, 0.35, 0.4, 0.42, 0.78, 0.81, 0.89, 0.95] * 20
    labels = [0, 0, 0, 0, 1, 0, 1, 1, 1, 1] * 20

    res = CalibrationEvaluator.evaluate_binary_calibration(preds, labels, num_bins=5)
    print(f"Total Samples: {res.total_samples}")
    print(f"Brier Score: {res.brier_score:.5f}")
    print(f"Log Loss: {res.log_loss:.5f}")
    print(f"Expected Calibration Error (ECE): {res.expected_calibration_error:.5f}")
    print("\nReliability Diagram Bins:")
    print(f"{'Bin':<12} | {'Pred Mean':<10} | {'Obs Freq':<10} | {'Samples':<8} | {'Abs Error':<10}")
    print("-" * 60)
    for b in res.reliability_bins:
        rng = f"[{b.bin_range[0]:.1f}, {b.bin_range[1]:.1f})"
        print(f"{rng:<12} | {b.predicted_mean:<10.4f} | {b.observed_frequency:<10.4f} | {b.sample_count:<8} | {b.absolute_calibration_error:<10.4f}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Torob Operations & Evaluation Toolkit")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    p_alerts = subparsers.add_parser("alerts", help="List quality alerts")
    p_alerts.add_argument("--all", action="store_true", help="Include resolved alerts")
    p_alerts.add_argument("--limit", type=int, default=20, help="Max alerts to show")
    p_alerts.set_defaults(func=cmd_list_alerts)

    p_decisions = subparsers.add_parser("decisions", help="Inspect policy decisions audit trail")
    p_decisions.add_argument("--limit", type=int, default=20, help="Max decisions to show")
    p_decisions.set_defaults(func=cmd_explain_decisions)

    p_sim = subparsers.add_parser("simulate", help="Run offline verification policy simulation")
    p_sim.add_argument("--hours", type=float, default=336.0, help="Simulation horizon in hours")
    p_sim.set_defaults(func=cmd_simulate_policies)

    p_calib = subparsers.add_parser("calibration", help="Evaluate calibration metrics on test fixture")
    p_calib.set_defaults(func=cmd_evaluate_calibration)

    args = parser.parse_args()
    if not args.subcommand:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
