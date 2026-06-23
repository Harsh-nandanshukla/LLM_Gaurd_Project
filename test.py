from datasets import load_dataset

print("starting")

ds = load_dataset(
    "google/civil_comments",
    split="train[:10]"
)

print("loaded")

print(ds[0])

print("done")