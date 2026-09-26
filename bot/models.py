"""
bot/models.py — Data models, schemas, and dataclasses.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field
from dataclasses import dataclass, field


# =============================================================================
# ENUMS FOR ORTHOGONAL STATES
# =============================================================================

class ConversationState(str, Enum):
    IDLE = "IDLE"
    PROACTIVE_SENT = "PROACTIVE_SENT"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    QUALIFYING = "QUALIFYING"
    READY_TO_ACT = "READY_TO_ACT"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    WAIT_BACKOFF = "WAIT_BACKOFF"
    ENDED = "ENDED"


class MerchantIntentState(str, Enum):
    UNKNOWN = "UNKNOWN"
    POSITIVE_ACK = "POSITIVE_ACK"
    EXPLICIT_EXECUTION = "EXPLICIT_EXECUTION"
    CONDITIONAL_EXECUTION = "CONDITIONAL_EXECUTION"
    DEFER_LATER = "DEFER_LATER"
    REJECTION = "REJECTION"
    OPT_OUT_HOSTILE = "OPT_OUT_HOSTILE"
    AUTO_REPLY_DETECTED = "AUTO_REPLY_DETECTED"
    QUESTION_OFF_TOPIC = "QUESTION_OFF_TOPIC"


class TriggerLifecycleState(str, Enum):
    PENDING = "PENDING"
    PROMOTED = "PROMOTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    SUPPRESSED = "SUPPRESSED"
    EXPIRED = "EXPIRED"


# =============================================================================
# API REQUEST & RESPONSE MODELS (SCHEMAS)
# =============================================================================

class ContextPushRequest(BaseModel):
    scope: str
    context_id: str
    version: int
    payload: Dict[str, Any]
    delivered_at: Optional[str] = None


class ContextPushResponse(BaseModel):
    accepted: bool
    ack_id: Optional[str] = None
    stored_at: Optional[str] = None
    reason: Optional[str] = None
    current_version: Optional[int] = None


class TickRequest(BaseModel):
    now: str
    available_triggers: List[str] = Field(default_factory=list)


class ActionPayload(BaseModel):
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: str = "vera"  # "vera" | "merchant_on_behalf"
    trigger_id: str
    template_name: str
    template_params: List[str] = Field(default_factory=list)
    body: str
    cta: str = "open_ended"
    suppression_key: str
    rationale: str


class TickResponse(BaseModel):
    actions: List[ActionPayload] = Field(default_factory=list)


class ReplyRequest(BaseModel):
    conversation_id: str
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    from_role: str = "merchant"  # "merchant" | "customer"
    message: str
    received_at: Optional[str] = None
    turn_number: int = 1


class ReplyResponse(BaseModel):
    action: str  # "send" | "wait" | "end"
    body: Optional[str] = None
    cta: Optional[str] = "open_ended"
    wait_seconds: Optional[int] = None
    rationale: str


class HealthzResponse(BaseModel):
    status: str = "ok"
    uptime_seconds: int
    contexts_loaded: Dict[str, int]


class MetadataResponse(BaseModel):
    team_name: str = "Team Vera Prime"
    team_members: List[str] = Field(default_factory=lambda: ["Lead AI Engineer"])
    model: str = "hybrid-realizer-v2"
    approach: str = "Deterministic Decision Engine + Fact Claim Ledger + Orthogonal FSM + Constrained LLM Realizer"
    contact_email: str = "vera-prime@magicpin.ai"
    version: str = "2.0.0"
    submitted_at: str = "2026-04-26T00:00:00Z"


# =============================================================================
# DECISION & CLAIM STRUCTURES
# =============================================================================

@dataclass
class ClaimNode:
    claim_id: str
    source_context: str
    context_version: int
    claim_type: str  # "count" | "percentage" | "currency" | "date" | "citation" | "duration"
    raw_value: Any
    permitted_transformations: Set[str] = field(default_factory=set)


@dataclass
class DecisionObject:
    action: str  # "send" | "suppress" | "wait" | "end"
    why_now: str
    trigger_id: str
    trigger_kind: str
    merchant_id: str
    customer_id: Optional[str]
    send_as: str
    context_versions: Dict[str, int]
    primary_signal: str
    supporting_signals: List[str]
    recommended_strategy: str
    audience_segment: str
    utility_score: float
    priority: int
    cta_type: str
    template_name: str
    template_params: List[str]
    suppression_key: str
    approved_facts: List[Dict[str, Any]]
    forbidden_claims: List[str]
    confidence: float
    rationale: str
