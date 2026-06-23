"""
Run locally:

    pip install datasets
    python build_toxic_dataset.py

Downloads a balanced toxicity evaluation dataset from
civil_comments and saves:

    data/toxic_prompts.csv
    data/clean_prompts.csv
"""

import csv
import os
import random

from datasets import load_dataset

random.seed(42)

SAMPLE_SIZE_TOXIC = 35
SAMPLE_SIZE_CLEAN = 35

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)

TOXIC_CSV = os.path.join(DATA_DIR, "toxic_prompts.csv")
CLEAN_CSV = os.path.join(DATA_DIR, "clean_prompts.csv")

print("Downloading civil_comments dataset (train split)...")

ds = load_dataset(
    "google/civil_comments",
    split="train"
)

print(f"Total rows available: {len(ds)}")

toxic_rows = []
clean_rows = []

for row in ds:

    text = row["text"].strip()

    # Keep evaluation samples reasonably sized
    if len(text) < 15 or len(text) > 300:
        continue

    if row["toxicity"] >= 0.7:

        toxic_rows.append({
            "text": text,
            "toxicity": round(row["toxicity"], 3),
            "severe_toxicity": round(row["severe_toxicity"], 3),
            "obscene": round(row["obscene"], 3),
            "threat": round(row["threat"], 3),
            "insult": round(row["insult"], 3),
            "identity_attack": round(row["identity_attack"], 3),
        })

    elif row["toxicity"] <= 0.05:

        clean_rows.append({
            "text": text
        })

    if (
        len(toxic_rows) >= SAMPLE_SIZE_TOXIC * 5
        and
        len(clean_rows) >= SAMPLE_SIZE_CLEAN * 5
    ):
        break

print(f"Candidate toxic rows found: {len(toxic_rows)}")
print(f"Candidate clean rows found: {len(clean_rows)}")

sampled_toxic = random.sample(
    toxic_rows,
    min(SAMPLE_SIZE_TOXIC, len(toxic_rows))
)

sampled_clean = random.sample(
    clean_rows,
    min(SAMPLE_SIZE_CLEAN, len(clean_rows))
)

with open(
    TOXIC_CSV,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "text",
            "label",
            "toxicity",
            "severe_toxicity",
            "obscene",
            "threat",
            "insult",
            "identity_attack",
        ],
    )

    writer.writeheader()

    for row in sampled_toxic:

        row["label"] = 1

        writer.writerow(row)

with open(
    CLEAN_CSV,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "text",
            "label",
        ],
    )

    writer.writeheader()

    for row in sampled_clean:

        row["label"] = 0

        writer.writerow(row)

print()
print("=" * 50)
print("DATASET BUILD COMPLETE")
print("=" * 50)
print(f"Toxic samples : {len(sampled_toxic)}")
print(f"Clean samples : {len(sampled_clean)}")
print()
print(f"Saved: {TOXIC_CSV}")
print(f"Saved: {CLEAN_CSV}")
print("=" * 50)