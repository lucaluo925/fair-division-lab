"""Entry point for the Desktop Pet application."""
import sys
import os


def main() -> None:
    if sys.version_info < (3, 8):
        sys.exit("Error: Python 3.8 or newer is required.")

    # Ensure the package root is importable when running directly
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)

    from desktop_pet.pet_window import PetWindow

    print("Starting Desktop Pet…")
    print("Right-click the pet for options.  Double-click to open chat.")
    print("Set ANTHROPIC_API_KEY (or add it to ~/.desktop_pet_config.json) for AI chat.\n")

    PetWindow().run()


if __name__ == "__main__":
    main()
