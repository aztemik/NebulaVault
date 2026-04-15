"""
views/profileScreen.py
════════════════════════════════════════════════════════════════════════════
NébulaVault — Pantalla de Perfil de Usuario.

Muestra los datos del usuario autenticado (nombre, correo, rol, modo,
fecha de creación, estado de verificación) y permite cerrar sesión.

Abre como tk.Toplevel sobre la ventana de Bóvedas.
════════════════════════════════════════════════════════════════════════════
"""

import math
import tkinter as tk

from firebase_config import get_firebase_app
from firebase_admin import firestore

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

FONT_DISPLAY  = ("Courier New", 18, "bold")
FONT_TITLE    = ("Courier New", 11, "bold")
FONT_SUBTITLE = ("Courier New",  9, "bold")
FONT_LABEL    = ("Courier New",  9, "normal")
FONT_VALUE    = ("Courier New",  9, "bold")
FONT_FAINT    = ("Courier New",  8, "normal")
FONT_BTN      = ("Courier New", 10, "bold")


# ═════════════════════════════════════════════════════════════════════════
#  WIDGET NVButton (local)
# ═════════════════════════════════════════════════════════════════════════

class _NVButton(tk.Canvas):
    def __init__(self, parent, texto: str, acento: str = ACCENT_CYAN,
                 comando=None, ancho: int = 220, alto: int = 40, **kw):
        super().__init__(parent, width=ancho, height=alto,
                         bg=BG_VOID, highlightthickness=0, cursor="hand2", **kw)
        self._texto, self._acento, self._cmd = texto, acento, comando
        self._ancho, self._alto, self._hover = ancho, alto, False
        self._render()
        self.bind("<Enter>",    lambda _: self._set_hover(True))
        self.bind("<Leave>",    lambda _: self._set_hover(False))
        self.bind("<Button-1>", lambda _: self._cmd() if callable(self._cmd) else None)

    def _render(self) -> None:
        self.delete("all")
        w, h = self._ancho, self._alto
        bg = BTN_HOVER if self._hover else BTN_ACTIVE
        self.create_rectangle(1, 1, w-1, h-1, fill=bg, outline=self._acento, width=1)
        t = 7
        for px, py, dx, dy in [(2,2,1,1),(w-2,2,-1,1),(2,h-2,1,-1),(w-2,h-2,-1,-1)]:
            self.create_line(px, py, px+dx*t, py,        fill=self._acento, width=1)
            self.create_line(px, py, px,       py+dy*t,  fill=self._acento, width=1)
        self.create_text(w//2, h//2, text=self._texto,
                         fill=TEXT_MAIN, font=FONT_BTN, anchor="center")

    def _set_hover(self, v: bool) -> None:
        self._hover = v
        self._render()


# ═════════════════════════════════════════════════════════════════════════
#  PANTALLA PERFIL
# ═════════════════════════════════════════════════════════════════════════

class ProfileScreen:
    """
    Ventana de perfil (Toplevel).

    Parámetros:
        parent        — ventana padre (BovedaScreen root), que se ocultó
                        antes de abrir esta pantalla.
        datos_usuario — dict devuelto por login_con_email  (localId, email,
                        displayName, emailVerified…)
        on_logout     — callable invocado al pulsar Cerrar Sesión; destruye
                        la ventana padre y abre el login.
        on_volver     — callable invocado al pulsar Volver; restaura la
                        ventana de bóvedas.
    """

    W = 440
    H = 540

    def __init__(self, parent: tk.Tk, datos_usuario: dict,
                 on_logout, on_volver) -> None:
        self._parent    = parent
        self._datos     = datos_usuario
        self._uid       = datos_usuario.get("localId", "")
        self._on_logout = on_logout
        self._on_volver = on_volver
        self._perfil    = {}   # datos de Firestore

        self._top = tk.Toplevel(parent)
        self._top.title("NébulaVault — Mi Perfil")
        self._top.configure(bg=BG_VOID)
        self._top.resizable(False, False)
        # Al cerrar con la X del sistema operativo, volver a bóvedas
        self._top.protocol("WM_DELETE_WINDOW", self._volver)
        self._centrar()
        self._cargar_perfil()
        self._construir()

    # ── centrar ventana ──────────────────────────────────────────────────

    def _centrar(self) -> None:
        sw = self._top.winfo_screenwidth()
        sh = self._top.winfo_screenheight()
        self._top.geometry(
            f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}"
        )

    # ── carga de datos ───────────────────────────────────────────────────

    def _cargar_perfil(self) -> None:
        """Lee el documento usuarios/{uid} de Firestore."""
        try:
            app = get_firebase_app()
            db  = firestore.client(app=app)
            snap = db.collection("usuarios").document(self._uid).get()
            if snap.exists:
                self._perfil = snap.to_dict()
        except Exception:
            pass   # si falla, mostrará lo que hay en datos_usuario

    # ── construcción UI ──────────────────────────────────────────────────

    def _construir(self) -> None:
        W, H = self.W, self.H

        # Fondo con rejilla hexagonal
        bg = tk.Canvas(self._top, width=W, height=H,
                       bg=BG_VOID, highlightthickness=0)
        bg.place(x=0, y=0)
        self._dibujar_fondo(bg, W, H)

        # ── Encabezado ──────────────────────────────────────────────────
        bg.create_line(0, 0, 0, H, fill=ACCENT_PURPLE, width=3)
        bg.create_line(3, 0, 3, H, fill=CYAN_20, width=1)
        bg.create_line(0, H-2, W, H-2, fill=ACCENT_PURPLE, width=2)

        bg.create_text(W//2, 36, text="◈  MI PERFIL",
                       fill=ACCENT_PURPLE, font=FONT_DISPLAY, anchor="center")
        bg.create_text(W//2, 58, text="NÉBULAVAULT  ·  CUENTA DE USUARIO",
                       fill=TEXT_MUTED, font=FONT_FAINT, anchor="center")

        # Separador
        bg.create_line(24, 72, W-24, 72, fill=BORDER_DARK, width=1)

        # ── Avatar hexagonal ────────────────────────────────────────────
        cx, cy_av = W//2, 116
        r = 36
        pts = []
        for i in range(6):
            a = math.radians(60*i - 30)
            pts += [cx + r*math.cos(a), cy_av + r*math.sin(a)]
        bg.create_polygon(pts, outline=ACCENT_PURPLE, fill=BG_CARD, width=2)
        # Inicial del nombre
        nombre_fs = (self._perfil.get("nombre")
                     or self._datos.get("displayName", "?"))
        inicial = nombre_fs[0].upper() if nombre_fs else "?"
        bg.create_text(cx, cy_av, text=inicial,
                       fill=ACCENT_PURPLE, font=("Courier New", 22, "bold"),
                       anchor="center")

        # ── Nombre y correo ──────────────────────────────────────────────
        nombre = (self._perfil.get("nombre")
                  or self._datos.get("displayName", "—"))
        email  = (self._perfil.get("email")
                  or self._datos.get("email", "—"))

        bg.create_text(W//2, 166, text=nombre,
                       fill=TEXT_MAIN, font=FONT_TITLE, anchor="center")
        bg.create_text(W//2, 184, text=email,
                       fill=TEXT_MUTED, font=FONT_LABEL, anchor="center")

        # Badge verificación
        verificado = (self._perfil.get("email_verificado")
                      or self._datos.get("emailVerified", False))
        badge_txt   = "✔  Correo verificado" if verificado else "✕  Correo no verificado"
        badge_color = SUCCESS if verificado else LOCK_RED
        bg.create_text(W//2, 202, text=badge_txt,
                       fill=badge_color, font=FONT_FAINT, anchor="center")

        # ── Separador ───────────────────────────────────────────────────
        bg.create_line(24, 220, W-24, 220, fill=BORDER_DARK, width=1)

        # ── Tabla de datos ───────────────────────────────────────────────
        filas = self._construir_filas()
        x_lbl = 44
        x_val = W//2 + 10
        y0    = 236
        dy    = 28

        for i, (etiqueta, valor, color) in enumerate(filas):
            y = y0 + i * dy
            bg.create_text(x_lbl, y, text=etiqueta,
                           fill=TEXT_MUTED, font=FONT_SUBTITLE, anchor="w")
            # Línea punteada separadora
            bg.create_line(x_lbl + 100, y+4, x_val - 8, y+4,
                           fill=TEXT_FAINT, dash=(2, 4), width=1)
            bg.create_text(x_val, y, text=valor,
                           fill=color, font=FONT_VALUE, anchor="w")

        # ── Separador ───────────────────────────────────────────────────
        y_sep2 = y0 + len(filas) * dy + 10
        bg.create_line(24, y_sep2, W-24, y_sep2, fill=BORDER_DARK, width=1)

        # ── Botones ──────────────────────────────────────────────────────
        y_btns = y_sep2 + 22

        _NVButton(self._top, texto="⊗  CERRAR SESIÓN",
                  acento=LOCK_RED, comando=self._cerrar_sesion,
                  ancho=200, alto=40).place(x=W//2 - 100, y=y_btns)

        y_close = y_btns + 54
        lbl_close = tk.Label(
            self._top, text="← Volver a bóvedas",
            bg=BG_VOID, fg=TEXT_MUTED, font=FONT_FAINT, cursor="hand2",
        )
        lbl_close.place(x=W//2, y=y_close, anchor="center")
        lbl_close.bind("<Button-1>", lambda _: self._volver())
        lbl_close.bind("<Enter>", lambda _: lbl_close.config(fg=ACCENT_CYAN))
        lbl_close.bind("<Leave>", lambda _: lbl_close.config(fg=TEXT_MUTED))

        # Footer
        bg.create_text(W//2, H-10,
                       text="v1.0.0  //  NÉBULAVAULT  //  CONFIDENTIAL",
                       fill=TEXT_FAINT, font=FONT_FAINT, anchor="center")

    def _construir_filas(self) -> list[tuple[str, str, str]]:
        """Devuelve lista de (etiqueta, valor, color) para la tabla de datos."""
        # Rol
        rol = self._perfil.get("rol", "usuario").capitalize()

        # Modo
        modo_raw = self._perfil.get("modo", "cloud")
        modo = "☁  Cloud" if modo_raw == "cloud" else "🖥  On-Premises"

        # Estado
        activo = self._perfil.get("activo", True)
        estado_txt   = "Activo" if activo else "Inactivo"
        estado_color = SUCCESS if activo else LOCK_RED

        # Fecha de creación
        creado_en = self._perfil.get("creado_en")
        if creado_en is not None:
            try:
                # Firestore devuelve DatetimeWithNanoseconds
                dt = creado_en
                fecha = f"{dt.day:02d}/{dt.month:02d}/{dt.year}"
            except Exception:
                fecha = "—"
        else:
            fecha = "—"

        # UID (truncado para no ocupar demasiado espacio)
        uid_corto = self._uid[:20] + "…" if len(self._uid) > 20 else self._uid

        return [
            ("ROL",           rol,          ACCENT_CYAN),
            ("MODO",          modo,         ACCENT_CYAN),
            ("ESTADO",        estado_txt,   estado_color),
            ("MIEMBRO DESDE", fecha,        TEXT_MAIN),
            ("UID",           uid_corto,    TEXT_MUTED),
        ]

    # ── fondo hexagonal ──────────────────────────────────────────────────

    def _dibujar_fondo(self, canvas: tk.Canvas, W: int, H: int) -> None:
        r  = 22
        dx = r * 3 * 0.75
        dy = r * math.sqrt(3)
        col, x = 0, -r
        while x < W + r:
            y = (dy/2 if col % 2 else 0) - r
            while y < H + r:
                pts = []
                for i in range(6):
                    a = math.radians(60*i - 30)
                    pts += [x + r*0.65*math.cos(a), y + r*0.65*math.sin(a)]
                canvas.create_polygon(pts, outline="#0d1520", fill="", width=1)
                y += dy
            x += dx
            col += 1

    # ── navegación ───────────────────────────────────────────────────────

    def _volver(self) -> None:
        """Destruye el perfil y restaura la pantalla de bóvedas."""
        self._top.destroy()
        self._on_volver()

    def _cerrar_sesion(self) -> None:
        """Destruye el perfil y delega el logout (destruye bóvedas + abre login)."""
        self._top.destroy()
        self._on_logout()
