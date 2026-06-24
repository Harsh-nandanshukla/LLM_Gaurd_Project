from pydantic import BaseModel
from typing import List, Optional,Dict


class AnalyzeRequest(BaseModel):
    text: str


class EntityDetail(BaseModel):
    entity_type: str
    start: int
    end: int
    score: float
    detected_text: str



class AnalyzeResponse(BaseModel):

    status: str

    guardrail: Optional[str] = None
    reason: Optional[str] = None

    original_text: Optional[str] = None
    redacted_input: Optional[str] = None

    llm_response: Optional[str] = None
    redacted_output: Optional[str] = None

    input_pii_detected: Optional[bool] = None
    output_pii_detected: Optional[bool] = None

    entities_redacted: Optional[List[str]] = None
    cache_hit: Optional[bool] = None
    latency_ms: Optional[float] = None
    detail: Optional[dict] = None
    timings: Optional[Dict[str, float]] = None