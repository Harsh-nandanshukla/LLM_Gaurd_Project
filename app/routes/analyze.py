
import time
import logging

from fastapi import APIRouter
from fastapi import Request
from app.rate_limiter import limiter

from app.models.request_models import (
    AnalyzeRequest,
    AnalyzeResponse,
)

from app.services.cache_service import cache_service
from app.services.attack_detection_service import attack_detection_service
from app.services.toxic_classifier_service import toxic_classifier_service
from app.services.presidio_service import presidio_service
from app.services.llm_service import llm_service

router = APIRouter(
    prefix="/analyze",
    tags=["Guardrails"]
)

logger = logging.getLogger("guardrails")


@router.post("", response_model=AnalyzeResponse)
@limiter.limit("10/hour")
def analyze_text(request: Request, body: AnalyzeRequest):

    start_time = time.perf_counter()
    text = body.text

   
    # Cache Lookup
   
    cached_response = cache_service.get_guardrail(text)

    if cached_response:

        latency_ms = (
            time.perf_counter() - start_time
        ) * 1000
        cached_response["cache_hit"] = True
        cached_response["latency_ms"] = round(latency_ms, 2)
        logger.info(
            f"guardrail=cache status=hit latency_ms={latency_ms:.2f}"
        )

        return cached_response

    
    # [1] Attack Detection (E4A) — timing captured here, at the call
    
    attack_start = time.perf_counter()
    attack_result = attack_detection_service.detect_attack(text)
    attack_ms = (time.perf_counter() - attack_start) * 1000

    if attack_result["is_attack"]:

        blocked_response = {
            "status": "blocked",
            "guardrail": "attack_detection",
            "reason": "Prompt injection or system prompt leakage detected",
            "original_text": None,
            "redacted_input": None,
            "llm_response": None,
            "redacted_output": None,
            "input_pii_detected": None,
            "output_pii_detected": None,
            "entities_redacted": None,
            "detail": {
                "category": attack_result["category"],
                "confidence": attack_result["confidence"],
                "detection_stage": attack_result["detection_stage"],
            },
        }

        latency_ms = (time.perf_counter() - start_time) * 1000
        blocked_response["cache_hit"] = False
        blocked_response["latency_ms"] = round(latency_ms, 2)
        blocked_response["timings"] = {"attack_detection_ms": round(attack_ms, 2)}



        cache_service.set_guardrail(
            text=text,
            result=blocked_response,
        )

        return blocked_response

    
    # [2] Input Toxicity (E4B) — timing captured here, at the call
   
    input_toxicity_start = time.perf_counter()
    toxic_input = toxic_classifier_service.analyze_text(
        text,
        source="input"
    )
    input_toxicity_ms = (time.perf_counter() - input_toxicity_start) * 1000

    if toxic_input["is_toxic"]:

        blocked_response = {
            "status": "blocked",
            "guardrail": "toxicity",
            "reason": "Toxic content detected in input",
            "original_text": None,
            "redacted_input": None,
            "llm_response": None,
            "redacted_output": None,
            "input_pii_detected": None,
            "output_pii_detected": None,
            "entities_redacted": None,
            "detail": {
                "category": toxic_input["category"],
                "max_label": toxic_input["max_label"],
                "max_score": toxic_input["max_score"],
            },
        }

        latency_ms = (time.perf_counter() - start_time) *1000
        blocked_response["cache_hit"] = False
        blocked_response["latency_ms"] = round(latency_ms, 2)
        blocked_response["timings"] = {"attack_detection_ms": round(attack_ms, 2),"input_toxicity_ms": round(input_toxicity_ms, 2)}


        cache_service.set_guardrail(
            text=text,
            result=blocked_response,
        )

        return blocked_response

   
    # [3] Input PII Redaction — timing captured here, at the call
    
    input_pii_start = time.perf_counter()
    input_redaction = presidio_service.redact_text(text)
    input_pii_ms = (time.perf_counter() - input_pii_start) * 1000

    redacted_input = input_redaction["redacted_text"]

   
    # [4] LLM Call — timing captured here, at the call
   
    llm_start = time.perf_counter()
    llm_result = llm_service.generate_response(redacted_input)
    llm_ms = (time.perf_counter() - llm_start) * 1000

    if not llm_result["success"]:

        return {
            "status": "error",
            "guardrail": "llm_call",
            "reason": "LLM call failed",
            "original_text": None,
            "redacted_input": None,
            "llm_response": None,
            "redacted_output": None,
            "input_pii_detected": None,
            "output_pii_detected": None,
            "entities_redacted": None,
            "detail": {
                "error": llm_result["error"]
            },
        }

    llm_response_text = llm_result["response"]

   
    # [5] Output Toxicity — timing captured here, at the call
    
    output_toxicity_start = time.perf_counter()
    toxic_output = toxic_classifier_service.analyze_text(
        llm_response_text,
        source="output"
    )
    output_toxicity_ms = (time.perf_counter() - output_toxicity_start) * 1000

    if toxic_output["is_toxic"]:

        blocked_response = {
            "status": "blocked",
            "guardrail": "output_toxicity",
            "reason": "Generated response flagged as toxic, discarded",
            "original_text": None,
            "redacted_input": None,
            "llm_response": None,
            "redacted_output": None,
            "input_pii_detected": None,
            "output_pii_detected": None,
            "entities_redacted": None,
            "detail": {
                "category": toxic_output["category"],
                "max_label": toxic_output["max_label"],
                "max_score": toxic_output["max_score"],
            },
        }
        latency_ms = (time.perf_counter() - start_time) * 1000
        blocked_response["cache_hit"] = False
        blocked_response["latency_ms"] = round(latency_ms, 2)
        blocked_response["timings"] = {
        "attack_detection_ms": round(attack_ms, 2),
        "input_toxicity_ms": round(input_toxicity_ms, 2),
        "input_pii_ms": round(input_pii_ms, 2),
        "llm_ms": round(llm_ms, 2),
        "output_toxicity_ms": round(output_toxicity_ms, 2)}

        cache_service.set_guardrail(
            text=text,
            result=blocked_response,
        )

        return blocked_response

   
    # [6] Output PII Redaction — timing captured here, at the call
   
    output_pii_start = time.perf_counter()
    output_redaction = presidio_service.redact_text(
        llm_response_text
    )
    output_pii_ms = (time.perf_counter() - output_pii_start) * 1000

    redacted_output = output_redaction["redacted_text"]

    entities_redacted = list({
        entity["entity_type"]
        for entity in (
            input_redaction["entities"]
            + output_redaction["entities"]
        )
    })

    
    # Success Response
    
    latency_ms = (
        time.perf_counter() - start_time
    ) * 1000

    # All six timings now come from variables captured at the actual
    # call sites above — nothing here re-runs any service, this dict
    # just collects values that already exist by this point.
    timings = {
        "attack_detection_ms": round(attack_ms, 2),
        "input_toxicity_ms": round(input_toxicity_ms, 2),
        "input_pii_ms": round(input_pii_ms, 2),
        "llm_ms": round(llm_ms, 2),
        "output_toxicity_ms": round(output_toxicity_ms, 2),
        "output_pii_ms": round(output_pii_ms, 2),
    }

    response_payload = {
        "status": "success",
        "guardrail": None,
        "reason": None,
        "original_text": text,
        "redacted_input": redacted_input,
        "llm_response": llm_response_text,
        "redacted_output": redacted_output,
        "input_pii_detected": input_redaction["contains_pii"],
        "output_pii_detected": output_redaction["contains_pii"],
        "entities_redacted": entities_redacted,
        "detail": None,
        "cache_hit": False,
        "latency_ms": round(latency_ms, 2),
        "timings": timings,
    }

    cache_service.set_guardrail(
        text=text,
        result=response_payload,
    )

    logger.info(
        f"guardrail=none status=success latency_ms={latency_ms:.2f}"
    )

    return response_payload