"""
Main pet window.

A transparent, always-on-top, decoration-less tkinter window that
hosts the canvas where the cat is rendered.  The window position is
updated every frame to follow the behavior engine's logical (x, y).
"""
import platform
import tkinter as tk

from . import renderer, behavior, personality as pers, config as cfg
from .chat_window import ChatWindow

# Canvas dimensions — must be large enough to contain the cat + effects
CANVAS_W = 170
CANVAS_H = 230

# Where the cat's feet sit inside the canvas
CAT_CX = CANVAS_W // 2
CAT_CY = CANVAS_H - 20

# Frames per second target
FPS    = 30
TICK   = 1000 // FPS   # milliseconds per frame

# How often to show an unprompted idle message (seconds)
IDLE_MSG_INTERVAL = 35


class PetWindow:
    def __init__(self):
        self._config = cfg.load()

        self.root = tk.Tk()
        self._setup_window()
        self._setup_canvas()
        self._setup_menu()

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        self.engine = behavior.BehaviorEngine(sw, sh, self._config)

        # Start near the bottom-centre of the screen
        self.engine.x = sw // 2
        self.engine.y = sh - 80

        self._chat_win: ChatWindow | None = None
        self._idle_msg_ticks = 0

        self._apply_position()
        self.root.after(TICK, self._loop)

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        root = self.root
        root.overrideredirect(True)       # no title bar / border
        root.wm_attributes("-topmost", True)
        root.geometry(f"{CANVAS_W}x{CANVAS_H}")

        system = platform.system()
        if system == "Darwin":
            try:
                root.wm_attributes("-transparent", True)
                root.configure(bg="systemTransparent")
                self._transparent_bg = "systemTransparent"
            except tk.TclError:
                # Older Tk on macOS — fall back to near-white
                root.configure(bg="white")
                root.wm_attributes("-alpha", 0.0)  # we rely on canvas bg
                self._transparent_bg = "white"
        elif system == "Windows":
            # Windows supports per-pixel colour keying
            root.configure(bg="#010101")
            root.wm_attributes("-transparentcolor", "#010101")
            self._transparent_bg = "#010101"
        else:
            # Linux / X11 — use alpha blending (no true transparency)
            root.configure(bg="#010101")
            root.wm_attributes("-alpha", 0.92)
            self._transparent_bg = "#010101"

    def _setup_canvas(self) -> None:
        self.canvas = tk.Canvas(
            self.root,
            width=CANVAS_W, height=CANVAS_H,
            bg=self._transparent_bg,
            highlightthickness=0, bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # ── Mouse bindings ────────────────────────────────────────────────────
        self.canvas.bind("<ButtonPress-1>",   self._mb1_press)
        self.canvas.bind("<B1-Motion>",        self._mb1_motion)
        self.canvas.bind("<ButtonRelease-1>",  self._mb1_release)
        self.canvas.bind("<Double-Button-1>",  self._double_click)
        self.canvas.bind("<Button-2>",         self._right_click)   # macOS middle
        self.canvas.bind("<Button-3>",         self._right_click)   # right click

        self._press_root_x = 0
        self._press_root_y = 0
        self._press_win_x  = 0
        self._press_win_y  = 0
        self._dragging = False

    def _setup_menu(self) -> None:
        name = self._config["character_name"]
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label=f"💬  Chat with {name}", command=self._open_chat)
        m.add_separator()
        m.add_command(label="🐾  Pet",               command=self._pet)
        m.add_command(label="⏰  Wake up",            command=self._wake)
        m.add_separator()
        m.add_command(label="❌  Exit",               command=self._exit)
        self._menu = m

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        self.engine.update()
        self._render()
        self._apply_position()
        self._maybe_idle_message()
        self.root.after(TICK, self._loop)

    def _render(self) -> None:
        renderer.draw(
            self.canvas, CAT_CX, CAT_CY,
            state=self.engine.state,
            frame=self.engine.frame,
            mood=self.engine.mood,
            facing=self.engine.facing,
            speech=self.engine.speech,
        )

    def _apply_position(self) -> None:
        """Move the tkinter window so the cat sits at engine.(x, y)."""
        win_x = int(self.engine.x - CANVAS_W / 2)
        win_y = int(self.engine.y - CAT_CY)

        # Clamp to screen bounds
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        win_x = max(0, min(win_x, sw - CANVAS_W))
        win_y = max(0, min(win_y, sh - CANVAS_H))

        self.root.geometry(f"{CANVAS_W}x{CANVAS_H}+{win_x}+{win_y}")

    def _maybe_idle_message(self) -> None:
        """Show an unprompted speech bubble now and then."""
        self._idle_msg_ticks += 1
        if self._idle_msg_ticks >= FPS * IDLE_MSG_INTERVAL:
            self._idle_msg_ticks = 0
            if self.engine.state == "idle":
                msg = pers.idle_message(
                    self._config.get("personality", "cheerful"),
                    self.engine.mood,
                )
                self.engine.say(msg, duration=4.0)

    # ── Mouse handlers ────────────────────────────────────────────────────────

    def _mb1_press(self, e: tk.Event) -> None:
        self._press_root_x = e.x_root
        self._press_root_y = e.y_root
        self._press_win_x  = self.root.winfo_x()
        self._press_win_y  = self.root.winfo_y()
        self._dragging = False
        self.engine.on_click()

    def _mb1_motion(self, e: tk.Event) -> None:
        dx = e.x_root - self._press_root_x
        dy = e.y_root - self._press_root_y
        if abs(dx) > 4 or abs(dy) > 4:
            if not self._dragging:
                self._dragging = True
                # Hand off drag start to engine using current screen coords
                pet_sx = self._press_win_x + CANVAS_W / 2
                pet_sy = self._press_win_y + CAT_CY
                self.engine.on_drag_start(pet_sx, pet_sy)
            # Update via raw window movement for responsiveness
            new_x = self._press_win_x + dx
            new_y = self._press_win_y + dy
            self.root.geometry(f"+{new_x}+{new_y}")
            self.engine.x = new_x + CANVAS_W / 2
            self.engine.y = new_y + CAT_CY

    def _mb1_release(self, _e: tk.Event) -> None:
        if self._dragging:
            self.engine.on_drag_end()
        self._dragging = False

    def _double_click(self, _e: tk.Event) -> None:
        self._open_chat()

    def _right_click(self, e: tk.Event) -> None:
        try:
            self._menu.tk_popup(e.x_root, e.y_root)
        finally:
            self._menu.grab_release()

    # ── Menu actions ──────────────────────────────────────────────────────────

    def _open_chat(self) -> None:
        if self._chat_win is None or not self._chat_win.is_open:
            self._chat_win = ChatWindow(self.root, self._config, self.engine)

    def _pet(self) -> None:
        self.engine.on_pet()
        self.engine.say(pers.reaction("pet"), duration=3.0)

    def _wake(self) -> None:
        self.engine.on_wake()
        self.engine.say(pers.reaction("sleep_wake"), duration=3.0)

    def _exit(self) -> None:
        self.root.quit()

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self) -> None:
        self.root.mainloop()
