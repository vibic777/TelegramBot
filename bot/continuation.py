"""Resolve short follow-ups against the current user's retained dialogue."""
import re

from bot.personas import PERSONA_LABELS, find_named_persona


def continuation_request(text):
    text = re.sub(r"@[a-zA-Z0-9_]+", "", text).strip()
    phrase = (r"(?:хочу\s+ещ[её]|давай\s+ещ[её]|ещ[её](?:\s+(?:раз|одну?\s+фразу|фразу|пример|шутку|анекдот|стикер|картинку))?"
              r"|продолж(?:ай|и)|more|i\s+want\s+more|one\s+more|another\s+one|continue|go\s+on)")
    if re.fullmatch(phrase + r"[\s.!?]*", text, re.IGNORECASE):
        return True, None
    match = re.fullmatch(r"(?:(.*?)\s*[:,]\s*|(.*?)\s+)?(" + phrase + r")[\s.!?]*", text, re.IGNORECASE)
    if not match:
        return False, None
    prefix = (match[1] or match[2] or "").strip()
    found = find_named_persona(prefix) if prefix else None
    return (True, found[0] if found else None) if not prefix or found else (False, None)


def continuation_source(events, persona, limit):
    if not limit:
        return None
    # Every retained dialogue event counts towards the window, including stickers.
    relevant = [event for event in events if event.get("persona") == persona][-limit:]
    assistant_index = next((i for i in range(len(relevant) - 1, -1, -1)
                            if relevant[i].get("role") == "assistant"), None)
    if assistant_index is None:
        return None
    request = next((event for event in reversed(relevant[:assistant_index])
                    if event.get("role") == "user" and (event.get("continuation_request")
                    or not continuation_request(str(event.get("text", "")))[0])), None)
    if not request:
        return None
    return str(request.get("continuation_request") or request.get("text", "")), str(relevant[assistant_index].get("text", ""))


def last_speaker(events):
    return next((event["persona"] for event in reversed(events)
                 if event.get("role") == "assistant" and event.get("persona") in PERSONA_LABELS), None)
