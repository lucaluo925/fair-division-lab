"""
AI response generation via Anthropic Claude API.

Falls back to built-in responses when no API key is configured.
"""
import random
from . import personality as pers


def get_response(
    user_msg: str,
    cfg: dict,
    mood: str,
    history: list[dict],
) -> str:
    """
    Return the pet's reply to `user_msg`.

    history: list of {"role": "user"|"assistant", "content": str}
    """
    api_key = cfg.get("api_key", "")
    if api_key:
        return _api_response(user_msg, cfg, mood, history, api_key)
    return _local_response(user_msg, cfg, mood)


# ── Claude API path ───────────────────────────────────────────────────────────

def _api_response(
    user_msg: str,
    cfg: dict,
    mood: str,
    history: list[dict],
    api_key: str,
) -> str:
    try:
        import anthropic
    except ImportError:
        return "(Install 'anthropic' package for AI responses — pip install anthropic)"

    client = anthropic.Anthropic(api_key=api_key)
    system = pers.system_prompt(
        cfg.get("personality", "cheerful"),
        cfg.get("character_name", "Mochi"),
        mood,
    )

    # Keep the last 8 turns for context
    messages = [{"role": m["role"], "content": m["content"]} for m in history[-8:]]
    messages.append({"role": "user", "content": user_msg})

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",  # fast + cheap model for chat
        max_tokens=120,
        system=system,
        messages=messages,
    )
    return resp.content[0].text.strip()


# ── Built-in fallback responses ───────────────────────────────────────────────

def _local_response(user_msg: str, cfg: dict, mood: str) -> str:
    ptype = cfg.get("personality", "cheerful")
    m = user_msg.lower()

    if any(w in m for w in ("hello", "hi ", "hey", "hiya", "howdy")):
        return {
            "cheerful":  "Nya~! Hi hi! *wiggles excitedly*",
            "tsundere":  "Oh, it's you.  …Hi.  *looks away*",
            "sarcastic": "Oh look, you acknowledged my existence.",
        }.get(ptype, "Nya~!")

    if any(w in m for w in ("how are", "feeling", "how're")):
        return {
            "happy":   "*purrs* Wonderfully happy!",
            "bored":   "…bored.  Very bored.",
            "annoyed": "*tail flick* Fine, I guess.",
            "sleepy":  "*yawns* Sleeeepy…",
        }.get(mood, "Doing great, nya~!")

    if any(w in m for w in ("pet", "pat", "stroke", "scratch", "cuddle")):
        return "*purrs loudly* …okay I like this.  Just a little."

    if any(w in m for w in ("food", "eat", "hungry", "snack", "treat")):
        return "FOOD?! *perks up instantly* Did someone say food?! Nya nya nya!"

    if any(w in m for w in ("sleep", "tired", "rest", "nap")):
        return "*yawns dramatically* Now that you mention it… *curls up*"

    if any(w in m for w in ("good", "nice", "cute", "love", "adorable")):
        return random.choice(["*happy chirp* Ehehe~", "*slow blink* You're not so bad yourself.", "♥"])

    return random.choice([
        "Mew~ *listens attentively*",
        "*tilts head* Nya?",
        "Interesting!  *paw at chin*",
        "*blinks slowly*",
        f"(Tip: set ANTHROPIC_API_KEY for real AI chat!  Nya~)",
    ])
