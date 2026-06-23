from fastapi import FastAPI

from app.routes.analyze import router as analyze_router
from app.routes.cache_stats import router as cache_router


from slowapi.middleware import SlowAPIMiddleware
from app.rate_limiter import limiter


app = FastAPI(
    title="LLM Guardrails API"
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.on_event("startup")
async def warm_up_models():

    from app.services.toxic_classifier_service import (
        toxic_classifier_service
    )

    from app.services.presidio_service import (
        presidio_service
    )

    from app.services.attack_detection_service import (
        attack_detection_service
    )

    try:

        toxic_classifier_service.analyze_text(
            "warm up",
            source="input"
        )

        presidio_service.redact_text(
            "warm up"
        )

        attack_detection_service.detect_attack(
            "warm up"
        )

        print("✓ Models warmed up successfully")

    except Exception as e:
        print(f"Warmup failed: {e}")


app.include_router(cache_router)
app.include_router(analyze_router)



@app.get("/health")
def health():
    return {
        "status": "healthy"
    }