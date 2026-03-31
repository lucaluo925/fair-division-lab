#!/usr/bin/env python3
"""
Desktop Pet — launcher script.

Usage:
    python run_pet.py

Optional: set your Anthropic API key for AI-powered chat:
    export ANTHROPIC_API_KEY=sk-ant-...
    python run_pet.py

Or add it to ~/.desktop_pet_config.json:
    {"api_key": "sk-ant-..."}
"""
import sys
import os
import subprocess


def _ensure_deps() -> None:
    """Install 'anthropic' if not already present (optional dependency)."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        print("Optional package 'anthropic' not found.")
        answer = input("Install it now for AI chat? [y/N] ").strip().lower()
        if answer == "y":
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "anthropic"],
                stdout=subprocess.DEVNULL,
            )
            print("Installed!  AI chat is now enabled.\n")
        else:
            print("Skipping.  The pet will use built-in responses.\n")


def main() -> None:
    # Change to the script directory so relative imports work
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    _ensure_deps()

    from desktop_pet.main import main as pet_main
    pet_main()


if __name__ == "__main__":
    main()
