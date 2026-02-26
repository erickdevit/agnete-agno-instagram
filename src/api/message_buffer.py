import time
import logging
import redis
from src.config import REDIS_URL

logger = logging.getLogger(__name__)

class MessageBuffer:
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.ttl = 300  # 5 minutes expiration for keys

    def add_message(self, sender_id: str, message: str):
        """Append a message to the user's buffer."""
        key = f"chat:buffer:{sender_id}"
        self.redis.rpush(key, message)
        self.redis.expire(key, self.ttl)

    def get_and_clear_messages(self, sender_id: str) -> list[str]:
        """Retrieve all messages and clear the buffer atomically."""
        key = f"chat:buffer:{sender_id}"
        pipeline = self.redis.pipeline()
        pipeline.lrange(key, 0, -1)
        pipeline.delete(key)
        results = pipeline.execute()
        return results[0] if results and results[0] else []

    def touch_timer(self, sender_id: str):
        """Update the timestamp of the last received message."""
        key = f"chat:last_seen:{sender_id}"
        self.redis.set(key, time.time(), ex=self.ttl)

    def get_last_message_time(self, sender_id: str) -> float:
        """Get the timestamp of the last received message."""
        key = f"chat:last_seen:{sender_id}"
        ts = self.redis.get(key)
        return float(ts) if ts else 0.0

    def acquire_processing_lock(self, sender_id: str) -> bool:
        """
        Try to acquire a lock to process the buffer.
        Returns True if acquired, False if already locked.
        """
        key = f"chat:processing:{sender_id}"
        # Set lock with a safety TTL (e.g. 60s) so it doesn't get stuck forever
        return bool(self.redis.set(key, "locked", nx=True, ex=60))

    def release_processing_lock(self, sender_id: str):
        """Release the processing lock."""
        key = f"chat:processing:{sender_id}"
        self.redis.delete(key)
