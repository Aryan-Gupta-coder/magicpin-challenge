"""
bot/store.py — Thread-safe atomic in-memory context and state store.
"""

from __future__ import annotations
import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bot.models import ConversationState, MerchantIntentState, TriggerLifecycleState


class MemoryStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._start_time = time.time()
        
        # (scope, context_id) -> {"version": int, "payload": dict, "stored_at": str}
        self._contexts: Dict[Tuple[str, str], Dict[str, Any]] = {}
        
        # suppression_key -> expiration_timestamp (float)
        self._suppressions: Dict[str, float] = {}
        
        # conversation_id -> conversation state record
        self._conversations: Dict[str, Dict[str, Any]] = {}

    @property
    def uptime_seconds(self) -> int:
        return int(time.time() - self._start_time)

    # -------------------------------------------------------------------------
    # Context Ingestion & Retrieval
    # -------------------------------------------------------------------------
    def push_context(self, scope: str, context_id: str, version: int, payload: Dict[str, Any], delivered_at: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Ingest context with version idempotency.
        Returns: (accepted, reason_or_ack_id, current_version_if_conflict)
        """
        with self._lock:
            key = (scope, context_id)
            current = self._contexts.get(key)

            if current and current["version"] > version:
                return False, "stale_version", current["version"]

            self._contexts[key] = {
                "version": version,
                "payload": payload,
                "stored_at": datetime.utcnow().isoformat() + "Z",
                "delivered_at": delivered_at or datetime.utcnow().isoformat() + "Z",
            }
            ack_id = f"ack_{context_id}_v{version}"
            return True, ack_id, None

    def get_context(self, scope: str, context_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            ctx = self._contexts.get((scope, context_id))
            return ctx["payload"] if ctx else None

    def get_context_with_version(self, scope: str, context_id: str) -> Tuple[Optional[Dict[str, Any]], int]:
        with self._lock:
            ctx = self._contexts.get((scope, context_id))
            if ctx:
                return ctx["payload"], ctx["version"]
            return None, 0

    def get_loaded_counts(self) -> Dict[str, int]:
        with self._lock:
            counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
            for (scope, _), _ in self._contexts.items():
                if scope in counts:
                    counts[scope] += 1
            return counts

    def get_context_meta(self, scope: str, context_id: str) -> Optional[Dict[str, Any]]:
        """Return full context dict (payload, version, stored_at, delivered_at) if exists."""
        with self._lock:
            return self._contexts.get((scope, context_id))

    # -------------------------------------------------------------------------
    # Suppression & Deduplication
    # -------------------------------------------------------------------------
    def is_suppressed(self, suppression_key: str, now_ts: float = None) -> bool:
        if not suppression_key:
            return False
        if now_ts is None:
            now_ts = time.time()
        with self._lock:
            exp = self._suppressions.get(suppression_key)
            if exp and exp > now_ts:
                return True
            return False

    def add_suppression(self, suppression_key: str, duration_seconds: float = 86400 * 7):
        if not suppression_key:
            return
        with self._lock:
            self._suppressions[suppression_key] = time.time() + duration_seconds

    # -------------------------------------------------------------------------
    # Conversation & Turn State
    # -------------------------------------------------------------------------
    def get_conversation_record(self, conversation_id: str) -> Dict[str, Any]:
        with self._lock:
            if conversation_id not in self._conversations:
                self._conversations[conversation_id] = {
                    "conversation_id": conversation_id,
                    "merchant_id": None,
                    "customer_id": None,
                    "trigger_id": None,
                    "conv_state": ConversationState.IDLE,
                    "merchant_intent": MerchantIntentState.UNKNOWN,
                    "trigger_state": TriggerLifecycleState.PENDING,
                    "auto_reply_count": 0,
                    "turns": [],
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "updated_at": datetime.utcnow().isoformat() + "Z",
                }
            return self._conversations[conversation_id]

    def update_conversation_record(self, conversation_id: str, updates: Dict[str, Any]):
        with self._lock:
            record = self.get_conversation_record(conversation_id)
            record.update(updates)
            record["updated_at"] = datetime.utcnow().isoformat() + "Z"

    def record_turn(self, conversation_id: str, from_role: str, message: str, meta: Dict[str, Any] = None):
        with self._lock:
            record = self.get_conversation_record(conversation_id)
            record["turns"].append({
                "from": from_role,
                "msg": message,
                "ts": datetime.utcnow().isoformat() + "Z",
                "meta": meta or {}
            })
            record["updated_at"] = datetime.utcnow().isoformat() + "Z"

    def wipe(self):
        with self._lock:
            self._contexts.clear()
            self._suppressions.clear()
            self._conversations.clear()


# Global store instance
store = MemoryStore()
