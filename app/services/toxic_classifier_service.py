import logging

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

logger = logging.getLogger("guardrails")


class ToxicClassifierService:
    """
    E4B — Toxic-BERT Content Guardrails.

    Multi-label toxicity classifier (unitary/toxic-bert) used on BOTH
    sides of the gateway:
        - Input side: catch toxic/abusive user messages before they
          reach the LLM (saves a wasted LLM call, protects against
          abuse logging).
        - Output side: catch cases where the LLM itself produces toxic
          content despite input-side checks passing (e.g. provoked by
          a borderline-but-not-blocked prompt, or model drift).

    unitary/toxic-bert outputs 6 independent labels (multi-label, not
    mutually exclusive — a single text can score high on more than one):
        toxic, severe_toxic, obscene, threat, insult, identity_hate

    These six map onto the locked threat model's four categories as:
        Toxicity      -> toxic, severe_toxic, obscene
        Hate Speech   -> identity_hate
        Threats       -> threat
        Abuse         -> insult

    A single overall "is_toxic" verdict is derived by thresholding the
    MAX label score, since any one label firing strongly is sufficient
    to flag the text — toxicity categories are not meant to average out.
    """

    LABELS = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]

    CATEGORY_MAP = {
        "toxic": "Toxicity",
        "severe_toxic": "Toxicity",
        "obscene": "Toxicity",
        "threat": "Threats",
        "insult": "Abuse",
        "identity_hate": "Hate Speech",
    }

    def __init__(self, threshold: float = 0.5, model_name: str = "unitary/toxic-bert"):
        self.threshold = threshold
        self.model_name = model_name

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.eval()
        except Exception as e:
            logger.error(f"Failed to load toxic-bert model: {e}")
            raise

    def _predict_scores(self, text: str) -> dict:
        """
        Runs the model and returns raw per-label sigmoid scores.
        Multi-label classification uses sigmoid, not softmax, since
        labels are independent (e.g. text can be both 'threat' and
        'identity_hate' simultaneously).
        """
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )

        with torch.no_grad():
            outputs = self.model(**inputs)
            scores = torch.sigmoid(outputs.logits)[0].tolist()

        return dict(zip(self.LABELS, scores))

    def analyze_text(self, text: str, source: str = "input") -> dict:
        """
        Args:
            text: the text to classify.
            source: "input" (user message) or "output" (LLM response) —
                purely for logging/auditing context, does not change
                the classification logic itself.

        Returns:
            {
                "is_toxic": bool,
                "max_label": str,
                "max_score": float,
                "category": str,            # mapped via CATEGORY_MAP
                "label_scores": {...},      # all 6 raw scores
                "source": "input" | "output",
            }
        """
        if not text or not text.strip():
            return {
                "is_toxic": False,
                "max_label": None,
                "max_score": 0.0,
                "category": None,
                "label_scores": {label: 0.0 for label in self.LABELS},
                "source": source,
            }

        try:
            label_scores = self._predict_scores(text)
        except Exception as e:
            logger.error(f"toxic_classifier analyze_text failed: {e}")
            # Fail open on classifier error — same rationale as the
            # LLM judge's fail-safe behavior in attack_detection_service:
            # a content classifier that blocks everything on its own
            # internal error creates an availability problem, and the
            # error is logged rather than silently swallowed.
            return {
                "is_toxic": False,
                "max_label": None,
                "max_score": 0.0,
                "category": "classifier_error",
                "label_scores": {label: 0.0 for label in self.LABELS},
                "source": source,
            }

        max_label = max(label_scores, key=label_scores.get)
        max_score = label_scores[max_label]
        is_toxic = max_score >= self.threshold

        return {
            "is_toxic": is_toxic,
            "max_label": max_label,
            "max_score": round(max_score, 4),
            "category": self.CATEGORY_MAP.get(max_label) if is_toxic else None,
            "label_scores": {k: round(v, 4) for k, v in label_scores.items()},
            "source": source,
        }


toxic_classifier_service = ToxicClassifierService()