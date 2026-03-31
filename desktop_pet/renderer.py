"""
Cat character renderer.

All drawing functions accept (canvas, cx, cy, ...) where:
  cx  — horizontal center of the cat in canvas pixels
  cy  — vertical position of the cat's feet in canvas pixels

The cat grows *upward* from cy.  Total height ≈ 185 px at scale 1.
"""
import math

# ── Colour palette ────────────────────────────────────────────────────────────

C = {
    "body":       "#F5A623",   # warm orange
    "belly":      "#FFF5E0",   # cream
    "inner_ear":  "#FFB6C1",   # pink
    "eye_iris":   "#2ECC71",   # green
    "eye_pupil":  "#1A252F",   # very dark navy
    "eye_white":  "#FFFFFF",
    "nose":       "#FF8FAB",   # pink
    "outline":    "#8B6240",   # warm brown
    "whisker":    "#A07850",
    "tail_tip":   "#FFF5E0",   # cream tip
    "paw":        "#FFF0D0",
    "blush":      "#FFB7C5",
    "zzz":        "#5B9BD5",
    "heart":      "#FF6B9D",
    "star":       "#FFD700",
}

TAG = "cat"  # all canvas items share this tag so we can delete them in one call


# ── Public API ────────────────────────────────────────────────────────────────

def clear(canvas) -> None:
    canvas.delete(TAG)


def draw(
    canvas,
    cx: float,
    cy: float,
    *,
    state: str = "idle",
    frame: int = 0,
    mood: str = "happy",
    facing: str = "right",
    speech: str = "",
) -> None:
    """Redraw the entire cat for one animation frame."""
    clear(canvas)

    t = frame * 0.08  # continuous time value

    # ── Derive per-state animation parameters ────────────────────────────────
    body_dy     = 0.0   # vertical breathing offset
    tail_swing  = 0.0   # degrees of tail-swing oscillation
    leg_phase   = 0.0   # walk-cycle phase (radians)
    eye_state   = "open"
    show_zzz    = False
    show_hearts = False
    show_stars  = False

    if state == "idle":
        body_dy    = math.sin(t) * 2.0
        tail_swing = math.sin(t * 0.6) * 15

    elif state == "walk":
        body_dy    = abs(math.sin(t * 2.5)) * 2.5
        tail_swing = math.sin(t * 2.0) * 25
        leg_phase  = t * 2.5

    elif state == "sleep":
        body_dy    = math.sin(t * 0.35) * 1.0   # slow, gentle breathing
        tail_swing = math.sin(t * 0.3) * 8
        eye_state  = "closed"
        show_zzz   = True

    elif state == "jump":
        tail_swing = 35
        body_dy    = math.sin(t * 3) * 4

    elif state == "react":
        body_dy    = -abs(math.sin(t * 4)) * 8  # bouncy
        tail_swing = math.sin(t * 4) * 40
        eye_state  = "wide"
        show_hearts = (mood in ("happy", "excited"))
        show_stars  = not show_hearts

    elif state == "pet":
        body_dy    = math.sin(t * 2) * 3
        tail_swing = math.sin(t * 1.5) * 30
        eye_state  = "half"
        show_hearts = True

    # Apply breathing offset
    cy = cy + body_dy

    # ── Draw order: back → front ─────────────────────────────────────────────
    _tail(canvas, cx, cy, facing, tail_swing)
    _back_legs(canvas, cx, cy, facing, leg_phase, state)
    _body(canvas, cx, cy)
    _front_legs(canvas, cx, cy, facing, leg_phase, state)
    _head(canvas, cx, cy, facing, eye_state, mood)
    _ears(canvas, cx, cy, facing)
    _whiskers(canvas, cx, cy, facing)

    # ── Overlays ─────────────────────────────────────────────────────────────
    if show_zzz:
        _zzz(canvas, cx, cy, frame)
    if show_hearts:
        _hearts(canvas, cx, cy, frame)
    if show_stars:
        _stars(canvas, cx, cy, frame)
    if speech:
        _speech_bubble(canvas, cx, cy, speech)


# ── Helper: mirror x around cx based on facing direction ─────────────────────

def _fx(cx: float, dx: float, facing: str) -> float:
    """Return mirrored x if facing left."""
    return cx + (dx if facing == "right" else -dx)


# ── Drawing sub-routines ──────────────────────────────────────────────────────

def _tail(canvas, cx, cy, facing, swing_deg):
    """Smooth three-point tail that curls upward."""
    # Tail root: at the back/side of the body
    rx = _fx(cx, -22, facing)
    ry = cy - 58

    swing = math.radians(swing_deg)
    # Base direction: left-and-up for right-facing cat
    if facing == "right":
        base = math.radians(130)
    else:
        base = math.radians(50)

    # Two segments
    a1 = base + swing * 0.4
    a2 = base - math.radians(35) + swing

    x1 = rx + math.cos(a1) * 32
    y1 = ry - math.sin(a1) * 32
    x2 = x1 + math.cos(a2) * 26
    y2 = y1 - math.sin(a2) * 26

    canvas.create_line(
        rx, ry, x1, y1, x2, y2,
        fill=C["body"], width=9, smooth=True, capstyle="round",
        tags=TAG,
    )
    # Cream tip
    canvas.create_oval(
        x2 - 7, y2 - 7, x2 + 7, y2 + 7,
        fill=C["tail_tip"], outline=C["outline"], width=1,
        tags=TAG,
    )


def _body(canvas, cx, cy):
    """Torso ellipse + cream belly."""
    bcy = cy - 65
    bw, bh = 34, 27

    canvas.create_oval(
        cx - bw, bcy - bh, cx + bw, bcy + bh,
        fill=C["body"], outline=C["outline"], width=1.5,
        tags=TAG,
    )
    # Belly patch
    canvas.create_oval(
        cx - bw * 0.55, bcy - bh * 0.55,
        cx + bw * 0.55, bcy + bh * 0.88,
        fill=C["belly"], outline="",
        tags=TAG,
    )


def _back_legs(canvas, cx, cy, facing, leg_phase, state):
    """Rear legs (drawn behind body)."""
    for dx, phase_offset in [(14, 0), (22, math.pi)]:
        lx = _fx(cx, dx, facing)
        leg_dy = math.sin(leg_phase + phase_offset) * 5 if state == "walk" else 0

        # Thigh blob
        canvas.create_oval(
            lx - 9, cy - 42 + leg_dy,
            lx + 9, cy - 16 + leg_dy,
            fill=C["body"], outline=C["outline"], width=1,
            tags=TAG,
        )
        # Paw
        canvas.create_oval(
            lx - 8, cy - 13 + leg_dy,
            lx + 8, cy + 1 + leg_dy,
            fill=C["paw"], outline=C["outline"], width=1,
            tags=TAG,
        )


def _front_legs(canvas, cx, cy, facing, leg_phase, state):
    """Front legs (drawn in front of body)."""
    for sign, phase_offset in [(-1, 0), (1, math.pi)]:
        lx = _fx(cx, sign * 17, facing)
        if state == "walk":
            # The leg on the same side as facing direction leads the stride
            if (sign == 1 and facing == "right") or (sign == -1 and facing == "left"):
                leg_dy = math.sin(leg_phase) * 6
            else:
                leg_dy = math.sin(leg_phase + math.pi) * 6
        else:
            leg_dy = 0

        canvas.create_oval(
            lx - 7, cy - 40 + leg_dy,
            lx + 7, cy - 13 + leg_dy,
            fill=C["body"], outline=C["outline"], width=1.5,
            tags=TAG,
        )
        canvas.create_oval(
            lx - 9, cy - 14 + leg_dy,
            lx + 9, cy + 1 + leg_dy,
            fill=C["paw"], outline=C["outline"], width=1.5,
            tags=TAG,
        )


def _head(canvas, cx, cy, facing, eye_state, mood):
    """Head circle + face (eyes, nose, mouth, blush)."""
    hr   = 28
    hcy  = cy - 112  # head vertical centre

    # Head circle
    canvas.create_oval(
        cx - hr, hcy - hr, cx + hr, hcy + hr,
        fill=C["body"], outline=C["outline"], width=1.5,
        tags=TAG,
    )

    # Cheek puffs
    for sign in (-1, 1):
        cpx = _fx(cx, sign * 23, facing)
        canvas.create_oval(
            cpx - 11, hcy + 3, cpx + 11, hcy + 18,
            fill=C["body"], outline="",
            tags=TAG,
        )

    # Eyes
    eye_dx = 11
    for sign in (-1, 1):
        ex = _fx(cx, sign * eye_dx, facing)
        _eye(canvas, ex, hcy - 3, eye_state, mood)

    # Nose
    ny = hcy + 11
    canvas.create_oval(
        cx - 5, ny - 3, cx + 5, ny + 4,
        fill=C["nose"], outline=C["outline"], width=1,
        tags=TAG,
    )

    # Mouth
    my = ny + 4
    if mood in ("happy", "excited"):
        # W-shaped happy mouth
        canvas.create_line(
            cx - 8, my + 1,
            cx - 4, my + 6,
            cx,     my + 2,
            cx + 4, my + 6,
            cx + 8, my + 1,
            fill=C["outline"], width=1.5, smooth=True,
            tags=TAG,
        )
    elif mood in ("bored", "sleepy"):
        canvas.create_line(
            cx - 6, my + 4, cx + 6, my + 4,
            fill=C["outline"], width=1.5,
            tags=TAG,
        )
    elif mood == "annoyed":
        canvas.create_arc(
            cx - 7, my, cx + 7, my + 10,
            start=0, extent=180, style="arc",
            outline=C["outline"], width=1.5,
            tags=TAG,
        )
    else:
        # Gentle smile
        canvas.create_arc(
            cx - 6, my, cx + 6, my + 8,
            start=180, extent=180, style="arc",
            outline=C["outline"], width=1.5,
            tags=TAG,
        )

    # Blush for happy/excited
    if mood in ("happy", "excited"):
        for sign in (-1, 1):
            bx = _fx(cx, sign * 20, facing)
            canvas.create_oval(
                bx - 9, hcy + 7, bx + 9, hcy + 13,
                fill=C["blush"], outline="",
                tags=TAG,
            )


def _eye(canvas, ex, ey, eye_state, mood):
    """Draw one eye at (ex, ey)."""
    er = 10 if eye_state == "wide" else 8

    if eye_state == "closed":
        # Arc line — eye squinted shut
        canvas.create_arc(
            ex - er, ey - 4, ex + er, ey + 4,
            start=0, extent=180, style="arc",
            outline=C["outline"], width=2,
            tags=TAG,
        )
        return

    if eye_state == "half":
        # Draw full eye then cover top half with body-colour rectangle
        canvas.create_oval(
            ex - er, ey - er, ex + er, ey + er,
            fill=C["eye_iris"], outline=C["outline"], width=1.5,
            tags=TAG,
        )
        canvas.create_rectangle(
            ex - er - 1, ey - er - 1, ex + er + 1, ey,
            fill=C["body"], outline="",
            tags=TAG,
        )
        canvas.create_line(
            ex - er, ey, ex + er, ey,
            fill=C["outline"], width=2,
            tags=TAG,
        )
        return

    # Normal / wide eye
    canvas.create_oval(
        ex - er, ey - er, ex + er, ey + er,
        fill=C["eye_white"], outline=C["outline"], width=1.5,
        tags=TAG,
    )
    ir = er * 0.65
    canvas.create_oval(
        ex - ir, ey - ir, ex + ir, ey + ir,
        fill=C["eye_iris"], outline="",
        tags=TAG,
    )
    # Pupil: slit for annoyed, round otherwise
    if mood == "annoyed":
        canvas.create_oval(
            ex - 2, ey - ir * 0.8,
            ex + 2, ey + ir * 0.8,
            fill=C["eye_pupil"], outline="",
            tags=TAG,
        )
    else:
        pr = ir * 0.55
        canvas.create_oval(
            ex - pr, ey - pr, ex + pr, ey + pr,
            fill=C["eye_pupil"], outline="",
            tags=TAG,
        )
    # Specular highlight
    canvas.create_oval(
        ex - er * 0.28, ey - er * 0.48,
        ex + er * 0.06, ey - er * 0.08,
        fill="white", outline="",
        tags=TAG,
    )


def _ears(canvas, cx, cy, facing):
    """Triangular ears with pink inner fill."""
    hcy = cy - 112

    for sign in (-1, 1):
        # Outer ear polygon
        pts = [
            _fx(cx, sign * 13, facing), hcy - 11,
            _fx(cx, sign * 28, facing), hcy - 42,
            _fx(cx, sign * 24, facing), hcy - 5,
        ]
        canvas.create_polygon(pts, fill=C["body"], outline=C["outline"], width=1.5, tags=TAG)

        # Inner ear
        ipts = [
            _fx(cx, sign * 15, facing), hcy - 13,
            _fx(cx, sign * 26, facing), hcy - 37,
            _fx(cx, sign * 22, facing), hcy - 9,
        ]
        canvas.create_polygon(ipts, fill=C["inner_ear"], outline="", tags=TAG)


def _whiskers(canvas, cx, cy, facing):
    """Three whiskers on each side of the nose."""
    hcy = cy - 112
    ny  = hcy + 11

    for side in (-1, 1):
        # Root position: just beside nose
        rx = _fx(cx, side * 5, facing)

        # End position: extends outward
        ex_base = _fx(cx, side * 33, facing)

        # Three whiskers at slightly different y angles
        for i, (dy_root, dy_end) in enumerate([(-4, -7), (0, 0), (4, 7)]):
            canvas.create_line(
                rx, ny + dy_root,
                ex_base, ny + dy_end,
                fill=C["whisker"], width=1,
                tags=TAG,
            )


def _zzz(canvas, cx, cy, frame):
    """Floating Zs for sleeping state."""
    hcy = cy - 112
    for i, (dx, dy, size) in enumerate([(18, -22, 9), (30, -38, 12), (44, -56, 16)]):
        # Stagger so they appear sequentially
        phase = (frame * 2 + i * 18) % 54
        if phase < 36:
            canvas.create_text(
                cx + dx, hcy + dy,
                text="Z", font=("Arial", size, "bold"),
                fill=C["zzz"],
                tags=TAG,
            )


def _hearts(canvas, cx, cy, frame):
    """Floating hearts for happy/pet state."""
    hcy = cy - 112
    for i in range(2):
        t = (frame * 3 + i * 28) % 56
        hy = hcy - 28 - t * 0.45
        hx = cx + math.sin(t * 0.18 + i) * 9 + (i - 0.5) * 14
        canvas.create_text(
            hx, hy, text="♥",
            font=("Arial", 11 + i * 2),
            fill=C["heart"],
            tags=TAG,
        )


def _stars(canvas, cx, cy, frame):
    """Impact stars for react/surprise state."""
    hcy = cy - 112
    for i, (dx, dy) in enumerate([(20, -28), (-17, -24), (4, -42)]):
        t = (frame + i * 4) % 18
        if t < 14:
            canvas.create_text(
                cx + dx, hcy + dy, text="✦",
                font=("Arial", 9 + i * 2),
                fill=C["star"],
                tags=TAG,
            )


def _speech_bubble(canvas, cx, cy, text: str):
    """Rounded speech bubble above the cat's head."""
    hcy = cy - 112
    # Measure approximate text size
    chars  = max(len(line) for line in text.split("\n")) if text else 1
    width  = max(80, min(chars * 7 + 20, 200))
    height = 32 + text.count("\n") * 16

    bx1 = cx - width // 2
    by1 = hcy - 50 - height
    bx2 = cx + width // 2
    by2 = hcy - 50

    # Bubble background
    canvas.create_rectangle(
        bx1, by1, bx2, by2,
        fill="#FFFFF0", outline=C["outline"], width=1.5,
        tags=TAG,
    )
    # Tail triangle pointing down toward head
    tip_y = hcy - 46
    canvas.create_polygon(
        cx - 6, by2,
        cx + 6, by2,
        cx,     tip_y,
        fill="#FFFFF0", outline=C["outline"], width=1,
        tags=TAG,
    )
    # Text
    canvas.create_text(
        cx, (by1 + by2) // 2,
        text=text, font=("Arial", 9),
        fill="#333333", width=width - 12,
        tags=TAG,
    )
