"""
Golden/regression tests for deterministic, dependency-free logic.

Run this BEFORE starting the FastAPI migration and again AFTER each step.
If any of these fail post-migration, you changed behavior, not just location.
"""
import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../app/services")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from conversation_loop import next_missing_field, prompt_for_field
from conversation_router import try_rule_based_route
import booking_engine as be
import clinic_config as config
import conversation_loop as cl

# ---------- next_missing_field ----------

def test_missing_field_no_intent():
    assert next_missing_field({"intent": None}) == "intent"

def test_missing_field_unclear_intent():
    assert next_missing_field({"intent": "unclear"}) == "intent"

def test_missing_field_book_needs_service_first():
    state = {"intent": "book", "service": None, "preferred_time": "tomorrow", "caller_name": "Sam"}
    assert next_missing_field(state) == "service"

def test_missing_field_book_complete():
    state = {"intent": "book", "service": "svc_botox_touchup", "preferred_time": "tomorrow 2pm", "caller_name": "Sam"}
    assert next_missing_field(state) is None

def test_missing_field_cancel_needs_ref():
    assert next_missing_field({"intent": "cancel", "existing_appointment_ref": None}) == "existing_appointment_ref"

def test_missing_field_reschedule_order():
    # existing_appointment_ref must be asked before preferred_time
    state = {"intent": "reschedule", "existing_appointment_ref": None, "preferred_time": "next week"}
    assert next_missing_field(state) == "existing_appointment_ref"


# ---------- prompt_for_field ----------

def test_prompt_known_fields_unchanged():
    # These exact strings are what callers currently hear. Pin them.
    assert prompt_for_field("intent") == "Hi! Are you looking to book, reschedule, or cancel an appointment today?"
    assert prompt_for_field("service") == "What service or treatment would you like to book?"
    assert prompt_for_field("preferred_time") == "What day and time works best for you?"
    assert prompt_for_field("caller_name") == "May I have your full name, please?"
    assert prompt_for_field("existing_appointment_ref") == "Could you please provide your existing appointment reference or date?"

def test_prompt_unknown_field_fallback():
    assert prompt_for_field("something_unmapped") == "Could you please provide more details?"


# ---------- conversation_router (rule-based fast path) ----------

def test_router_confirmation_yes():
    state = {"_awaiting_confirmation": True, "intent": "book"}
    result = try_rule_based_route("yes", state)
    assert result == {"intent": "book", "_confirmed": True}

def test_router_confirmation_no():
    state = {"_awaiting_confirmation": True, "intent": "book"}
    result = try_rule_based_route("no thanks", state)
    assert result is None  # "no thanks" isn't in the exact _NO_WORDS set today

def test_router_confirmation_ambiguous_falls_to_llm():
    state = {"_awaiting_confirmation": True, "intent": "book"}
    assert try_rule_based_route("maybe", state) is None

def test_router_bare_time_answer():
    state = {"_awaiting_field": "preferred_time"}
    result = try_rule_based_route("2pm", state)
    assert result == {"preferred_time": "2pm"}

def test_router_bare_intent_book():
    state = {"_awaiting_field": "intent"}
    assert try_rule_based_route("book", state) == {"intent": "book"}

def test_router_empty_transcript():
    assert try_rule_based_route("", {}) is None


# ---------- booking_engine: emergency + contraindication checks ----------

def test_emergency_detected():
    msg = be.check_emergency_protocol("I'm having difficulty breathing right now")
    assert msg is not None
    assert "911" in msg

def test_emergency_not_triggered_on_unrelated_text():
    assert be.check_emergency_protocol("I'd like to book a facial") is None

def test_emergency_none_text():
    assert be.check_emergency_protocol(None) is None

def test_contraindication_pregnancy_blocks_botox():
    svc = config.get_service("svc_botox_touchup")
    reason = be.check_contraindications(svc, "I'm currently pregnant")
    assert reason is not None
    assert "Botox" in reason or "cannot be performed" in reason

def test_KNOWN_BUG_contraindication_false_positive_on_unrelated_condition():
    """
    Discovered gap (found by running this suite against the real code, not
    assumed from docs): check_contraindications() triggers on
        `service.get("category") in (...) or contraindications`
    The `or contraindications` half means ANY service with a non-empty
    contraindications list gets blocked for pregnancy/breastfeeding/accutane
    mentions, even if that specific condition isn't actually in the list.
    HydraFacial's real contraindications are ["active skin infection",
    "recent sunburn"] -- pregnancy isn't one of them -- but it still blocks.
    This PINS today's (arguably wrong) behavior. Decide deliberately whether
    to fix this during migration; don't let it change silently.
    """
    svc = config.get_service("svc_hydrafacial")
    reason = be.check_contraindications(svc, "I'm pregnant")
    assert reason is not None  # current (buggy) behavior: false-positive block

def test_contraindication_no_service_returns_none():
    assert be.check_contraindications(None, "I'm pregnant") is None


# ---------- clinic_config lookups (documents KNOWN BUGS — don't silently "fix" these while migrating) ----------

def test_get_service_botox_resolves():
    svc = config.get_service("botox")
    assert svc is not None
    assert svc["id"] == "svc_botox_touchup"

def test_get_service_consultation_resolves():
    svc = config.get_service("consultation")
    assert svc["id"] == "svc_consult"

def test_get_service_exact_id():
    svc = config.get_service("svc_hydrafacial")
    assert svc["name"] == "HydraFacial"

def test_filler_keyword_resolves_correctly():
    """
    NOTE: the Architecture Doc (Section 6, item #4) claims 'filler' maps to a
    nonexistent 'svc_filler_juvederm'. Running this against the actual code in
    this branch shows that bug is ALREADY FIXED here -- it correctly resolves
    to svc_filler_lips. Trust the code over the doc; the doc is stale.
    """
    svc = config.get_service("filler")
    assert svc is not None
    assert svc["id"] == "svc_filler_lips"

def test_hydrafacial_keyword_resolves_correctly():
    """Same correction: 'hydrafacial' keyword resolves fine in this branch."""
    svc = config.get_service("hydrafacial")
    assert svc is not None
    assert svc["id"] == "svc_hydrafacial"

def test_get_provider_by_id():
    prov = config.get_provider("prov_001")
    assert prov["name"] == "Dr. Emily Carter, MD"

def test_providers_for_service():
    provs = config.providers_for_service("svc_botox_touchup")
    ids = {p["id"] for p in provs}
    assert ids == {"prov_001", "prov_003"}


# ---------- handle_turn() end-to-end ----------

def base_state(**overrides):
    state = {
        "intent": None, "service": None, "preferred_time": None,
        "caller_name": None, "existing_appointment_ref": None,
        "turn_count": 0, "status": "collecting",
        "idempotency_key": "test_key_001", "booking_result": None,
    }
    state.update(overrides)
    return state


def test_emergency_overrides_everything(monkeypatch):
    # Even if extract_intent would be called, emergency check runs first and
    # short-circuits -- assert the LLM is never even invoked.
    def boom(*a, **k):
        raise AssertionError("extract_intent should not be called on emergency path")
    monkeypatch.setattr(cl, "extract_intent", boom)

    state = base_state(intent="book")
    result = cl.handle_turn("I'm having difficulty breathing", state)

    assert result["terminal"] is True
    assert state["status"] == "emergency_transferred"
    assert "911" in result["reply_text"]


def test_contraindication_flags_for_human_review(monkeypatch):
    monkeypatch.setattr(cl, "extract_intent", lambda t: (
        {"intent": "book", "service": None, "preferred_time": None,
         "caller_name": None, "existing_appointment_ref": None, "confidence": 0.9}, 0.1
    ))
    state = base_state(intent="book", service="svc_botox_touchup")
    result = cl.handle_turn("I'm currently pregnant", state)

    assert result["terminal"] is True
    assert state["status"] == "flagged_human_review"
    assert "cannot be performed" in result["reply_text"]


def test_missing_field_prompts_for_service(monkeypatch):
    monkeypatch.setattr(cl, "extract_intent", lambda t: (
        {"intent": "book", "service": None, "preferred_time": None,
         "caller_name": None, "existing_appointment_ref": None, "confidence": 0.9}, 0.1
    ))
    state = base_state()
    result = cl.handle_turn("I'd like to book an appointment", state)

    assert result["terminal"] is False
    assert result["reply_text"] == "What service or treatment would you like to book?"


def test_full_booking_success(monkeypatch):
    monkeypatch.setattr(cl, "extract_intent", lambda t: (
        {"intent": None, "service": None, "preferred_time": None,
         "caller_name": None, "existing_appointment_ref": None, "confidence": 0.9}, 0.1
    ))
    monkeypatch.setattr(cl.be, "book_appointment", lambda state, key: {
        "status": "confirmed",
        "message": "Successfully booked Botox Touch-Up with Dr. Emily Carter for Friday, Aug 1 at 02:00 PM.",
        "appointment": {"id": "fake-uuid"},
    })

    state = base_state(intent="book", service="svc_botox_touchup",
                        preferred_time="next Friday at 2pm", caller_name="Sarah Connor")
    result = cl.handle_turn("yes that's correct", state)

    assert result["terminal"] is True
    assert state["status"] == "done"
    assert "Successfully booked" in result["reply_text"]


def test_booking_rejected_by_business_rules(monkeypatch):
    monkeypatch.setattr(cl, "extract_intent", lambda t: (
        {"intent": None, "service": None, "preferred_time": None,
         "caller_name": None, "existing_appointment_ref": None, "confidence": 0.9}, 0.1
    ))
    monkeypatch.setattr(cl.be, "book_appointment", lambda state, key: {
        "status": "rejected",
        "reason": "Dr. Emily Carter does not work on Sundays (works Monday, Wednesday, Friday).",
    })

    state = base_state(intent="book", service="svc_botox_touchup",
                        preferred_time="this Sunday at 2pm", caller_name="Sarah Connor")
    result = cl.handle_turn("that's right", state)

    assert result["terminal"] is False
    assert state["status"] == "collecting"
    assert "I couldn't lock in that time" in result["reply_text"]


def test_cancel_flow_success(monkeypatch):
    monkeypatch.setattr(cl, "extract_intent", lambda t: (
        {"intent": None, "service": None, "preferred_time": None,
         "caller_name": None, "existing_appointment_ref": None, "confidence": 0.9}, 0.1
    ))
    monkeypatch.setattr(cl.be, "cancel_appointment", lambda ref: {
        "status": "cancelled",
        "message": "Appointment reference 'conv_123' for Jane Doe has been cancelled.",
    })
    state = base_state(intent="cancel", existing_appointment_ref="conv_123")
    result = cl.handle_turn("please cancel it", state)

    assert result["terminal"] is True
    assert state["status"] == "done"


def test_service_check_general_inquiry(monkeypatch):
    monkeypatch.setattr(cl, "extract_intent", lambda t: (
        {"intent": "service_check", "service": "services", "preferred_time": None,
         "caller_name": None, "existing_appointment_ref": None, "confidence": 0.8}, 0.1
    ))

    def fake_rag_stream(*args, **kwargs):
        yield [{"title": "Services", "url": "https://example.test/services"}]
        yield "We offer Botox, dermal fillers, HydraFacials, and consultations."

    monkeypatch.setattr(cl, "answer_question_streaming", fake_rag_stream)

    state = base_state()
    result = cl.handle_turn("what services do you offer?", state)

    assert result["terminal"] is False
    assert result["is_faq"] is True


def test_service_check_specific_match_switches_to_book(monkeypatch):
    monkeypatch.setattr(cl, "extract_intent", lambda t: (
        {"intent": "service_check", "service": "botox", "preferred_time": None,
         "caller_name": None, "existing_appointment_ref": None, "confidence": 0.8}, 0.1
    ))
    state = base_state()
    result = cl.handle_turn("do you offer botox?", state)

    assert result["terminal"] is False
    assert state["intent"] == "book"
    assert state["service"] == "svc_botox_touchup"


def test_service_check_unmatched_routes_to_rag(monkeypatch):
    monkeypatch.setattr(cl, "extract_intent", lambda t: (
        {"intent": "service_check", "service": "ultherapy", "preferred_time": None,
         "caller_name": None, "existing_appointment_ref": None, "confidence": 0.6}, 0.1
    ))

    def fake_rag_stream(*args, **kwargs):
        yield [{"title": "FAQ", "url": "https://example.test/faq"}]
        yield "We don't currently offer Ultherapy, but I can have someone call you back."

    monkeypatch.setattr(cl, "answer_question_streaming", fake_rag_stream)

    state = base_state()
    result = cl.handle_turn("do you do ultherapy?", state)

    assert result["is_faq"] is True
    assert result["terminal"] is False
    stream = result["faq_stream"]
    sources = next(stream)
    assert sources[0]["title"] == "FAQ"


def test_explicit_faq_intent_routes_to_rag(monkeypatch):
    monkeypatch.setattr(cl, "extract_intent", lambda t: (
        {"intent": "faq", "service": None, "preferred_time": None,
         "caller_name": None, "existing_appointment_ref": None, "confidence": 0.9}, 0.1
    ))

    def fake_rag_stream(*args, **kwargs):
        yield [{"title": "Cancellation Policy", "url": "https://example.test/policy"}]
        yield "We require 24 hours notice to cancel or reschedule."

    monkeypatch.setattr(cl, "answer_question_streaming", fake_rag_stream)

    state = base_state()
    result = cl.handle_turn("what's your cancellation policy?", state)

    assert result["is_faq"] is True
    assert result["terminal"] is False
