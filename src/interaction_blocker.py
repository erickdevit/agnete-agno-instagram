"""
Interaction blocker: Prevents agent from responding when user is actively interacting.
Uses Redis to track user interactions with a rolling 5-minute window.
"""
import redis
import logging
import hashlib
from typing import Optional
from src.config import REDIS_URL

logger = logging.getLogger(__name__)

# Redis key prefix for user interaction locks
INTERACTION_LOCK_PREFIX = "user_interaction_lock:"
INTERACTION_LOCK_TTL = 300  # 5 minutes in seconds
AGENT_OUTBOUND_ECHO_PREFIX = "agent_outbound_echo:"
AGENT_OUTBOUND_ECHO_TTL = 120  # echo should arrive quickly after outbound send


class InteractionBlocker:
    """Manages agent blocking when user is actively interacting."""
    
    def __init__(self, redis_url: str = REDIS_URL):
        """
        Initialize Redis connection.
        
        Args:
            redis_url: Redis connection URL
        """
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("InteractionBlocker: Redis connection established")
        except Exception as e:
            logger.warning("InteractionBlocker: Failed to connect to Redis: %s", e)
            self.redis_client = None
    
    def mark_user_interaction(self, sender_id: str) -> None:
        """
        Mark that user has interacted, blocking agent response.
        Only creates lock on FIRST interaction. Does NOT extend if already locked.
        Maximum block time is 5 minutes from first interaction.
        
        Args:
            sender_id: Instagram user ID
        """
        if not self.redis_client:
            logger.debug("Redis not available, skipping interaction lock")
            return
        
        try:
            key = f"{INTERACTION_LOCK_PREFIX}{sender_id}"
            
            # Only set if key doesn't exist (first interaction)
            # This ensures 5 min is from FIRST message, not extended by subsequent ones
            exists = self.redis_client.exists(key) > 0
            
            if not exists:
                # Create new lock with 5 min TTL
                self.redis_client.setex(key, INTERACTION_LOCK_TTL, "locked")
                logger.info("[USER] First interaction from %s - Agent blocked for 5 min", sender_id[-6:])
            else:
                # User sent another message, but don't extend the timer
                remaining = self.redis_client.ttl(key)
                logger.info("[USER] Additional interaction from %s - Block continues (%.0f sec remaining)", 
                           sender_id[-6:], remaining)
        except Exception as e:
            logger.error("Error marking user interaction for %s: %s", sender_id, e)

    def _build_echo_key(self, user_id: str, text: str) -> str:
        digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:20]
        return f"{AGENT_OUTBOUND_ECHO_PREFIX}{user_id}:{digest}"

    def register_agent_outbound_message(self, user_id: str, text: str) -> None:
        """
        Register outbound agent message so its echo does not trigger user block.
        """
        if not self.redis_client or not user_id or not text:
            return

        try:
            key = self._build_echo_key(user_id, text)
            self.redis_client.setex(key, AGENT_OUTBOUND_ECHO_TTL, "1")
        except Exception as e:
            logger.error("Error registering outbound message for %s: %s", user_id, e)

    def consume_agent_outbound_echo(self, user_id: str, text: str) -> bool:
        """
        Consume outbound marker if this echo matches a recent agent-sent message.
        """
        if not self.redis_client or not user_id or not text:
            return False

        try:
            key = self._build_echo_key(user_id, text)
            removed = self.redis_client.delete(key)
            return removed > 0
        except Exception as e:
            logger.error("Error consuming outbound echo for %s: %s", user_id, e)
            return False
    
    def is_blocked(self, sender_id: str) -> bool:
        """
        Check if agent is blocked from responding to this user.
        
        Args:
            sender_id: Instagram user ID
            
        Returns:
            True if agent is blocked, False otherwise
        """
        if not self.redis_client:
            logger.debug("Redis not available, no block applied")
            return False
        
        try:
            key = f"{INTERACTION_LOCK_PREFIX}{sender_id}"
            is_locked = self.redis_client.exists(key) > 0
            
            if is_locked:
                # Get remaining TTL
                ttl = self.redis_client.ttl(key)
                logger.debug("[BLOCK] Agent blocked for %s (%.0f sec remaining)", sender_id[-6:], ttl)
            
            return is_locked
        except Exception as e:
            logger.error("Error checking block status for %s: %s", sender_id, e)
            return False
    
    def unblock(self, sender_id: str) -> None:
        """
        Manually unblock agent for a user.
        
        Args:
            sender_id: Instagram user ID
        """
        if not self.redis_client:
            return
        
        try:
            key = f"{INTERACTION_LOCK_PREFIX}{sender_id}"
            self.redis_client.delete(key)
            logger.info("[UNBLOCK] Agent unblocked for %s", sender_id[-6:])
        except Exception as e:
            logger.error("Error unblocking for %s: %s", sender_id, e)
    
    def get_remaining_block_time(self, sender_id: str) -> Optional[int]:
        """
        Get remaining block time in seconds.
        
        Args:
            sender_id: Instagram user ID
            
        Returns:
            Remaining seconds, or None if not blocked
        """
        if not self.redis_client:
            return None
        
        try:
            key = f"{INTERACTION_LOCK_PREFIX}{sender_id}"
            ttl = self.redis_client.ttl(key)
            
            if ttl > 0:
                return ttl
            return None
        except Exception as e:
            logger.error("Error getting block time for %s: %s", sender_id, e)
            return None


# Global instance
_blocker: Optional[InteractionBlocker] = None


def get_blocker() -> InteractionBlocker:
    """Get or create global InteractionBlocker instance."""
    global _blocker
    if _blocker is None:
        _blocker = InteractionBlocker()
    return _blocker
