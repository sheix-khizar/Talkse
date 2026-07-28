"""
Rule-based fast-path routing for simple conversational turns.
Goal: avoid an LLM round-trip for yes/no confirmations and bare digit/time
answers to a question we just asked. Falls through to the LLM (returns None)
for anything that isn't a confident match.
"""
import re

_YES_WORDS = {
    "yes", "yeah", "yep", "yup", "correct", "right", "sure",
    "sounds good", "that's right", "thats right", "confirmed", "ok", "okay"
}
_NO_WORDS = {
    "no", "nope", "not right", "wrong", "incorrect", "that's wrong", "thats wrong"
}

_DIGIT_ONLY_RE = re.compile(r"^\s*\d{1,2}(:\d{2})?\s*(am|pm)?\s*$", re.IGNORECASE)


def _normalize(text: str) -> str:
    return text.strip().lower().strip(".!")


def try_rule_based_route(transcript: str, state: dict) -> dict | None:
    """
    Attempts to resolve a turn without calling the LLM.

    Returns a dict compatible with merge_state()'s `new_extracted` argument,
    or None if the LLM should handle this turn instead.

    Only fires when we can be confident from conversational context
    (i.e. we know what field we just asked for).
    """
    if not transcript:
        return None

    norm = _normalize(transcript)
    awaiting_field = state.get("_awaiting_field")  # set by conversation_loop before this call

    # --- Confirmation turns (e.g. after "Does that sound right?") ---
    if state.get("_awaiting_confirmation"):
        if norm in _YES_WORDS:
            return {"intent": state.get("intent"), "_confirmed": True}
        if norm in _NO_WORDS:
            return {"intent": state.get("intent"), "_confirmed": False}
        return None  # ambiguous reply to a confirmation -> let the LLM parse it

    # --- Bare time answers (e.g. we just asked "what day and time works?") ---
    if awaiting_field == "preferred_time" and _DIGIT_ONLY_RE.match(norm):
        return {"preferred_time": transcript.strip()}

    # --- Bare intent answers (book/reschedule/cancel as a single word) ---
    if awaiting_field == "intent":
        if norm in ("book", "booking", "book an appointment", "make an appointment"):
            return {"intent": "book"}
        if norm in ("reschedule", "change my appointment", "move my appointment"):
            return {"intent": "reschedule"}
        if norm in ("cancel", "cancel my appointment"):
            return {"intent": "cancel"}

    return None
