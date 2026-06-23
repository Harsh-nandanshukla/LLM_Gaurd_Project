
import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from app.services.regex_service import RegexService


service = RegexService()

# Load dataset
df = pd.read_csv("data/pii_dataset.csv")

results = []

y_true = []
y_pred = []

for _, row in df.iterrows():

    text = row["text"]
    label = int(row["label"])

    result = service.analyze_text(text)

    prediction = int(result["contains_pii"])

    y_true.append(label)
    y_pred.append(prediction)

    entity_types = ",".join(
        entity["entity_type"]
        for entity in result["entities"]
    )

    results.append(
        {
            "text": text,
            "label": label,
            "prediction": prediction,
            "contains_pii": result["contains_pii"],
            "entity_count": result["entity_count"],
            "entities": entity_types,
        }
    )

# Save detailed results
results_df = pd.DataFrame(results)
results_df.to_csv(
    "results/results_regex.csv",
    index=False,
)

# Metrics
precision = precision_score(y_true, y_pred)
recall = recall_score(y_true, y_pred)
f1 = f1_score(y_true, y_pred)

tn, fp, fn, tp = confusion_matrix(
    y_true,
    y_pred
).ravel()

metrics_df = pd.DataFrame(
    [
        {
            "model": "regex",
            "total_samples": len(df),
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }
    ]
)

metrics_df.to_csv(
    "results/metrics_regex.csv",
    index=False,
)

print("\n==============================")
print("PRESIDIO EVALUATION")
print("==============================")
print(f"Total Samples : {len(df)}")
print(f"TP : {tp}")
print(f"FP : {fp}")
print(f"TN : {tn}")
print(f"FN : {fn}")
print()
print(f"Precision : {precision:.4f}")
print(f"Recall    : {recall:.4f}")
print(f"F1 Score  : {f1:.4f}")
print()
print("Saved:")
print("results/results_regex.csv")
print("results/metrics_regex.csv")
