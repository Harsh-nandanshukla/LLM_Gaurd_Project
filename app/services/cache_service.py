import redis
import hashlib
import json
from app.config import settings


class CacheService:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )

        # TTLs (seconds)
        self.guardrail_ttl = 86400  # 24 hour
        self.llm_ttl = 1800        # 30 minutes

        # Metrics for E3
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_errors = 0

    def ping(self):
        """Check Redis connection."""
        try:
            return self.client.ping()
        except Exception:
            return False

    def _make_key(self, prefix: str, text: str) -> str:
        """
        Generate a unique cache key.
        """
        hash_val = hashlib.sha256(text.encode()).hexdigest() #Generates unique Redis keys
        return f"{prefix}:{hash_val}"# guardrail:f81d4fae7dec...

    # ==========================
    # Guardrail Cache
    # ==========================

    def get_guardrail(self, text: str):
        try:
            key = self._make_key("guardrail", text)

            result = self.client.get(key)

            if result: #Is analysis already cached?
                self.cache_hits += 1
                return json.loads(result)

            self.cache_misses += 1
            return None

        except Exception as e:
            print("GET ERROR:", e)
            self.cache_errors += 1
            return None

    def set_guardrail(self, text: str, result: dict):
        try:
            key = self._make_key("guardrail", text)
            print("SET KEY:", key)
            self.client.setex(
                key,
                self.guardrail_ttl,
                json.dumps(result)
            )


        except Exception as e:
            print("SET ERROR:", e)
            # pass

    # ==========================
    # LLM Cache
    # ==========================

    def get_llm(self, text: str):
        try:
            key = self._make_key("llm", text)

            result = self.client.get(key)

            if result:
                self.cache_hits += 1
                return json.loads(result)

            self.cache_misses += 1
            return None

        except Exception:
            self.cache_misses += 1
            return None

    def set_llm(self, text: str, response):
        try:
            key = self._make_key("llm", text)

            self.client.setex(
                key,
                self.llm_ttl,
                json.dumps(response)
            )

        except Exception:
            pass

    # ==========================
    # Utility Functions
    # ==========================

    def delete(self, prefix: str, text: str):
        try:
            key = self._make_key(prefix, text)
            self.client.delete(key)
        except Exception:
            pass

    def get_hit_rate(self):
        total = self.cache_hits + self.cache_misses

        if total == 0:
            return 0

        return round(
            self.cache_hits / total,
            4
        )
cache_service = CacheService()    