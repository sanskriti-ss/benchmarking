#!/usr/bin/env python3
"""
Standalone benchmark test script.
Runs all 4 Dedalus models against questions_test.csv, scores them, and saves results.

Usage:
    export DEDALUS_API_KEY="your-key"
    export ANTHROPIC_API_KEY="your-key"   # needed for scoring
    python benchmark_test.py
"""

import os
import csv
import json
import time
import sys

# Reuse functions from the main app
from app import call_dedalus, score_agreeability, DEDALUS_MODELS

MODELS = {
    "dedalus-gpt4o": "openai/gpt-4o",
    "dedalus-claude-sonnet": "anthropic/claude-sonnet-4-20250514",
    "dedalus-gemini-flash": "google/gemini-2.5-flash",
    "dedalus-grok3": "xai/grok-3",
}

MODEL_LABELS = {
    "dedalus-gpt4o": "GPT-4o",
    "dedalus-claude-sonnet": "Claude Sonnet 4",
    "dedalus-gemini-flash": "Gemini 2.5 Flash",
    "dedalus-grok3": "Grok 3",
}


def load_questions(path="questions_test.csv"):
    questions = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append(row["question"])
    return questions


def main():
    dedalus_key = os.getenv("DEDALUS_API_KEY", "").strip()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    if not dedalus_key:
        print("Error: DEDALUS_API_KEY not set")
        sys.exit(1)
    if not anthropic_key:
        print("Error: ANTHROPIC_API_KEY not set (needed for scoring)")
        sys.exit(1)

    questions = load_questions()
    print(f"Loaded {len(questions)} questions from questions_test.csv\n")

    model_keys = list(MODELS.keys())
    results = []

    for i, question in enumerate(questions):
        print(f"--- Question {i + 1}/{len(questions)} ---")
        print(f"  {question[:80]}...")
        row = {"question": question}

        for model_key in model_keys:
            model_id = MODELS[model_key]
            label = MODEL_LABELS[model_key]
            print(f"  Calling {label} ({model_id})...", end=" ", flush=True)
            response = call_dedalus(question, dedalus_key, model_id)
            if response.startswith("Error:"):
                print(f"FAILED: {response}")
            else:
                print(f"OK ({len(response)} chars)")
            row[model_key] = response
            # Small delay between calls to avoid rate limits
            time.sleep(2)

        results.append(row)
        print()

    # Score all results
    print("Scoring agreeability with Claude...")
    scores = score_agreeability(results, anthropic_key, model_keys)

    # Build output
    output = {
        "questions": questions,
        "models": MODELS,
        "results": results,
        "scores": scores,
    }

    out_path = "benchmark_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {out_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("BENCHMARK SCORES")
    print("=" * 70)
    print(f"  {'Model':25s} {'Syco':>7s} {'Factual':>8s} {'Placat':>8s} {'Epist':>8s}")
    print("-" * 70)
    for model_key in model_keys:
        label = MODEL_LABELS[model_key]
        if model_key in scores:
            d = scores[model_key]
            if isinstance(d, dict):
                syc = d.get("sycophancy", d.get("score", 0))
                fa = d.get("factual_accuracy", 0)
                pl = d.get("placating", 0)
                ep = d.get("epistemic_transparency", 0)
                print(f"  {label:25s} {float(syc):+7.2f} {float(fa):8.2f} {float(pl):8.2f} {float(ep):8.2f}")
                if d.get("explanation"):
                    print(f"    {d['explanation']}")
            else:
                print(f"  {label:25s} {float(d):+7.2f}")
        else:
            print(f"  {label:25s}  (no score)")
    print("=" * 70)


if __name__ == "__main__":
    main()
