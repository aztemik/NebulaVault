"""
pantalla_principal.py
══════════════════════════════════════════════════════════════════════════════
NébulaVault — Pantalla Principal (stub de bienvenida post-login)
Muestra al usuario que ha accedido correctamente a la aplicación.
══════════════════════════════════════════════════════════════════════════════
"""

import math
import time
import tkinter as tk


# ── Paleta NébulaVault ────────────────────────────────────────────────────────
BG_VOID       = "#07090f"
BG_PANEL      = "#0d1117"
BG_CARD       = "#111827"
BORDER_DARK   = "#1e2939"
ACCENT_CYAN   = "#38bdf8"
ACCENT_PURPLE = "#818cf8"
ACCENT_GOLD   = "#fbbf24"
SUCCESS       = "#34d399"
TEXT_MAIN     = "#e2e8f0"
TEXT_MUTED    = "#64748b"
TEXT_FAINT    = "#334155"

CYAN_20 = "#0f2535"
CYAN_33 = "#153650"
CYAN_53 = "#1e5478"


# ── Helpers de dibujo ─────────────────────────────────────────────────────────

def _hex_grid(canvas: tk.Canvas, w: int, h: int,
              spacing: int = 52, color: str = "#0d1520") -> None:
    r  = spacing / 2
    dx = spacing * 1.5
    dy = spacing * math.sqrt(3) / 2
    col, x = 0, -spacing
    while x < w + spacing:
        y = (dy if col % 2 else 0) - spacing
        while y < h + spacing:
            pts = []
            for i in range(6):
                a = math.radians(60 * i - 30)
                pts += [x + r * math.cos(a), y + r * math.sin(a)]
            canvas.create_polygon(pts, outline=color, fill="", width=1)
            y += dy * 2
        x += dx
        col += 1


def _corner(canvas: tk.Canvas, cx: int, cy: int,
            size: int, color: str, pos: str) -> None:
    s = size // 2
    coords = {
        "tl": (cx, cy+s, cx, cy, cx+s, cy),
        "tr": (cx, cy+s, cx, cy, cx-s, cy),
        "bl": (cx, cy-s, cx, cy, cx+s, cy),
        "br": (cx, cy-s, cx, cy, cx-s, cy),
    }
    canvas.create_line(*coords[pos], fill=color, width=2)


# ══════════════════════════════════════════════════════════════════════════════
#  PANTALLA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class PantallaPrincipal:
    """
    Pantalla principal stub de NébulaVault.
    Recibe el dict de datos del usuario de Firebase.
    """

    W, H = 860, 540

    def __init__(self, datos_usuario: dict) -> None:
        self._datos   = datos_usuario
        self._root    = tk.Tk()
        self._t_start = time.time()

        self._configurar()
        self._construir()
        self._animar()
        self._root.mainloop()

    # ── Configuración ─────────────────────────────────────────────────────────

    def _configurar(self) -> None:
        self._root.title("NébulaVault — Bóveda")
        self._root.configure(bg=BG_VOID)
        self._root.resizable(False, False)
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(
            f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}"
        )

    # ── Construcción ──────────────────────────────────────────────────────────

    def _construir(self) -> None:
        W, H = self.W, self.H

        # ── Canvas de fondo ───────────────────────────────────────────────
        self._bg = tk.Canvas(self._root, width=W, height=H,
                             bg=BG_VOID, highlightthickness=0)
        self._bg.place(x=0, y=0)
        _hex_grid(self._bg, W, H)

        # Bordes de acento
        self._bg.create_line(0, 0, 0, H,   fill=ACCENT_CYAN, width=3)
        self._bg.create_line(3, 0, 3, H,   fill=CYAN_20,     width=1)
        self._bg.create_line(0, H-3, W, H-3, fill=ACCENT_CYAN, width=2)

        # Esquinas decorativas
        _corner(self._bg, 20, 20, 32, ACCENT_CYAN, "tl")
        _corner(self._bg, W-20, 20, 32, ACCENT_CYAN, "tr")
        _corner(self._bg, 20, H-20, 32, ACCENT_CYAN, "bl")
        _corner(self._bg, W-20, H-20, 32, ACCENT_CYAN, "br")

        # ── Canvas de logo animado ────────────────────────────────────────
        self._logo_c = tk.Canvas(self._root, width=80, height=80,
                                 bg=BG_VOID, highlightthickness=0)
        self._logo_c.place(x=W//2 - 40, y=68)
        self._dibujar_logo()

        # ── Nombre de la app ──────────────────────────────────────────────
        tk.Label(self._root, text="NÉBULA",
                 font=("Courier New", 26, "bold"),
                 bg=BG_VOID, fg=ACCENT_CYAN).place(x=W//2 - 112, y=160)
        tk.Label(self._root, text="VAULT",
                 font=("Courier New", 26, "bold"),
                 bg=BG_VOID, fg=TEXT_MAIN).place(x=W//2 + 2, y=160)

        # ── Línea separadora decorativa ───────────────────────────────────
        sep = tk.Canvas(self._root, width=320, height=2,
                        bg=BG_VOID, highlightthickness=0)
        sep.place(x=W//2 - 160, y=200)
        sep.create_line(0, 1, 120, 1, fill=CYAN_33, width=1)
        sep.create_oval(124, 0, 132, 2, fill=ACCENT_CYAN, outline="")
        sep.create_oval(144, 0, 152, 2, fill=ACCENT_CYAN, outline="")
        sep.create_oval(164, 0, 172, 2, fill=ACCENT_CYAN, outline="")
        sep.create_line(176, 1, 320, 1, fill=CYAN_33, width=1)

        # ── Indicador de acceso ───────────────────────────────────────────
        self._bg.create_oval(W//2 - 5, 228, W//2 + 5, 238,
                             fill=SUCCESS, outline="")
        tk.Label(self._root,
                 text="ACCESO CONCEDIDO",
                 font=("Courier New", 9, "bold"),
                 bg=BG_VOID, fg=SUCCESS).place(x=W//2 - 58, y=226)

        # ── Mensaje principal ─────────────────────────────────────────────
        nombre = (self._datos.get("displayName") or
                  self._datos.get("email", "usuario").split("@")[0])

        tk.Label(self._root,
                 text=f"Bienvenido, {nombre}.",
                 font=("Courier New", 17, "bold"),
                 bg=BG_VOID, fg=TEXT_MAIN).place(anchor="center",
                                                  x=W//2, y=285)

        tk.Label(self._root,
                 text="Tu bóveda está lista. Aquí administrarás\n"
                      "tus credenciales de forma segura y local.",
                 font=("Courier New", 10),
                 bg=BG_VOID, fg=TEXT_MUTED,
                 justify="center").place(anchor="center", x=W//2, y=326)

        # ── Tarjeta de estado ─────────────────────────────────────────────
        card = tk.Frame(self._root, bg=BG_CARD,
                        highlightthickness=1,
                        highlightbackground=BORDER_DARK)
        card.place(anchor="center", x=W//2, y=418, width=480, height=60)

        items = [
            ("🔒", "CIFRADO",    "AES-256",   ACCENT_CYAN),
            ("☁",  "MODO",       "CLOUD",     ACCENT_PURPLE),
            ("✔",  "TÉRMINOS",   "ACEPTADOS", SUCCESS),
        ]
        for col_idx, (ico, lbl, val, color) in enumerate(items):
            cell = tk.Frame(card, bg=BG_CARD)
            cell.pack(side="left", expand=True, fill="both", padx=10, pady=8)
            tk.Label(cell, text=f"{ico}  {lbl}",
                     font=("Courier New", 7), bg=BG_CARD,
                     fg=TEXT_MUTED).pack(anchor="center")
            tk.Label(cell, text=val,
                     font=("Courier New", 9, "bold"),
                     bg=BG_CARD, fg=color).pack(anchor="center")

        # ── Footer ────────────────────────────────────────────────────────
        tk.Label(self._root,
                 text="v1.0.0  //  NÉBULAVAULT  //  CONFIDENTIAL",
                 font=("Courier New", 7),
                 bg=BG_VOID, fg=TEXT_FAINT).place(anchor="center",
                                                   x=W//2, y=H - 18)

    def _dibujar_logo(self) -> None:
        c = self._logo_c
        c.delete("all")
        for radio, color, grosor in [
            (38, CYAN_33, 1),
            (32, CYAN_53, 1),
            (26, ACCENT_CYAN, 2),
        ]:
            c.create_oval(40-radio, 40-radio, 40+radio, 40+radio,
                          outline=color, fill="", width=grosor)
        c.create_polygon(40,10, 60,20, 60,40, 40,62, 20,40, 20,20,
                         fill=BG_CARD, outline=ACCENT_CYAN, width=2)
        c.create_oval(35,34, 45,44,
                      fill=BG_CARD, outline=ACCENT_CYAN, width=2)
        c.create_rectangle(33,40, 47,50,
                           fill=CYAN_53, outline="")

    # ── Animación: pulso del logo ─────────────────────────────────────────────

    def _animar(self) -> None:
        t = time.time() - self._t_start
        radio = int(26 + 5 * math.sin(t * 2.4))
        self._logo_c.delete("pulse")
        self._logo_c.create_oval(
            40 - radio, 40 - radio, 40 + radio, 40 + radio,
            outline=ACCENT_CYAN, fill="", width=1, tags="pulse"
        )
        self._root.after(50, self._animar)