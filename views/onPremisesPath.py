"""
views/onPremisesPath.py
════════════════════════════════════════════════════════════════════════════
NébulaVault — Pantalla de selección de directorio para modo On-Premises.

El usuario ingresa (o selecciona mediante file picker) el directorio donde
se almacenará la base de datos local `nebulavault.db`.

Al confirmar:
  1. Se valida que el directorio exista y sea escribible.
  2. Se inicializa (o abre) la base de datos SQLite.
  3. Se destruye esta ventana y se abre BovedaScreenLocal.
════════════════════════════════════════════════════════════════════════════
"""

import math
import os
import tkinter as tk
from tkinter import filedialog, messagebox

from services.local_storage import init_db

# ═════════════════════════════════════════════════════════════════════════
#  PALETA NÉBULAVAULT
# ═════════════════════════════════════════════════════════════════════════
BG_VOID       = "#07090f"
BG_PANEL      = "#0d1117"
BG_CARD       = "#111827"
BORDER_DARK   = "#1e2939"
ACCENT_CYAN   = "#38bdf8"
ACCENT_PURPLE = "#818cf8"
ACCENT_GOLD   = "#fbbf24"
SUCCESS       = "#34d399"
LOCK_RED      = "#f87171"
TEXT_MAIN     = "#e2e8f0"
TEXT_MUTED    = "#64748b"
TEXT_FAINT    = "#334155"
BTN_ACTIVE    = "#0369a1"
BTN_HOVER     = "#0284c7"
CYAN_20       = "#0f2535"
HEX_GRID_COLOR = "#0d1520"
HEX_SPACING    = 48

FONT_DISPLAY  = ("Courier New", 22, "bold")
FONT_SUBTITLE = ("Courier New", 10, "bold")
FONT_LABEL    = ("Courier New",  9, "normal")
FONT_FAINT    = ("Courier New",  8, "normal")
FONT_BTN      = ("Courier New", 11, "bold")
FONT_INPUT    = ("Courier New", 10, "normal")


# ═════════════════════════════════════════════════════════════════════════
#  HELPERS DE DIBUJO
# ═════════════════════════════════════════════════════════════════════════

def _grilla_hex(canvas: tk.Canvas, w: int, h: int) -> None:
    r  = HEX_SPACING / 2
    hh = r * math.sqrt(3)
    col, x = 0, r
    while x < w + r:
        offset_y = hh if col % 2 else 0
        y = offset_y
        while y < h + hh:
            pts = []
            for i in range(6):
                a = math.radians(60 * i - 30)
                pts += [x + r * 0.72 * math.cos(a),
                        y + r * 0.72 * math.sin(a)]
            canvas.create_polygon(pts, outline=HEX_GRID_COLOR, fill="", width=1)
            y += hh * 2
        x += hh * 1.5
        col += 1


def _esquinas_L(canvas: tk.Canvas, w: int, h: int) -> None:
    m, t = 18, 36
    for (x1, y1, dx, dy) in [(m, m, 1, 1), (w-m, m, -1, 1),
                               (m, h-m, 1, -1), (w-m, h-m, -1, -1)]:
        canvas.create_line(x1, y1, x1 + dx*t, y1, fill=ACCENT_CYAN, width=2)
        canvas.create_line(x1, y1, x1, y1 + dy*t, fill=ACCENT_CYAN, width=2)


# ═════════════════════════════════════════════════════════════════════════
#  BOTÓN PERSONALIZADO
# ═════════════════════════════════════════════════════════════════════════

class NVButton(tk.Canvas):

    def __init__(self, parent, texto: str, acento: str = ACCENT_CYAN,
                 comando=None, ancho: int = 200, alto: int = 42, **kw):
        super().__init__(parent, width=ancho, height=alto,
                         bg=BG_VOID, highlightthickness=0, cursor="hand2", **kw)
        self._texto  = texto
        self._acento = acento
        self._cmd    = comando
        self._ancho  = ancho
        self._alto   = alto
        self._hover  = False
        self._render()
        self.bind("<Enter>",    lambda _: self._set(True))
        self.bind("<Leave>",    lambda _: self._set(False))
        self.bind("<Button-1>", lambda _: self._cmd() if callable(self._cmd) else None)

    def _render(self) -> None:
        self.delete("all")
        w, h = self._ancho, self._alto
        bg = BTN_HOVER if self._hover else BTN_ACTIVE
        self.create_rectangle(1, 1, w-1, h-1, fill=bg, outline=self._acento, width=1)
        t = 7
        for px, py, dx, dy in [(2,2,1,1),(w-2,2,-1,1),(2,h-2,1,-1),(w-2,h-2,-1,-1)]:
            self.create_line(px, py, px+dx*t, py,       fill=self._acento, width=1)
            self.create_line(px, py, px,       py+dy*t, fill=self._acento, width=1)
        self.create_text(w//2, h//2, text=self._texto,
                         fill=TEXT_MAIN, font=FONT_BTN, anchor="center")

    def _set(self, v: bool) -> None:
        self._hover = v
        self._render()


# ═════════════════════════════════════════════════════════════════════════
#  PANTALLA DE SELECCIÓN DE DIRECTORIO
# ═════════════════════════════════════════════════════════════════════════

class OnPremisesPath:
    """
    Pantalla de selección del directorio de trabajo para modo On-Premises.

    Permite al usuario escribir la ruta manualmente o usar el explorador
    de archivos del sistema operativo. Al confirmar se valida el acceso
    al directorio y se navega a BovedaScreenLocal.
    """

    ANCHO = 820
    ALTO  = 480

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._configurar_ventana()
        self._construir_ui()

    # ── Configuración ─────────────────────────────────────────────────────

    def _configurar_ventana(self) -> None:
        self._root.title("NébulaVault — On-Premises · Directorio de trabajo")
        self._root.configure(bg=BG_VOID)
        self._root.resizable(False, False)
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(
            f"{self.ANCHO}x{self.ALTO}"
            f"+{(sw - self.ANCHO) // 2}+{(sh - self.ALTO) // 2}"
        )

    # ── UI ────────────────────────────────────────────────────────────────

    def _construir_ui(self) -> None:
        W, H = self.ANCHO, self.ALTO
        cx   = W // 2

        # Fondo decorativo
        bg = tk.Canvas(self._root, width=W, height=H,
                       bg=BG_VOID, highlightthickness=0)
        bg.place(x=0, y=0)
        _grilla_hex(bg, W, H)
        _esquinas_L(bg, W, H)

        # Línea lateral izquierda
        bg.create_line(10, 60, 10, H - 60, fill=ACCENT_CYAN, width=3)
        bg.create_line(14, 60, 14, H - 60, fill=CYAN_20,     width=1)

        # Línea inferior
        bg.create_line(18, H - 18, W - 18, H - 18, fill=ACCENT_CYAN, width=2)

        # ── Panel central ──────────────────────────────────────────────
        px1, py1 = cx - 310, 54
        px2, py2 = cx + 310, H - 44
        bg.create_rectangle(px1, py1, px2, py2,
                            fill=BG_PANEL, outline=BORDER_DARK, width=1)
        bg.create_line(px1, py1, px2, py1, fill=ACCENT_CYAN, width=2)

        # ── Título ────────────────────────────────────────────────────
        bg.create_text(cx, py1 + 32, text="⬡  ON-PREMISES",
                       fill=ACCENT_CYAN, font=FONT_DISPLAY, anchor="center")
        bg.create_text(cx, py1 + 56,
                       text="SELECCIONA EL DIRECTORIO DE ALMACENAMIENTO",
                       fill=TEXT_MUTED, font=FONT_FAINT, anchor="center")

        # Separador
        bg.create_line(cx - 220, py1 + 70, cx + 220, py1 + 70,
                       fill=ACCENT_CYAN, width=1)

        # ── Descripción ───────────────────────────────────────────────
        bg.create_text(
            cx, py1 + 94,
            text="Las bóvedas y entradas se guardarán en un archivo\n"
                 "nebulavault.db dentro del directorio que elijas.",
            fill=TEXT_MUTED, font=FONT_LABEL, anchor="center", justify="center",
        )

        # ── Campo de ruta ─────────────────────────────────────────────
        frame_path = tk.Frame(self._root, bg=BG_PANEL)
        frame_path.place(x=cx - 295, y=py1 + 126, width=590)

        tk.Label(frame_path, text="DIRECTORIO", bg=BG_PANEL,
                 fg=TEXT_MUTED, font=FONT_LABEL).pack(anchor="w", pady=(0, 3))

        input_row = tk.Frame(frame_path, bg=BG_PANEL)
        input_row.pack(fill="x")

        # Marco del campo
        self._marco_path = tk.Frame(input_row, bg=BORDER_DARK, padx=1, pady=1)
        self._marco_path.pack(side="left", fill="x", expand=True)

        self._var_path = tk.StringVar()
        self._entry_path = tk.Entry(
            self._marco_path,
            textvariable=self._var_path,
            bg=BG_CARD, fg=TEXT_MAIN, insertbackground=ACCENT_CYAN,
            relief="flat", font=FONT_INPUT, bd=4,
        )
        self._entry_path.pack(fill="x")
        self._entry_path.bind(
            "<FocusIn>",  lambda _: self._marco_path.config(bg=ACCENT_CYAN))
        self._entry_path.bind(
            "<FocusOut>", lambda _: self._marco_path.config(bg=BORDER_DARK))
        self._entry_path.bind("<Return>", lambda _: self._confirmar())

        # Botón explorar
        btn_explorar = tk.Canvas(
            input_row, width=104, height=30,
            bg=BG_VOID, highlightthickness=0, cursor="hand2",
        )
        btn_explorar.pack(side="left", padx=(6, 0))
        btn_explorar.create_rectangle(
            1, 1, 103, 29, fill=BG_CARD, outline=BORDER_DARK, width=1)
        btn_explorar.create_text(
            52, 15, text="📁  Explorar",
            fill=TEXT_MUTED, font=FONT_FAINT, anchor="center")
        btn_explorar.bind("<Enter>",
            lambda _: btn_explorar.itemconfig(2, fill=TEXT_MAIN))
        btn_explorar.bind("<Leave>",
            lambda _: btn_explorar.itemconfig(2, fill=TEXT_MUTED))
        btn_explorar.bind("<Button-1>", lambda _: self._explorar())

        # ── Etiqueta de error ──────────────────────────────────────────
        self._lbl_err = tk.Label(
            self._root, text="", bg=BG_PANEL,
            fg=LOCK_RED, font=FONT_FAINT, wraplength=560, justify="left",
        )
        self._lbl_err.place(x=cx - 280, y=py1 + 190)

        # ── Botones de acción ──────────────────────────────────────────
        btn_y = py1 + 218

        NVButton(
            self._root,
            texto="✔  CONTINUAR",
            acento=ACCENT_CYAN,
            comando=self._confirmar,
            ancho=200, alto=44,
        ).place(x=cx - 105, y=btn_y)

        # ── Enlace volver ──────────────────────────────────────────────
        lbl_volver = tk.Label(
            self._root, text="← Volver",
            bg=BG_PANEL, fg=TEXT_MUTED,
            font=FONT_FAINT, cursor="hand2",
        )
        lbl_volver.place(x=cx - 295, y=py2 - 28)
        lbl_volver.bind("<Button-1>", lambda _: self._volver())
        lbl_volver.bind("<Enter>",    lambda _: lbl_volver.config(fg=ACCENT_CYAN))
        lbl_volver.bind("<Leave>",    lambda _: lbl_volver.config(fg=TEXT_MUTED))

        # ── Footer ─────────────────────────────────────────────────────
        bg.create_text(
            cx, H - 8,
            text="v1.0.0  //  NÉBULAVAULT  ON-PREMISES  //  ALMACENAMIENTO LOCAL",
            fill=TEXT_FAINT, font=FONT_FAINT, anchor="center",
        )

        self._entry_path.focus_set()

    # ── Acciones ──────────────────────────────────────────────────────────

    def _explorar(self) -> None:
        directorio = filedialog.askdirectory(
            title="Selecciona el directorio de almacenamiento",
            mustexist=True,
            parent=self._root,
        )
        if directorio:
            self._var_path.set(directorio)
            self._lbl_err.config(text="")

    def _confirmar(self) -> None:
        ruta = self._var_path.get().strip()

        if not ruta:
            self._lbl_err.config(text="Debes ingresar o seleccionar un directorio.")
            return

        if not os.path.isdir(ruta):
            self._lbl_err.config(
                text=f"El directorio no existe: {ruta}"
            )
            return

        if not os.access(ruta, os.W_OK):
            self._lbl_err.config(
                text="No tienes permisos de escritura en ese directorio."
            )
            return

        try:
            db_path = init_db(ruta)
        except Exception as exc:
            self._lbl_err.config(
                text=f"No se pudo inicializar la base de datos:\n{exc}"
            )
            return

        # Navegar a BovedaScreenLocal
        self._root.destroy()
        from views.bovedaScreenLocal import BovedaScreenLocal
        BovedaScreenLocal(db_path)

    def _volver(self) -> None:
        for w in self._root.winfo_children():
            w.destroy()
        from views.WelcomeScreen import WelcomeScreen
        WelcomeScreen(self._root)
