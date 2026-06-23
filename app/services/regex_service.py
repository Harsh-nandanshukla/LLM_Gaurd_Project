
import re


class RegexService:
    def __init__(self):

        self.patterns = {
            "EMAIL_ADDRESS": re.compile(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
            ),

            # Indian phone numbers
            "PHONE_NUMBER": re.compile(
                r"(?:\+91[- ]?)?[6-9]\d{9}\b"
            ),

            # Generic credit card pattern
            "CREDIT_CARD": re.compile(
                r"\b(?:\d[ -]*?){13,16}\b"
            ),

            # Very naive PERSON detector
            # Only for experiment comparison
            "PERSON": re.compile(
                r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"
            ),
        }

    def analyze_text(self, text: str) -> dict:

        entities = []

        for entity_type, pattern in self.patterns.items():

            matches = pattern.finditer(text)

            for match in matches:

                entities.append(
                    {
                        "entity_type": entity_type,
                        "start": match.start(),
                        "end": match.end(),
                        "score": 1.0,
                        "detected_text": match.group(),
                    }
                )

        return {
            "contains_pii": len(entities) > 0,
            "entity_count": len(entities),
            "entities": entities,
        }


