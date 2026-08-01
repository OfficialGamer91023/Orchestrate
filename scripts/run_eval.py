#!/usr/bin/env python3
"""Headless CLI evaluation script.

Triggers the batch evaluation pipeline via the FastAPI API
and prints results to stdout.

Usage:
    python scripts/run_eval.py [--api-url http://localhost:8000] [--token dev-token]
"""

import argparse
import json
import sys
import time

import httpx


def main():
    parser = argparse.ArgumentParser(description="Run batch evaluation")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend API base URL",
    )
    parser.add_argument(
        "--token",
        default="dev-token",
        help="Bearer token for API auth",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recalculation even if results exist",
    )
    args = parser.parse_args()

    url = f"{args.api_url}/api/v1/batch-eval"
    headers = {"Authorization": f"Bearer {args.token}"}
    params = {"force_recalculate": str(args.force).lower()}

    print(f"🚀 Starting batch evaluation at {url}")
    print(f"   Force recalculate: {args.force}")
    start = time.time()

    try:
        with httpx.Client(timeout=600.0) as client:
            response = client.post(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError as e:
        print(f"❌ API request failed: {e}", file=sys.stderr)
        sys.exit(1)

    elapsed = time.time() - start

    print(f"\n✅ Evaluation complete in {elapsed:.1f}s")
    print(f"   Total processed: {result.get('total_processed', 0)}")
    print(f"   Accuracy: {result.get('accuracy', 0):.2%}")
    print(f"   Macro F1: {result.get('macro_f1', 0):.4f}")
    print(f"   Notify FPR: {result.get('notify_fpr', 0):.4f}")

    class_metrics = result.get("class_metrics", {})
    if class_metrics:
        print(f"\n{'Class':<10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
        print("-" * 50)
        for cls, metrics in class_metrics.items():
            print(
                f"{cls:<10} {metrics['precision']:>10.4f} {metrics['recall']:>10.4f} "
                f"{metrics['f1']:>10.4f} {metrics['support']:>10d}"
            )

    print(f"\n📄 Results written to output.csv")


if __name__ == "__main__":
    main()
