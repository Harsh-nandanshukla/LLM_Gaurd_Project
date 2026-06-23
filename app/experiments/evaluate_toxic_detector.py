"""
E4B Evaluation — Toxic-BERT Content Guardrails

Evaluates ToxicClassifierService.analyze_text() against:
    - toxic_prompts.csv  (real, civil_comments derived, label=1)
    - clean_prompts.csv  (real, civil_comments derived, label=0)

NOTE: before running, make sure toxic_prompts.csv does not contain any
slur-based rows — those should be removed manually after sourcing from
civil_comments, regardless of their toxicity score.

Usage:
    python app/experiments/evaluate_toxic_detector.py
"""

import csv
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.services.toxic_classifier_service import toxic_classifier_service


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "results")

TOXIC_CSV = os.path.join(DATA_DIR, "toxic_prompts.csv")
CLEAN_CSV = os.path.join(DATA_DIR, "clean_prompts.csv")


def load_dataset():
    samples = []

    with open(TOXIC_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples.append({
                "text": row["text"],
                "true_label": 1,
                "source_file": "toxic_prompts.csv",
            })

    with open(CLEAN_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples.append({
                "text": row["text"],
                "true_label": 0,
                "source_file": "clean_prompts.csv",
            })

    return samples


def run_evaluation():
    samples = load_dataset()

    results = []
    tp = fp = tn = fn = 0
    total_latency_ms = 0.0

    for sample in samples:
        text = sample["text"]
        true_label = sample["true_label"]

        start = time.perf_counter()
        verdict = toxic_classifier_service.analyze_text(text, source="input")
        latency_ms = (time.perf_counter() - start) * 1000
        total_latency_ms += latency_ms

        predicted_label = 1 if verdict["is_toxic"] else 0

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
            "max_label": verdict["max_label"],
            "max_score": verdict["max_score"],
            "category": verdict["category"],
            "source_file": sample["source_file"],
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
    avg_latency_ms = total_latency_ms / total if total > 0 else 0.0

    print("=" * 40)
    print("E4B EVALUATION — TOXIC-BERT CONTENT GUARDRAILS")
    print("=" * 40)
    print(f"Total Samples       : {total}")
    print(f"TP : {tp}  FP : {fp}  TN : {tn}  FN : {fn}")
    print(f"Precision           : {precision:.4f}")
    print(f"Recall              : {recall:.4f}")
    print(f"F1 Score            : {f1:.4f}")
    print(f"False Positive Rate : {fpr:.4f}")
    print(f"Avg latency/request : {avg_latency_ms:.2f} ms")
    print("=" * 40)

    os.makedirs(RESULTS_DIR, exist_ok=True)

    results_path = os.path.join(RESULTS_DIR, "results_toxic_detector.csv")
    with open(results_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "text", "true_label", "predicted_label", "outcome",
                "max_label", "max_score", "category", "source_file",
                "latency_ms",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    metrics_path = os.path.join(RESULTS_DIR, "metrics_toxic_detector.csv")
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
        writer.writerow(["avg_latency_ms", round(avg_latency_ms, 2)])

    print(f"Saved: {results_path}")
    print(f"Saved: {metrics_path}")


if __name__ == "__main__":
    run_evaluation()