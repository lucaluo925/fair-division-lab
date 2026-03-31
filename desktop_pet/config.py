"""Configuration management — loads/saves settings from ~/.desktop_pet_config.json."""
import os
import json

CONFIG_FILE = os.path.expanduser("~/.desktop_pet_config.json")

DEFAULTS: dict = {
    # API key — falls back to env var if not set here
    "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
    # Character
    "character_name": "Mochi",
    "personality": "cheerful",   # cheerful | tsundere | sarcastic
    # Behaviour
    "walk_speed": 2,             # pixels per frame
    "idle_timeout": 20,          # seconds before wandering
    "sleep_timeout": 120,        # seconds of inactivity before sleeping
    # Visual
    "scale": 1.0,
}


def load() -> dict:
    cfg = DEFAULTS.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as fh:
                cfg.update(json.load(fh))
        except Exception:
            pass  # silently use defaults on corrupt file
    return cfg


def save(cfg: dict) -> None:
    with open(CONFIG_FILE, "w") as fh:
        json.dump(cfg, fh, indent=2)
