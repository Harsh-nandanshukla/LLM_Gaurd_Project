import random
import pandas as pd

from locust import HttpUser, task, between


df = pd.read_csv("data/pii_dataset.csv")

texts = df["text"].tolist()


class AnalyzeUser(HttpUser):

    wait_time = between(1, 2)

    @task
    def analyze_text(self):

        payload = {
            "text": random.choice(texts)
        }

        self.client.post(
            "/analyze",
            json=payload,
            name="/analyze"
        )