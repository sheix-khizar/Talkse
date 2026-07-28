import os
import sys
import time
import json
import uuid
from dotenv import load_dotenv

# Import functions from poc.py, booking_engine, mic_input, audio_playback
from poc import transcribe, extract_intent, synthesize, merge_state
import booking_engine as be
import db
from conversation_router import try_rule_based_route
from rag.rag_chat import answer_question_streaming

def next_missing_field(state: dict) -> str | None:
    """Returns the name of the first missing required field for state['intent'], or None if complete."""
    intent = state.get("intent")
    if not intent or intent in ("unclear", "none", "null"):
        return "intent"
        
    required_map = {
        "book": ["service", "preferred_time", "caller_name"],
        "reschedule": ["existing_appointment_ref", "preferred_time"],
        "cancel": ["existing_appointment_ref"],
    }
    
    fields = required_map.get(intent, [])
    for field in fields:
        val = state.get(field)
        if val is None or str(val).strip() == "" or str(val).lower() == "null":
            return field
            
    return None

def prompt_for_field(field: str) -> str:
    """Returns a natural hardcoded question prompt for a missing field."""
    prompts = {
        "intent": "Hi! Are you looking to book, reschedule, or cancel an appointment today?",
        "service": "What service or treatment would you like to book?",
        "preferred_time": "What day and time works best for you?",
        "caller_name": "May I have your full name, please?",
        "existing_appointment_ref": "Could you please provide your existing appointment reference or date?",
    }
    return prompts.get(field, "Could you please provide more details?")

def safe_transcribe_with_retry(audio_path: str) -> tuple[str | None, float]:
    """Wraps STT call in a retry block."""
    try:
        return transcribe(audio_path)
    except Exception as e:
        print(f"[STT Retry Warning] Transcribe attempt 1 failed: {e}. Retrying once...")
        time.sleep(1)
        try:
            return transcribe(audio_path)
        except Exception as retry_err:
            print(f"[STT Error] Transcribe failed permanently: {retry_err}")
            return None, 0.0

def safe_extract_intent_with_retry(transcript: str) -> tuple[dict, float]:
    """Wraps LLM call in a retry block."""
    try:
        return extract_intent(transcript)
    except Exception as e:
        print(f"[LLM Retry Warning] Intent extraction attempt 1 failed: {e}. Retrying once...")
        time.sleep(1)
        try:
            return extract_intent(transcript)
        except Exception as retry_err:
            print(f"[LLM Error] Intent extraction failed permanently: {retry_err}")
            fallback = {
                "intent": "unclear",
                "service": None,
                "preferred_time": None,
                "caller_name": None,
                "existing_appointment_ref": None,
                "confidence": 0.0
            }
            return fallback, 0.0

def safe_synthesize_with_retry(text: str, out_path: str) -> float:
    """Wraps TTS batch call in a retry block."""
    try:
        return synthesize(text, out_path)
    except Exception as e:
        print(f"[TTS Retry Warning] Synthesis attempt 1 failed: {e}. Retrying once...")
        time.sleep(1)
        try:
            return synthesize(text, out_path)
        except Exception as retry_err:
            print(f"[TTS Error] Synthesis failed permanently: {retry_err}")
            return 0.0

def handle_turn(transcript: str, state: dict) -> dict:
    """
    Runs one turn of conversation logic against `state` (mutated in place)
    given an already-transcribed `transcript`. Does NOT do TTS synthesis or
    audio playback — the caller owns that, since the Streamlit UI and the
    local-mic CLI path synthesize/play audio differently.

    Returns a dict:
        {
            "reply_text": str,
            "llm_time": float,
            "routed": bool,           # True if the rule-based fast path handled it
            "is_faq": bool,           # True if this turn should stream multiple
                                        TTS chunks (one per RAG answer sentence)
            "faq_stream": generator | None,  # only set if is_faq is True; first
                                                yield is the sources list, rest are
                                                answer sentences (see rag/rag_chat.py)
            "terminal": bool,         # True if the caller should stop the
                                        conversation after this turn (done/rejected/
                                        transferred/emergency/flagged)
        }
    """
    # 1. Emergency check
    emergency_msg = be.check_emergency_protocol(transcript)
    if emergency_msg:
        state["status"] = "emergency_transferred"
        return {"reply_text": emergency_msg, "llm_time": 0.0, "routed": False,
                "is_faq": False, "faq_stream": None, "terminal": True}

    # 2. Fast-path router or LLM
    state["_awaiting_field"] = next_missing_field(state)
    routed = try_rule_based_route(transcript, state)
    if routed is not None:
        extracted, llm_time = routed, 0.0
    else:
        extracted, llm_time = safe_extract_intent_with_retry(transcript)

    # 3. Contraindication check
    svc_candidate = be.config.get_service(state.get("service") or extracted.get("service") or "")
    contra_reason = be.check_contraindications(svc_candidate, transcript)
    if contra_reason:
        state["status"] = "flagged_human_review"
        return {"reply_text": contra_reason, "llm_time": llm_time, "routed": routed is not None,
                "is_faq": False, "faq_stream": None, "terminal": True}

    # 4. Merge state
    merge_state(state, extracted)

    # 5. service_check branch
    if state["intent"] == "service_check":
        raw_svc = (extracted.get("service") or "").lower().strip()
        trans_lower = transcript.lower().strip()

        general_query_keywords = [
            "what service", "what kind of service", "what treatment", "what do you offer",
            "what do you provide", "services do you provide", "services do you offer",
            "services you provide", "services you offer", "list of services", "all services",
            "what do you have", "what can i book", "what are your services", "tell me about your services",
            "which services", "what kind of treatments"
        ]

        is_general_inquiry = (
            raw_svc in ("service", "services", "treatment", "treatments", "all", "general")
            or any(kw in trans_lower for kw in general_query_keywords)
        )

        if is_general_inquiry:
            reply_text = (
                "We offer a variety of aesthetic treatments including Botox and neuromodulators, "
                "dermal fillers, HydraFacials, chemical peels, and new patient consultations. "
                "Which service would you like to book or learn more about?"
            )
            return {
                "reply_text": reply_text,
                "llm_time": llm_time,
                "routed": routed is not None,
                "is_faq": False,
                "faq_stream": None,
                "terminal": False
            }

        matched = be.config.get_service(extracted.get("service") or transcript)
        if matched:
            reply_text = f"Yes, we offer {matched['name']}. What day works best for you?"
            state["intent"] = "book"
            state["service"] = matched["id"]
            return {
                "reply_text": reply_text,
                "llm_time": llm_time,
                "routed": routed is not None,
                "is_faq": False,
                "faq_stream": None,
                "terminal": False
            }
        else:
            # Unmatched specific treatment -> query RAG knowledge base
            stream_gen = answer_question_streaming(transcript)
            return {
                "reply_text": None,
                "llm_time": llm_time,
                "routed": routed is not None,
                "is_faq": True,
                "faq_stream": stream_gen,
                "terminal": False
            }

    # 6. faq branch -> hands back the RAG streaming generator, caller synthesizes it
    if state["intent"] == "faq":
        stream_gen = answer_question_streaming(transcript)
        return {"reply_text": None, "llm_time": llm_time, "routed": routed is not None,
                "is_faq": True, "faq_stream": stream_gen, "terminal": False}

    # 7. Missing field or execute booking action
    missing = next_missing_field(state)
    if missing is not None:
        reply_text = prompt_for_field(missing)
        terminal = False
    else:
        state["status"] = "executing"
        intent = state["intent"]
        if intent == "book":
            result = be.book_appointment(state, state["idempotency_key"])
            state["booking_result"] = result
            if result["status"] == "confirmed":
                reply_text, state["status"] = result["message"], "done"
            else:
                reply_text, state["status"] = f"I couldn't complete that booking: {result['reason']}", "rejected"
        elif intent == "reschedule":
            result = be.reschedule_appointment(state["existing_appointment_ref"], state["preferred_time"])
            state["booking_result"] = result
            if result["status"] == "rescheduled":
                reply_text, state["status"] = result["message"], "done"
            else:
                reply_text, state["status"] = f"I couldn't reschedule that appointment: {result['reason']}", "rejected"
        elif intent == "cancel":
            result = be.cancel_appointment(state["existing_appointment_ref"])
            state["booking_result"] = result
            if result["status"] == "cancelled":
                reply_text, state["status"] = result["message"], "done"
            else:
                reply_text, state["status"] = f"I couldn't cancel that appointment: {result['reason']}", "rejected"
        else:
            reply_text, state["status"] = "Action could not be determined.", "rejected"
        terminal = state["status"] in ("done", "rejected")

    return {"reply_text": reply_text, "llm_time": llm_time, "routed": routed is not None,
            "is_faq": False, "faq_stream": None, "terminal": terminal}

# CLI mode disabled for FastAPI migration
