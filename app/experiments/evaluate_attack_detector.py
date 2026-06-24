"""
E4A Evaluation — LLM Security Guardrails (Prompt Injection / System Prompt Leakage)

Evaluates the combined detect_attack() pipeline (heuristic + LLM-judge
fallback) as a single system against attack_prompts.csv and
benign_prompts.csv.

This is NOT a heuristic-vs-judge comparison. It evaluates detect_attack()
as one unit, the same way evaluate_presidio.py / evaluate_regex.py
evaluated each detector as one unit in E1.

Usage:
    python app/experiments/evaluate_attack_detector.py
"""

import csv
import os
import sys
import time

# Allow running this file directly via `python app/experiments/evaluate_attack_detector.py`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.services.attack_detection_service import AttackDetectionService


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "results")

ATTACK_CSV = os.path.join(DATA_DIR, "attack_prompts.csv")
BENIGN_CSV = os.path.join(DATA_DIR, "benign_prompts.csv")


def load_dataset():
    """
    Loads attack_prompts.csv (label=1) and benign_prompts.csv (label=0)
    into a single list of (text, true_label) tuples.
    """
    samples = []

    with open(ATTACK_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples.append({"text": row["text"], "true_label": 1})

    with open(BENIGN_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples.append({"text": row["text"], "true_label": 0})

    return samples


def run_evaluation():
    detector = AttackDetectionService()
    samples = load_dataset()

    results = []
    tp = fp = tn = fn = 0
    heuristic_count = 0
    judge_count = 0
    total_latency_ms = 0.0

    for sample in samples:
        text = sample["text"]
        true_label = sample["true_label"]

        start = time.perf_counter()
        verdict = detector.detect_attack(text)
        latency_ms = (time.perf_counter() - start) * 1000
        total_latency_ms += latency_ms

        predicted_label = 1 if verdict["is_attack"] else 0

        if verdict["detection_stage"] == "heuristic":
            heuristic_count += 1
        else:
            judge_count += 1

        if predicted_label == 1 and true_label == 1:
            tp += 1
            outcome = "TP"
        elif predicted_label == 1 and true_label == 0:
            fp += 1
            outcome = "FP"
        elif predicted_label == 0 and true_label == 0:
            tn += 1
            outcome = "TN"
        else:
            fn += 1
            outcome = "FN"

        results.append({
            "text": text,
            "true_label": true_label,
            "predicted_label": predicted_label,
            "outcome": outcome,
            "category": verdict["category"],
            "confidence": round(verdict["confidence"], 4),
            "detection_stage": verdict["detection_stage"],
            "latency_ms": round(latency_ms, 2),
        })

    total = len(samples)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    detection_rate = recall  # detection rate == recall on the attack class

    avg_latency_ms = total_latency_ms / total if total > 0 else 0.0
    judge_fallback_rate = judge_count / total if total > 0 else 0.0

    print("=" * 40)
    print("E4A EVALUATION — ATTACK DETECTION")
    print("=" * 40)
    print(f"Total Samples      : {total}")
    print(f"TP : {tp}  FP : {fp}  TN : {tn}  FN : {fn}")
    print(f"Precision          : {precision:.4f}")
    print(f"Recall (Detection) : {recall:.4f}")
    print(f"F1 Score           : {f1:.4f}")
    print(f"False Positive Rate: {fpr:.4f}")
    print("-" * 40)
    print(f"Caught by heuristic only : {heuristic_count} ({heuristic_count/total:.1%})")
    print(f"Required LLM judge call  : {judge_count} ({judge_fallback_rate:.1%})")
    print(f"Avg latency / request    : {avg_latency_ms:.2f} ms")
    print("=" * 40)

    os.makedirs(RESULTS_DIR, exist_ok=True)

    results_path = os.path.join(RESULTS_DIR, "results_attack_detector.csv")
    with open(results_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "text", "true_label", "predicted_label", "outcome",
                "category", "confidence", "detection_stage", "latency_ms",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    metrics_path = os.path.join(RESULTS_DIR, "metrics_attack_detector.csv")
    with open(metrics_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["total_samples", total])
        writer.writerow(["tp", tp])
        writer.writerow(["fp", fp])
        writer.writerow(["tn", tn])
        writer.writerow(["fn", fn])
        writer.writerow(["precision", round(precision, 4)])
        writer.writerow(["recall", round(recall, 4)])
        writer.writerow(["f1_score", round(f1, 4)])
        writer.writerow(["false_positive_rate", round(fpr, 4)])
        writer.writerow(["heuristic_only_count", heuristic_count])
        writer.writerow(["llm_judge_count", judge_count])
        writer.writerow(["judge_fallback_rate", round(judge_fallback_rate, 4)])
        writer.writerow(["avg_latency_ms", round(avg_latency_ms, 2)])

    print(f"Saved: {results_path}")
    print(f"Saved: {metrics_path}")


if __name__ == "__main__":
    run_evaluation()