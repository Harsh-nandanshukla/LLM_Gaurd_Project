import os
import logging
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("guardrails")


class LLMService:
    """
    Wraps the GPT-4o mini call that sits between the input and output
    guardrail stages in the gateway pipeline.

    No system prompt is set — the model runs with its default behavior.
    This project demonstrates the guardrail gateway's behavior, not a
    particular assistant persona, so there's nothing extra to explain
    or tune in a demo beyond the guardrail layer itself.
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found")

        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model

    def generate_response(self, text: str) -> dict:
        """
        Args:
            text: the (already redacted, already cleared) input text
                  to send to the LLM.

        Returns:
            {
                "response": str,
                "success": bool,
                "error": str | None,
            }

        Fails closed here, not open — unlike the guardrail components,
        an LLM call failure has no safe fallback content to return, so
        the caller (analyze.py) is expected to surface this as an
        error response rather than silently substituting empty text.
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
    {
        "role": "system",
        "content": (
            "You are a helpful AI assistant. "
            "Answer the user's questions directly, clearly, and concisely."
            "Keep  professional language."
            
        ),
    },
    {
        "role": "user",
        "content": text,
    },
],
                
                temperature=0.7,
                max_tokens=500,
            )
            response_text = completion.choices[0].message.content or ""

            return {
                "response": response_text,
                "success": True,
                "error": None,
            }
        except Exception as e:
            logger.error(f"llm_service generate_response failed: {e}")
            return {
                "response": None,
                "success": False,
                "error": str(e),
            }


llm_service = LLMService() 