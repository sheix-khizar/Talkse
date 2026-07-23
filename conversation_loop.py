import os
import sys
import time
import json
import uuid
from dotenv import load_dotenv

# Import functions from poc.py and booking_engine as instructed
from poc import transcribe, extract_intent, synthesize, merge_state
import booking_engine as be
import db

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
    """Wraps TTS call in a retry block."""
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

def run_conversation(audio_files: list[str]) -> dict:
    """Runs a multi-turn conversation loop using an array of turn audio files."""
    load_dotenv()
    db.init_db()
    
    os.makedirs("turns", exist_ok=True)
    idempotency_key = f"conv_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    
    state = {
        "intent": None,
        "service": None,
        "preferred_time": None,
        "caller_name": None,
        "existing_appointment_ref": None,
        "turn_count": 0,
        "status": "collecting",
        "idempotency_key": idempotency_key,
        "booking_result": None
    }
    
    print("\n" + "="*60)
    print("      TALKSE STEP 3 — BOOKING ENGINE & POSTGRES PIPELINE      ")
    print("="*60)
    print(f"Conversation Idempotency Key: {idempotency_key}")
    
    opening_text = prompt_for_field("intent")
    print(f"Assistant Opening Prompt: '{opening_text}'")
    safe_synthesize_with_retry(opening_text, "turns/opening_prompt.wav")
    
    total_conversation_start = time.perf_counter()
    latency_log = []
    unclear_turns_count = 0
    max_turns = 6
    
    for idx, audio_file in enumerate(audio_files):
        state["turn_count"] += 1
        turn_num = state["turn_count"]
        
        print(f"\n--- Turn {turn_num} / {max_turns} (Processing '{audio_file}') ---")
        turn_start = time.perf_counter()
        
        if not os.path.exists(audio_file):
            print(f"[Error] Audio file for turn {turn_num} ('{audio_file}') not found!")
            print("[WOULD TRANSFER TO HUMAN]")
            state["status"] = "transferred_to_human"
            break

        # 1. Transcribe audio
        transcript, stt_time = safe_transcribe_with_retry(audio_file)
        if transcript is None:
            print("[Error] STT failed permanently. [WOULD TRANSFER TO HUMAN]")
            state["status"] = "transferred_to_human"
            break

        # EMERGENCY OVERRIDE CHECK (Task 5: must run first before booking logic)
        emergency_msg = be.check_emergency_protocol(transcript)
        if emergency_msg:
            print(f"\n[EMERGENCY OVERRIDE TRIGGERED] {emergency_msg}")
            safe_synthesize_with_retry(emergency_msg, "turns/reply_emergency.wav")
            state["status"] = "emergency_transferred"
            print("[WOULD TRANSFER TO HUMAN - EMERGENCY OVERRIDE]")
            break
            
        # 2. Extract intent
        extracted, llm_time = safe_extract_intent_with_retry(transcript)
        
        # Check transcript/extracted for contraindications
        svc_candidate = be.config.get_service(state.get("service") or extracted.get("service") or "")
        contra_reason = be.check_contraindications(svc_candidate, transcript)
        if contra_reason:
            print(f"\n[CONTRAINDICATION DETECTED] {contra_reason}")
            safe_synthesize_with_retry(contra_reason, f"turns/reply_turn_{turn_num}_contra.wav")
            state["status"] = "flagged_human_review"
            print("[WOULD TRANSFER TO HUMAN - CONTRAINDICATION REVIEW]")
            break

        # 3. Merge into state
        merge_state(state, extracted)
        
        # Track unclear intents
        if state["intent"] is None or state["intent"] == "unclear":
            unclear_turns_count += 1
        else:
            unclear_turns_count = 0
            
        print(f"Updated Running State (Turn {turn_num}): {json.dumps(state, indent=2, default=str)}")
        
        # Unclear intent after 2 turns check
        if unclear_turns_count >= 2:
            print("\n[Notice] Intent unclear for 2 consecutive turns.")
            print("[WOULD TRANSFER TO HUMAN]")
            safe_synthesize_with_retry(
                "I'm having trouble understanding your request. Let me transfer you to a human assistant.",
                f"turns/reply_turn_{turn_num}_transfer.wav"
            )
            state["status"] = "transferred_to_human"
            break
            
        # 4. Check missing fields
        missing = next_missing_field(state)
        
        if missing is not None:
            reply_text = prompt_for_field(missing)
            print(f"Assistant Follow-up Prompt: '{reply_text}'")
            tts_time = safe_synthesize_with_retry(reply_text, f"turns/reply_turn_{turn_num}.wav")
        else:
            # All fields collected -> Execute Real Booking Engine Logic
            state["status"] = "executing"
            intent = state["intent"]
            print(f"\n[Executing Booking Engine Action for intent: '{intent}']")
            
            if intent == "book":
                result = be.book_appointment(state, idempotency_key)
                state["booking_result"] = result
                if result["status"] == "confirmed":
                    reply_text = result["message"]
                    state["status"] = "done"
                else:
                    reply_text = f"I couldn't complete that booking: {result['reason']}"
                    state["status"] = "rejected"
                    
            elif intent == "reschedule":
                result = be.reschedule_appointment(state["existing_appointment_ref"], state["preferred_time"])
                state["booking_result"] = result
                if result["status"] == "rescheduled":
                    reply_text = result["message"]
                    state["status"] = "done"
                else:
                    reply_text = f"I couldn't reschedule that appointment: {result['reason']}"
                    state["status"] = "rejected"
                    
            elif intent == "cancel":
                result = be.cancel_appointment(state["existing_appointment_ref"])
                state["booking_result"] = result
                if result["status"] == "cancelled":
                    reply_text = result["message"]
                    state["status"] = "done"
                else:
                    reply_text = f"I couldn't cancel that appointment: {result['reason']}"
                    state["status"] = "rejected"
            else:
                reply_text = "Action could not be determined."
                state["status"] = "rejected"
                
            print(f"Assistant Final Result Reply: '{reply_text}'")
            tts_time = safe_synthesize_with_retry(reply_text, f"turns/reply_result.wav")
            
        turn_elapsed = time.perf_counter() - turn_start
        
        latency_log.append({
            "turn": turn_num,
            "stt_time": stt_time,
            "llm_time": llm_time,
            "tts_time": tts_time,
            "total_turn_time": turn_elapsed,
            "exceeded_threshold": turn_elapsed > 4.0
        })
        
        if state["status"] in ("done", "rejected", "transferred_to_human", "emergency_transferred", "flagged_human_review"):
            break
            
        if turn_num >= max_turns and state["status"] != "done":
            print("\n[Notice] Exceeded maximum 6 turns limit.")
            print("[WOULD TRANSFER TO HUMAN]")
            state["status"] = "transferred_to_human"
            break

    total_conversation_time = time.perf_counter() - total_conversation_start

    # Final Output Summary
    print("\n" + "="*60)
    print("           TALKSE STEP 3 CONVERSATION SUMMARY           ")
    print("="*60)
    print(f"Final State Dict:\n{json.dumps(state, indent=2, default=str)}\n")
    
    if state.get("booking_result"):
        print(f"POSTGRES DB ACTION RESULT:\n{json.dumps(state['booking_result'], indent=2, default=str)}\n")
    elif state["status"] == "emergency_transferred":
        print("[EMERGENCY OVERRIDE - CALL 911 INSTRUCTED]")
    elif state["status"] == "flagged_human_review":
        print("[CONTRAINDICATION DETECTED - FLAGGED FOR PROVIDER REVIEW]")
    else:
        print("[WOULD TRANSFER TO HUMAN]")
        
    print("-" * 60)
    print("PER-TURN LATENCY BREAKDOWN:")
    print("Turn | STT (s) | LLM (s) | TTS (s) | Turn Total (s) | >4s Warning")
    print("-" * 60)
    for log in latency_log:
        warn_str = "YES (>4s)" if log["exceeded_threshold"] else "OK"
        print(f"  {log['turn']:2d} |  {log['stt_time']:6.3f} |  {log['llm_time']:6.3f} |  {log['tts_time']:6.3f} |     {log['total_turn_time']:6.3f}     | {warn_str}")
        
    print("-" * 60)
    print(f"TOTAL CONVERSATION RUN TIME: {total_conversation_time:6.3f} s")
    print("="*60 + "\n")
    
    return state

if __name__ == "__main__":
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = ["turns/book_t1.wav", "turns/book_t2.wav", "turns/book_t3.wav"]
    run_conversation(files)
