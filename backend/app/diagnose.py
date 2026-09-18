"""
Phase 4: Diagnostic Engine — main entry point.

Three modes:

1. Diagnose an entire Phase 3 experiment sweep (default — reads the most
   recent file in experiment_results/):
    python diagnose.py

2. Diagnose one specific saved sweep:
    python diagnose.py --file experiment_results/experiment_20260918_120414.json

3. Diagnose a single ad-hoc set of metrics (no file needed) — useful for
   checking one number you're staring at without re-running anything:
    python diagnose.py --recall 0.45 --precision 0.55 --mrr 0.7 --ndcg 0.4

4. Close the loop: take the worst-recall config's top suggestion, actually
   build and run the follow-up experiment, and print a before/after
   comparison — this is the "diagnose -> suggest -> auto-run -> re-diagnose"
   loop from the original project plan.
    python diagnose.py --auto_follow_up
"""
import argparse
import json
from pathlib import Path

from diagnostics import (
    diagnose_config,
    diagnose_experiment_results,
    apply_suggestion,
    latest_results_file,
)

RESULTS_DIR = Path(__file__).parent / "experiment_results"


def run_auto_follow_up(results: list, metric_x: str, metric_y: str, judge: str = "offline"):
    """
    Closed-loop demo: find the worst config on metric_x, take its first
    actionable suggestion, run that follow-up config for real, and print
    a before/after comparison.

    IMPORTANT: `judge` controls which generation evaluators the follow-up
    run uses (offline lexical-overlap/embedding-similarity, or an LLM
    judge). It defaults to "offline" and does NOT infer from the config's
    generator — using a different judge for "before" and "after" would
    compare two different metrics on two different scales and make any
    delta meaningless (e.g. an offline embedding-similarity relevance
    score of 0.47 is not comparable to an LLM-judge relevance score of
    0.99 — they're not the same measurement). Pass --judge llm explicitly
    only if the ORIGINAL sweep also used the LLM judge.
    """
    from pipeline import PipelineConfig
    from experiment import run_single_config, load_data

    worst = min(results, key=lambda r: r.get(metric_x, 0))
    diagnosis = diagnose_config(worst)

    print(f"\n=== Auto follow-up ===")
    print(f"Worst config by {metric_x}: {worst['config']}")
    print(f"  {metric_x} = {worst.get(metric_x):.3f}" + (f", {metric_y} = {worst.get(metric_y):.3f}" if metric_y in worst else ""))
    diagnosis.print()

    actionable = [s for s in diagnosis.suggested_experiments if s.get("param")]
    if not actionable:
        print("\nNo actionable (auto-runnable) suggestion for this config — stopping here.")
        return

    suggestion = actionable[0]
    new_config = apply_suggestion(worst["config"], suggestion)
    if new_config is None:
        print("\nCould not build a follow-up config from this suggestion.")
        return

    print(f"\nRunning follow-up experiment: {suggestion['label']}")
    print(f"New config: {new_config.as_dict()}")
    print(f"Using judge: {judge} (matched to the original sweep for a fair before/after comparison)")

    documents, test_set = load_data()
    try:
        new_result = run_single_config(new_config, documents, test_set, judge=judge, skip_generation=(metric_y not in worst))
    except Exception as e:
        print(f"Follow-up run failed: {e}")
        return

    print(f"\n=== Before vs after ===")
    print(f"{'Metric':<15}{'Before':<12}{'After':<12}{'Change':<10}")
    for m in ["recall", "precision", "mrr", "ndcg", "faithfulness", "relevance"]:
        if m in worst and m in new_result:
            delta = new_result[m] - worst[m]
            print(f"{m:<15}{worst[m]:<12.3f}{new_result[m]:<12.3f}{delta:+.3f}")


def parse_args():
    p = argparse.ArgumentParser(description="Phase 4: diagnose why a RAG config is underperforming")
    p.add_argument("--file", type=str, default=None, help="Path to a Phase 3 experiment_results JSON file")
    p.add_argument("--metric_x", type=str, default="recall")
    p.add_argument("--metric_y", type=str, default="faithfulness")
    p.add_argument("--auto_follow_up", action="store_true",
                    help="Actually run the top suggested follow-up experiment and show before/after")
    p.add_argument("--judge", type=str, default="offline", choices=["offline", "llm"],
                    help="Judge to use for the --auto_follow_up run. Must match the judge used in the "
                         "original sweep, or the before/after comparison mixes two different metrics.")

    # Ad-hoc single-config diagnosis (no file needed)
    p.add_argument("--recall", type=float, default=None)
    p.add_argument("--precision", type=float, default=None)
    p.add_argument("--mrr", type=float, default=None)
    p.add_argument("--ndcg", type=float, default=None)
    p.add_argument("--faithfulness", type=float, default=None)
    p.add_argument("--relevance", type=float, default=None)

    return p.parse_args()


def main():
    args = parse_args()

    # Mode 3: ad-hoc single-config diagnosis from raw numbers
    ad_hoc_metrics = {
        k: v for k, v in {
            "recall": args.recall, "precision": args.precision, "mrr": args.mrr,
            "ndcg": args.ndcg, "faithfulness": args.faithfulness, "relevance": args.relevance,
        }.items() if v is not None
    }
    if ad_hoc_metrics:
        print(f"Diagnosing ad-hoc metrics: {ad_hoc_metrics}\n")
        diagnose_config(ad_hoc_metrics).print()
        return

    # Modes 1/2/4: load a saved experiment sweep
    file_path = Path(args.file) if args.file else latest_results_file(RESULTS_DIR)
    if file_path is None or not file_path.exists():
        print(f"No experiment results found. Run experiment.py first, or pass --file, "
              f"or pass individual metrics (--recall, --precision, ...) for an ad-hoc diagnosis.")
        return

    print(f"Loading: {file_path}")
    with open(file_path) as f:
        results = json.load(f)

    if args.auto_follow_up:
        run_auto_follow_up(results, args.metric_x, args.metric_y, judge=args.judge)
    else:
        diagnose_experiment_results(results, args.metric_x, args.metric_y)


if __name__ == "__main__":
    main()