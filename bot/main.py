"""
bot/main.py — FastAPI application entrypoint for magicpin Vera AI Challenge.
"""

from __future__ import annotations
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from bot.models import (
    ContextPushRequest, ContextPushResponse,
    TickRequest, TickResponse, ActionPayload,
    ReplyRequest, ReplyResponse,
    HealthzResponse, MetadataResponse,
    ConversationState, MerchantIntentState, TriggerLifecycleState
)
from bot.store import store
from bot.decision_engine import DecisionEngine
from bot.intent_engine import IntentEngine
from bot.realizer import MessageRealizer
from bot.claim_ledger import build_claim_ledger_from_contexts
from bot.safety_guard import SafetyGuard

app = FastAPI(title="magicpin Vera AI Bot", version="2.0.0")


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/v1/healthz", response_model=HealthzResponse)
async def healthz():
    """Fast, zero-latency health check probe."""
    return HealthzResponse(
        status="ok",
        uptime_seconds=store.uptime_seconds,
        contexts_loaded=store.get_loaded_counts()
    )


@app.get("/v1/metadata", response_model=MetadataResponse)
async def metadata():
    """Returns candidate bot identity and approach overview."""
    return MetadataResponse()


@app.post("/v1/context")
async def push_context(body: ContextPushRequest):
    # Validate scope
    valid_scopes = {"category", "merchant", "customer", "trigger"}
    if body.scope not in valid_scopes:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"accepted": False, "reason": "invalid_scope"},
        )

    accepted, ack_or_reason, current_version = store.push_context(
        scope=body.scope,
        context_id=body.context_id,
        version=body.version,
        payload=body.payload,
        delivered_at=body.delivered_at,
    )

    if not accepted:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"accepted": False, "reason": ack_or_reason, "current_version": current_version},
        )

    # Retrieve stored_at timestamp from metadata
    meta = store.get_context_meta(body.scope, body.context_id)
    stored_at = meta.get("stored_at") if meta else ""
    return {"accepted": True, "ack_id": ack_or_reason, "stored_at": stored_at}


@app.post("/v1/tick", response_model=TickResponse)
async def tick(body: TickRequest):
    candidates = []

    for trg_id in body.available_triggers:
        trg_payload, trg_ver = store.get_context_with_version("trigger", trg_id)
        if not trg_payload:
            continue

        merchant_id = trg_payload.get("merchant_id")
        if not merchant_id:
            continue

        merchant_payload, mer_ver = store.get_context_with_version("merchant", merchant_id)
        if not merchant_payload:
            continue

        cat_slug = merchant_payload.get("category_slug", "")
        category_payload, cat_ver = store.get_context_with_version("category", cat_slug)
        if not category_payload:
            continue

        customer_id = trg_payload.get("customer_id")
        customer_payload, cust_ver = (None, 0)
        if customer_id:
            customer_payload, cust_ver = store.get_context_with_version("customer", customer_id)

        # Build DecisionObject with simulated request timestamp now_str
        decision = DecisionEngine.evaluate_trigger(
            trigger=trg_payload,
            merchant=merchant_payload,
            category=category_payload,
            customer=customer_payload,
            cat_ver=cat_ver, mer_ver=mer_ver, trg_ver=trg_ver, cust_ver=cust_ver,
            now_str=body.now
        )

        if not decision:
            continue

        candidates.append((decision, category_payload, merchant_payload, trg_payload, customer_payload, cat_ver, mer_ver, trg_ver, cust_ver))

    # Group candidate decisions by merchant_id and select top-1 highest utility decision per merchant
    merchant_top_decisions = {}
    for item in candidates:
        dec = item[0]
        m_id = dec.merchant_id
        if m_id not in merchant_top_decisions or dec.utility_score > merchant_top_decisions[m_id][0].utility_score:
            merchant_top_decisions[m_id] = item

    actions = []
    # Sort top-1 decisions per merchant by utility_score descending, capped at 20 actions per tick
    selected_items = sorted(
        merchant_top_decisions.values(),
        key=lambda item: item[0].utility_score,
        reverse=True
    )[:20]

    for item in selected_items:
        decision, category_payload, merchant_payload, trg_payload, customer_payload, cat_ver, mer_ver, trg_ver, cust_ver = item
        trg_id = decision.trigger_id
        merchant_id = decision.merchant_id
        customer_id = decision.customer_id

        # Build Claim Ledger
        ledger = build_claim_ledger_from_contexts(
            category_payload, merchant_payload, trg_payload, customer_payload,
            cat_ver, mer_ver, trg_ver, cust_ver
        )

        # Realize Message Body
        body_text, rationale = MessageRealizer.realize_proactive(
            decision=decision,
            category=category_payload,
            merchant=merchant_payload,
            trigger=trg_payload,
            customer=customer_payload,
            ledger=ledger
        )

        # Enforce Safety Guard (Strips URLs, converts to 100% ASCII-safe text)
        body_text = SafetyGuard.sanitize_output(body_text, decision.forbidden_claims)
        rationale = SafetyGuard.to_ascii_safe(rationale)

        # Generate unique conversation ID
        conv_id = f"conv_{merchant_id}_{trg_id}"

        # Track suppression and update lifecycle state
        store.add_suppression(decision.suppression_key)
        store.update_conversation_record(conv_id, {
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "trigger_id": trg_id,
            "conv_state": ConversationState.PROACTIVE_SENT,
            "trigger_state": TriggerLifecycleState.PROMOTED
        })

        actions.append(ActionPayload(
            conversation_id=conv_id,
            merchant_id=merchant_id,
            customer_id=customer_id,
            send_as=decision.send_as,
            trigger_id=trg_id,
            template_name=decision.template_name,
            template_params=[SafetyGuard.to_ascii_safe(p) for p in decision.template_params],
            body=body_text,
            cta=decision.cta_type,
            suppression_key=decision.suppression_key,
            rationale=rationale
        ))

    return TickResponse(actions=actions)


@app.post("/v1/reply", response_model=ReplyResponse)
async def reply(body: ReplyRequest):
    record = store.get_conversation_record(body.conversation_id)

    # Classify merchant intent
    intent, confidence, reason = IntentEngine.classify_intent(
        message=body.message,
        past_turns=record.get("turns", [])
    )

    # Track auto-reply turns
    if intent == MerchantIntentState.AUTO_REPLY_DETECTED:
        record["auto_reply_count"] += 1

    # Record current turn
    store.record_turn(
        conversation_id=body.conversation_id,
        from_role=body.from_role,
        message=body.message,
        meta={"intent": intent.value, "confidence": confidence, "reason": reason}
    )

    # Load merchant and category context if available
    merchant_id = body.merchant_id or record.get("merchant_id")
    merchant_payload = store.get_context("merchant", merchant_id) if merchant_id else None
    cat_slug = merchant_payload.get("category_slug", "") if merchant_payload else ""
    category_payload = store.get_context("category", cat_slug) if cat_slug else None

    # Realize response turn
    action_type, reply_body, cta, wait_seconds = MessageRealizer.realize_reply(
        merchant_intent=intent,
        conversation_record=record,
        merchant=merchant_payload,
        category=category_payload
    )

    # Sanitize outputs to 100% plain ASCII
    if reply_body:
        reply_body = SafetyGuard.sanitize_output(reply_body)
    
    rationale = SafetyGuard.to_ascii_safe(f"Intent classified as {intent.value} ({reason}). Action choice: {action_type}.")

    if action_type == "end":
        store.update_conversation_record(body.conversation_id, {"conv_state": ConversationState.ENDED})
        return ReplyResponse(action="end", body=reply_body, cta="none", rationale=rationale)

    if action_type == "wait":
        store.update_conversation_record(body.conversation_id, {"conv_state": ConversationState.WAIT_BACKOFF})
        return ReplyResponse(action="wait", wait_seconds=wait_seconds, rationale=rationale)

    # Standard send action
    store.update_conversation_record(body.conversation_id, {"conv_state": ConversationState.EXECUTING})
    return ReplyResponse(action="send", body=reply_body, cta=cta or "open_ended", rationale=rationale)


# Entry point for uvicorn CLI
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
