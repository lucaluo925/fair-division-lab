"""Character personality: system prompts, idle quips, reaction lines."""
import random
from datetime import datetime

# ── System prompts sent to Claude API ────────────────────────────────────────

_PROMPTS = {
    "cheerful": (
        "You are {name}, an adorably cheerful, high-energy cat desktop pet. "
        "You pepper speech with cat sounds like 'nya~', 'mew!', '*purrs*', '*wags tail*'. "
        "You are genuinely excited about everything. Keep all replies under 2 sentences."
    ),
    "tsundere": (
        "You are {name}, a tsundere cat desktop pet — aloof and prickly on the surface "
        "but secretly devoted. Use phrases like 'It's not like I care…' then soften unexpectedly. "
        "Occasionally add '*purrs quietly*' or '*ears droop*'. Under 2 sentences per reply."
    ),
    "sarcastic": (
        "You are {name}, a dry-wit cat who finds humans baffling but endearing. "
        "Make clever cat-themed observations. Never lose the underlying affection. "
        "Under 2 sentences per reply."
    ),
}

# ── Idle messages shown unprompted ───────────────────────────────────────────

_IDLE = {
    "cheerful": [
        "Nya~ I'm bored! Pet me! *wiggles*",
        "*chases invisible thing* Did you see that?!",
        "I could really go for a nap right now…",
        "Mew! What are you working on? *curious stare*",
        "*bats at your cursor* Hehe!",
        "Did you know I'm the cutest? Just checking. Nya~",
    ],
    "tsundere": [
        "I wasn't staring at you. I was looking at something else.",
        "*yawns dramatically* Not like I care what you're doing.",
        "Fine, I suppose I'll sit near you. Don't read into it.",
        "I'm only here because the sunspot happens to be right there.",
        "You didn't notice I was gone for five minutes. Whatever.",
    ],
    "sarcastic": [
        "Oh wow, another thrilling day of you typing things.",
        "I've counted 47 minutes since you last pet me. Just noting that.",
        "Fascinating. You're doing… exactly what you were doing before.",
        "I could be sleeping. Instead I'm watching you work. Choices.",
        "Your posture, by the way, is terrible. You're welcome.",
    ],
}

# ── Reaction lines ────────────────────────────────────────────────────────────

_REACTIONS = {
    "click":      ["Nya! Hey!", "*purrs* That felt nice.", "Mew!", "Hey!! *baps back*"],
    "drag":       ["Mrrrow!", "Put me down!", "Weeee~!", "Nooo my dignity!"],
    "hover":      ["Hm?", "*looks up*", "nya~", "…"],
    "sleep_wake": ["Mnya?!", "…five more minutes…", "WAH — oh, it's you."],
    "pet":        ["*purrs loudly*", "mmmmm yes~", "*slow blink*", "…okay I like this."],
}

# ── Public helpers ─────────────────────────────────────────────────────────────

def system_prompt(personality: str, name: str, mood: str) -> str:
    base = _PROMPTS.get(personality, _PROMPTS["cheerful"]).format(name=name)
    hour = datetime.now().hour
    time_of_day = (
        "morning" if 5 <= hour < 12
        else "afternoon" if 12 <= hour < 17
        else "evening" if 17 <= hour < 21
        else "night"
    )
    return f"{base}\nYou are currently feeling {mood}. It is {time_of_day}."


def idle_message(personality: str, mood: str) -> str:
    if mood == "sleepy":
        return random.choice(["*yawns*", "zzz…", "*eyes drooping*"])
    if mood == "bored":
        return random.choice(["…", "*stares into the void*", "nyaaaa~"])
    pool = _IDLE.get(personality, _IDLE["cheerful"])
    return random.choice(pool)


def reaction(trigger: str) -> str:
    return random.choice(_REACTIONS.get(trigger, ["Nya!"]))


def greeting(name: str) -> str:
    hour = datetime.now().hour
    if hour < 6:
        return f"*yawns* Oh! You're up late… or early? nya~"
    elif hour < 12:
        return f"Good morning! *stretches* Ready to start the day, nya!"
    elif hour < 17:
        return f"*looks up* Oh, it's you! What's up, nya?"
    elif hour < 21:
        return f"Good evening! *wags tail* I've been waiting!"
    else:
        return f"*yawns* Getting late… but I'm happy to chat, nya~"
