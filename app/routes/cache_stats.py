from fastapi import APIRouter

from app.services.cache_service import cache_service


router = APIRouter(
    prefix="/cache-stats",
    tags=["Cache"]
)




@router.get("")
def get_cache_stats():

    hits = cache_service.cache_hits
    misses = cache_service.cache_misses
    errors = cache_service.cache_errors

    total_requests = hits + misses

    hit_rate = (
        hits / total_requests
        if total_requests > 0
        else 0
    )

    miss_rate = (
        misses / total_requests
        if total_requests > 0
        else 0
    )

    return {
        "hits": hits,
        "misses": misses,
        "errors": errors,
        "total_requests": total_requests,
        "hit_rate": round(hit_rate, 4),
        "miss_rate": round(miss_rate, 4)
    }