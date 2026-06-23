from presidio_analyzer import AnalyzerEngine
import logging

logger = logging.getLogger("guardrails")


class PresidioService:
    def __init__(self, threshold: float = 0.3):
        self.analyzer = AnalyzerEngine()
        self.threshold = threshold

        # Only detect entity types relevant to our threat model
        self.entities_to_detect = [
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "PERSON",
        ]

    def analyze_text(self, text: str) -> dict:
        """
        Analyze text for PII entities using Microsoft Presidio.
        """

        try:
            results = self.analyzer.analyze(
                text=text,
                language="en",
                entities=self.entities_to_detect,
            )

            entities = []

            for result in results:

                # Ignore low-confidence detections
                if result.score < self.threshold:
                    continue

                entities.append(
                    {
                        "entity_type": result.entity_type,
                        "start": result.start,
                        "end": result.end,
                        "score": round(result.score, 4),
                        "detected_text": text[result.start:result.end],
                    }
                )

            return {
                "contains_pii": len(entities) > 0,
                "entity_count": len(entities),
                "entities": entities,
            }

        except Exception as e:
            logger.error(f"presidio analyze_text failed: {e}")

            return {
                "contains_pii": False,
                "entity_count": 0,
                "entities": [],
                "error": str(e),
            }

    def redact_text(self, text: str) -> dict:
        """
        Detect PII and replace each entity with a standardized
        placeholder such as:

            [EMAIL_ADDRESS]
            [PHONE_NUMBER]
            [PERSON]
            [CREDIT_CARD]

        Used by the gateway before sending text to the LLM and
        again before returning the final response.
        """

        analysis = self.analyze_text(text)

        if not analysis["contains_pii"]:
            return {
                "redacted_text": text,
                "contains_pii": False,
                "entity_count": 0,
                "entities": [],
            }

        # Replace from end to beginning so offsets remain valid
        entities_sorted = sorted(
            analysis["entities"],
            key=lambda e: e["start"],
            reverse=True,
        )

        redacted_text = text

        for entity in entities_sorted:

            placeholder = f"[{entity['entity_type']}]"

            redacted_text = (
                redacted_text[:entity["start"]]
                + placeholder
                + redacted_text[entity["end"]:]
            )

        return {
            "redacted_text": redacted_text,
            "contains_pii": True,
            "entity_count": analysis["entity_count"],
            "entities": analysis["entities"],
        }


presidio_service = PresidioService()

# if __name__ == "__main__":
#     result = presidio_service.redact_text(
#         "My email is harsh@gmail.com and my phone number is 9876543210"
#     )

#     print(result)