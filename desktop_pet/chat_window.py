"""
Chat window — a Toplevel dialog for talking to the pet.

Opens on double-click or via the right-click context menu.
AI responses are fetched in a background thread so the UI stays responsive.
"""
import threading
import tkinter as tk
from tkinter import scrolledtext

from . import ai_chat, personality as pers


class ChatWindow:
    def __init__(self, parent: tk.Misc, cfg: dict, engine):
        self.cfg    = cfg
        self.engine = engine
        self.is_open = True
        self._history: list[dict] = []

        self.win = tk.Toplevel(parent)
        self.win.title(f"Chat with {cfg['character_name']}")
        self.win.geometry("340x440")
        self.win.resizable(True, True)
        self.win.minsize(280, 360)
        self.win.wm_attributes("-topmost", True)
        self.win.protocol("WM_DELETE_WINDOW", self._close)

        self._build_ui()

        # Greet the user
        greeting = pers.greeting(cfg["character_name"])
        self._append(cfg["character_name"], greeting, tag="pet")

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        accent = "#FFB347"

        # Header bar
        hdr = tk.Frame(self.win, bg=accent, pady=7)
        hdr.pack(fill="x")
        tk.Label(
            hdr, text=f"🐱  {self.cfg['character_name']}",
            bg=accent, fg="white", font=("Arial", 13, "bold"),
        ).pack()

        # Chat display
        self.display = scrolledtext.ScrolledText(
            self.win, wrap="word", state="disabled",
            bg="#FFF9F0", font=("Arial", 11),
            relief="flat", padx=8, pady=6,
        )
        self.display.pack(fill="both", expand=True, padx=6, pady=6)

        # Text styling tags
        self.display.tag_config("pet",      foreground="#CC6600", font=("Arial", 11, "bold"))
        self.display.tag_config("user",     foreground="#336699", font=("Arial", 11, "bold"))
        self.display.tag_config("body",     foreground="#333333", font=("Arial", 11))
        self.display.tag_config("thinking", foreground="#AAAAAA", font=("Arial", 10, "italic"))

        # Input row
        row = tk.Frame(self.win, bg="#F0F0F0", pady=4)
        row.pack(fill="x", padx=6, pady=(0, 6))

        self._input_var = tk.StringVar()
        self._entry = tk.Entry(
            row, textvariable=self._input_var,
            font=("Arial", 11), relief="solid", bd=1,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._entry.bind("<Return>", self._send)
        self._entry.focus_set()

        self._send_btn = tk.Button(
            row, text="Send", command=self._send,
            bg=accent, fg="white",
            font=("Arial", 11, "bold"), relief="flat", padx=12,
        )
        self._send_btn.pack(side="right")

    # ── Send / receive ────────────────────────────────────────────────────────

    def _send(self, _event=None) -> None:
        text = self._input_var.get().strip()
        if not text:
            return

        self._input_var.set("")
        self._send_btn.config(state="disabled")
        self._append("You", text, tag="user")
        self._history.append({"role": "user", "content": text})

        self._show_thinking()
        self.engine.on_click()  # pet reacts while thinking

        def worker():
            try:
                reply = ai_chat.get_response(
                    text, self.cfg, self.engine.mood,
                    list(self._history),
                )
            except Exception as exc:
                reply = f"*connection hiccup* nya… ({exc!s:.40})"
            if self.is_open:
                self.win.after(0, lambda: self._receive(reply))

        threading.Thread(target=worker, daemon=True).start()

    def _receive(self, text: str) -> None:
        self._hide_thinking()
        self._append(self.cfg["character_name"], text, tag="pet")
        self._history.append({"role": "assistant", "content": text})
        self._send_btn.config(state="normal")
        self._entry.focus_set()
        self.engine.on_pet()

    # ── Display helpers ───────────────────────────────────────────────────────

    def _append(self, speaker: str, text: str, *, tag: str) -> None:
        self.display.config(state="normal")
        self.display.insert("end", f"{speaker}: ", tag)
        self.display.insert("end", f"{text}\n\n", "body")
        self.display.see("end")
        self.display.config(state="disabled")

    def _show_thinking(self) -> None:
        self.display.config(state="normal")
        self.display.insert("end", "…\n", "thinking")
        self.display.see("end")
        self.display.config(state="disabled")
        self._thinking_mark = self.display.index("end-2l")

    def _hide_thinking(self) -> None:
        self.display.config(state="normal")
        try:
            self.display.delete(self._thinking_mark, "end")
        except Exception:
            pass
        self.display.config(state="disabled")

    def _close(self) -> None:
        self.is_open = False
        self.win.destroy()
