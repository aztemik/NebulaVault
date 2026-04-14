from pathlib import Path
import math
import time
import tkinter as tk
from tkinter import ttk, messagebox
from views.cloud import PantallaCloud


# ── Opcional: descomenta si tu app usa Firebase ──────────────────────────────
# import firebase_admin
# from firebase_admin import credentials, firestore

# ═════════════════════════════════════════════════════════════════════════════
#  PALETA NÉBULAVAULT — DESIGN TOKENS
# ═════════════════════════════════════════════════════════════════════════════
BG_VOID        = "#07090f"
BG_PANEL       = "#0d1117"
BG_CARD        = "#111827"
BORDER_DARK    = "#1e2939"
BORDER_ACCENT  = "#0ea5e9"

ACCENT_CYAN    = "#38bdf8"
ACCENT_GLOW    = "#7dd3fc"
ACCENT_PURPLE  = "#818cf8"
ACCENT_GOLD    = "#fbbf24"
SUCCESS        = "#34d399"
LOCK_RED       = "#f87171"

TEXT_MAIN      = "#e2e8f0"
TEXT_MUTED     = "#64748b"
TEXT_FAINT     = "#334155"

BTN_ACTIVE     = "#0369a1"
BTN_HOVER      = "#0284c7"
BTN_DISABLED   = "#1e2939"

CYAN_05        = "#09141a"
CYAN_13        = "#0c1d27"
CYAN_20        = "#0f2535"
CYAN_27        = "#122d42"
CYAN_33        = "#153650"
CYAN_53        = "#1e5478"
CYAN_80        = "#2b9acc"

HEX_GRID_COLOR = "#0d1520"
HEX_SPACING    = 48

FONT_DISPLAY   = ("Courier New", 26, "bold")
FONT_SUBTITLE  = ("Courier New", 10, "bold")
FONT_LABEL     = ("Courier New",  9, "normal")
FONT_FAINT     = ("Courier New",  8, "normal")
FONT_BTN       = ("Courier New", 11, "bold")


# ═════════════════════════════════════════════════════════════════════════════
#  FUNCIONES STUB — lógica de navegación
# ═════════════════════════════════════════════════════════════════════════════

def abrir_pantalla_on_premises(root: tk.Tk) -> None:
    """
    Abre la pantalla correspondiente al modo On-Premises.
    TODO: implementar la lógica de navegación.
    """
    pass


def abrir_pantalla_nube(root: tk.Tk) -> None:
    # Limpia todos los widgets de la pantalla principal
    for widget in root.winfo_children():
        widget.destroy()

    # Entrega el mismo root a PantallaCloud para que construya su UI encima
    PantallaCloud(root)


# ═════════════════════════════════════════════════════════════════════════════
#  HELPERS DE DIBUJO
# ═════════════════════════════════════════════════════════════════════════════

def dibujar_grilla_hexagonal(canvas: tk.Canvas, ancho: int, alto: int) -> None:
    """Dibuja una grilla hexagonal decorativa de fondo."""
    r = HEX_SPACING / 2
    h = r * math.sqrt(3)
    col = 0
    x = r
    while x < ancho + r:
        fila = 0
        offset_y = h if col % 2 else 0
        y = offset_y
        while y < alto + h:
            pts = []
            for i in range(6):
                angulo = math.radians(60 * i - 30)
                pts.append(x + r * 0.72 * math.cos(angulo))
                pts.append(y + r * 0.72 * math.sin(angulo))
            canvas.create_polygon(pts, outline=HEX_GRID_COLOR, fill="", width=1)
            y += h * 2
        x += h * 1.5
        col += 1


def dibujar_esquinas_L(canvas: tk.Canvas, ancho: int, alto: int,
                       tam: int = 36, color: str = ACCENT_CYAN,
                       grosor: int = 2) -> None:
    """Dibuja las cuatro esquinas en L decorativas."""
    m = 18   # margen desde el borde de la ventana
    # Superior-izquierda
    canvas.create_line(m, m + tam, m, m, fill=color, width=grosor)
    canvas.create_line(m, m, m + tam, m, fill=color, width=grosor)
    # Superior-derecha
    canvas.create_line(ancho - m, m, ancho - m - tam, m, fill=color, width=grosor)
    canvas.create_line(ancho - m, m, ancho - m, m + tam, fill=color, width=grosor)
    # Inferior-izquierda
    canvas.create_line(m, alto - m, m, alto - m - tam, fill=color, width=grosor)
    canvas.create_line(m, alto - m, m + tam, alto - m, fill=color, width=grosor)
    # Inferior-derecha
    canvas.create_line(ancho - m, alto - m, ancho - m - tam, alto - m, fill=color, width=grosor)
    canvas.create_line(ancho - m, alto - m, ancho - m, alto - m - tam, fill=color, width=grosor)


def dibujar_linea_lateral(canvas: tk.Canvas, alto: int,
                          margen_v: int = 60) -> None:
    """Línea lateral izquierda: 3 px ACCENT_CYAN + 1 px CYAN_20."""
    x = 10
    canvas.create_line(x,     margen_v, x,     alto - margen_v,
                       fill=ACCENT_CYAN, width=3)
    canvas.create_line(x + 4, margen_v, x + 4, alto - margen_v,
                       fill=CYAN_20, width=1)


def dibujar_linea_inferior(canvas: tk.Canvas, ancho: int, alto: int,
                           margen_h: int = 18) -> None:
    """Línea inferior: 2 px ACCENT_CYAN."""
    y = alto - 18
    canvas.create_line(margen_h, y, ancho - margen_h, y,
                       fill=ACCENT_CYAN, width=2)


def dibujar_separador(canvas: tk.Canvas, cx: int, y: int,
                      mitad: int = 120, color: str = ACCENT_CYAN) -> None:
    """Separador horizontal centrado de 1 px."""
    canvas.create_line(cx - mitad, y, cx + mitad, y, fill=color, width=1)


# ═════════════════════════════════════════════════════════════════════════════
#  BOTÓN PERSONALIZADO NÉBULAVAULT
# ═════════════════════════════════════════════════════════════════════════════

class NVButton(tk.Canvas):
    """
    Botón estilo NébulaVault dibujado sobre un Canvas.
    Tiene borde de acento, esquinas rectas y efecto hover.
    """

    def __init__(self, parent, texto: str, acento: str = ACCENT_CYAN,
                 comando=None, ancho: int = 220, alto: int = 52, **kw):
        super().__init__(parent, width=ancho, height=alto,
                         bg=BG_VOID, highlightthickness=0, cursor="hand2", **kw)
        self._texto   = texto
        self._acento  = acento
        self._comando = comando
        self._ancho   = ancho
        self._alto    = alto
        self._hover   = False

        self._dibujar()
        self.bind("<Enter>",    self._on_enter)
        self.bind("<Leave>",    self._on_leave)
        self.bind("<Button-1>", self._on_click)

    # ── Renderizado ──────────────────────────────────────────────────────────

    def _dibujar(self) -> None:
        self.delete("all")
        w, h = self._ancho, self._alto
        bg   = BTN_HOVER if self._hover else BTN_ACTIVE
        brd  = self._acento

        # Relleno
        self.create_rectangle(1, 1, w - 1, h - 1, fill=bg, outline="")
        # Borde exterior
        self.create_rectangle(1, 1, w - 1, h - 1, outline=brd, width=1)
        # Mini-esquinas en L internas (decoración)
        t = 8
        for px, py, dx, dy in [(2, 2, 1, 1), (w - 2, 2, -1, 1),
                                (2, h - 2, 1, -1), (w - 2, h - 2, -1, -1)]:
            self.create_line(px, py, px + dx * t, py,        fill=brd, width=1)
            self.create_line(px, py, px,           py + dy * t, fill=brd, width=1)
        # Texto
        self.create_text(w // 2, h // 2, text=self._texto,
                         fill=TEXT_MAIN, font=FONT_BTN, anchor="center")

    # ── Eventos ──────────────────────────────────────────────────────────────

    def _on_enter(self, _) -> None:
        self._hover = True
        self._dibujar()

    def _on_leave(self, _) -> None:
        self._hover = False
        self._dibujar()

    def _on_click(self, _) -> None:
        if callable(self._comando):
            self._comando()


# ═════════════════════════════════════════════════════════════════════════════
#  PANTALLA PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════

class WelcomeScreen:
    """
    Pantalla de bienvenida de NébulaVault.
    Pregunta al usuario si desea operar On-Premises o en la Nube.
    """

    ANCHO = 780
    ALTO  = 500

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self._configurar_ventana()
        self._construir_ui()

    # ── Configuración de ventana ─────────────────────────────────────────────

    def _configurar_ventana(self) -> None:
        self.root.title("NébulaVault — Selección de Entorno")
        self.root.configure(bg=BG_VOID)
        self.root.resizable(False, False)
        # Centrar en pantalla
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        ox = (sw - self.ANCHO) // 2
        oy = (sh - self.ALTO)  // 2
        self.root.geometry(f"{self.ANCHO}x{self.ALTO}+{ox}+{oy}")

    # ── Construcción de la UI ────────────────────────────────────────────────

    def _construir_ui(self) -> None:
        w, h = self.ANCHO, self.ALTO
        cx   = w // 2

        # ── Canvas de fondo decorativo ────────────────────────────────────
        self.bg_canvas = tk.Canvas(self.root, width=w, height=h,
                                   bg=BG_VOID, highlightthickness=0)
        self.bg_canvas.place(x=0, y=0)

        dibujar_grilla_hexagonal(self.bg_canvas, w, h)
        dibujar_linea_lateral(self.bg_canvas, h)
        dibujar_linea_inferior(self.bg_canvas, w, h)
        dibujar_esquinas_L(self.bg_canvas, w, h)

        # ── Panel central ─────────────────────────────────────────────────
        panel_x1, panel_y1 = cx - 270, 80
        panel_x2, panel_y2 = cx + 270, h - 60
        self.bg_canvas.create_rectangle(
            panel_x1, panel_y1, panel_x2, panel_y2,
            fill=BG_PANEL, outline=BORDER_DARK, width=1
        )
        # Línea de acento superior del panel
        self.bg_canvas.create_line(
            panel_x1, panel_y1, panel_x2, panel_y1,
            fill=ACCENT_CYAN, width=2
        )

        # ── Logotipo / marca ──────────────────────────────────────────────
        self.bg_canvas.create_text(
            cx, 115, text="◈  NÉBULAVAULT",
            fill=ACCENT_CYAN, font=FONT_DISPLAY, anchor="center"
        )
        self.bg_canvas.create_text(
            cx, 143, text="SISTEMA DE GESTIÓN DE CREDENCIALES",
            fill=TEXT_MUTED, font=FONT_FAINT, anchor="center"
        )

        # Separador bajo el título
        dibujar_separador(self.bg_canvas, cx, 162, mitad=200)

        # ── Pregunta principal ────────────────────────────────────────────
        self.bg_canvas.create_text(
            cx, 205, text="¿Desea operar on-premises o en la nube?",
            fill=TEXT_MAIN, font=("Courier New", 13, "bold"), anchor="center"
        )
        self.bg_canvas.create_text(
            cx, 228,
            text="Seleccione el entorno de despliegue para continuar.",
            fill=TEXT_MUTED, font=FONT_LABEL, anchor="center"
        )

        # ── Botones ───────────────────────────────────────────────────────
        btn_y = 280
        gap   = 30

        btn_op = NVButton(
            self.root,
            texto   = "⬡  ON-PREMISES",
            acento  = ACCENT_CYAN,
            comando = lambda: abrir_pantalla_on_premises(self.root),
            ancho   = 210,
            alto    = 54,
        )
        btn_op.place(x=cx - 210 - gap // 2, y=btn_y, anchor="nw")

        btn_cloud = NVButton(
            self.root,
            texto   = "☁  EN LA NUBE",
            acento  = ACCENT_PURPLE,
            comando = lambda: abrir_pantalla_nube(self.root),
            ancho   = 210,
            alto    = 54,
        )
        btn_cloud.place(x=cx + gap // 2, y=btn_y, anchor="nw")

        # Etiquetas bajo los botones
        self.bg_canvas.create_text(
            cx - 210 - gap // 2 + 105, btn_y + 66,
            text="Infraestructura local", fill=TEXT_MUTED, font=FONT_FAINT
        )
        self.bg_canvas.create_text(
            cx + gap // 2 + 105, btn_y + 66,
            text="Infraestructura cloud", fill=TEXT_MUTED, font=FONT_FAINT
        )

        # ── Footer ────────────────────────────────────────────────────────
        self.bg_canvas.create_text(
            cx, h - 30,
            text="v1.0.0  //  NÉBULAVAULT SECURE PLATFORM  //  CONFIDENTIAL",
            fill=TEXT_FAINT, font=FONT_FAINT, anchor="center"
        )

        # Indicador de estado
        self.bg_canvas.create_oval(w - 48, h - 40, w - 36, h - 28,
                                   fill=SUCCESS, outline="")
        self.bg_canvas.create_text(w - 30, h - 34,
                                   text="READY", fill=SUCCESS,
                                   font=FONT_FAINT, anchor="w")


