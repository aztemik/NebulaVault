"""
views/bovedaScreen.py
════════════════════════════════════════════════════════════════════════════
NébulaVault — Pantalla de Bóvedas (solo UI / presentación).

Toda la lógica de negocio y persistencia se delega a:
    services/bovedas.py   — CRUD de bóvedas en Firestore
    services/entradas.py  — CRUD de entradas en Firestore
    services/crypto.py    — cifrado / descifrado con Fernet

Layout:
  ┌─────────────┬──────────────────────────────────────────────┐
  │  MIS        │  ⬡ <Nombre bóveda>          [⊘ ELIMINAR]    │
  │  BÓVEDAS    │  ───────────────────────────────────────────  │
  │             │  [⊕ NUEVA ENTRADA]                            │
  │  [Bóveda 1] │                                               │
  │  [Bóveda 2] │  ┌─ correo ────────────────┐  [editar]       │
  │  …          │  │  •••••••  [ ver ]        │  [eliminar]     │
  │             │  │  nota…                   │                 │
  │  [⊕ NUEVA   │  ┌─ Formulario inline ─────────────────────┐ │
  │   BÓVEDA]   │  │  CORREO | CONTRASEÑA | NOTA              │ │
  │             │  │  [✔ GUARDAR]  [✕ CANCELAR]               │ │
  └─────────────┴──────────────────────────────────────────────┘
════════════════════════════════════════════════════════════════════════════
"""

import math
import tkinter as tk
from tkinter import messagebox

from cryptography.fernet import Fernet

from services.crypto   import (cifrar, descifrar,
                                get_fernet_boveda,
                                hashear_password_boveda,
                                verificar_password_boveda,
                                cifrar_password_con_respuesta,
                                descifrar_password_con_respuesta)
from services.bovedas  import (cargar_bovedas, crear_boveda, eliminar_boveda,
                                actualizar_intentos_boveda,
                                bloquear_boveda_permanente,
                                resetear_bloqueo_boveda)
from services.entradas import (cargar_entradas, crear_entrada,
                                actualizar_entrada, eliminar_entrada,
                                contar_entradas)
from views.profileScreen import ProfileScreen

# ═══════════════════════════════════════════════════════════════════════════
#  PALETA NÉBULAVAULT
# ═══════════════════════════════════════════════════════════════════════════
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

FONT_TITLE    = ("Courier New", 11, "bold")
FONT_SUBTITLE = ("Courier New",  9, "bold")
FONT_LABEL    = ("Courier New",  9, "normal")
FONT_FAINT    = ("Courier New",  8, "normal")
FONT_BTN      = ("Courier New",  9, "bold")
FONT_INPUT    = ("Courier New", 10, "normal")


# ═══════════════════════════════════════════════════════════════════════════
#  WIDGETS REUTILIZABLES
# ═══════════════════════════════════════════════════════════════════════════

class NVButton(tk.Canvas):
    """Botón canvas con hover y borde de acento."""

    def __init__(self, parent, texto: str, acento: str = ACCENT_CYAN,
                 comando=None, ancho: int = 180, alto: int = 34, **kw):
        super().__init__(parent, width=ancho, height=alto,
                         bg=BG_VOID, highlightthickness=0, cursor="hand2", **kw)
        self._texto  = texto
        self._acento = acento
        self._cmd    = comando
        self._ancho  = ancho
        self._alto   = alto
        self._hover  = False
        self._render()
        self.bind("<Enter>",    lambda _: self._set_hover(True))
        self.bind("<Leave>",    lambda _: self._set_hover(False))
        self.bind("<Button-1>", lambda _: self._cmd() if callable(self._cmd) else None)

    def _render(self) -> None:
        self.delete("all")
        w, h = self._ancho, self._alto
        bg = BTN_HOVER if self._hover else BTN_ACTIVE
        self.create_rectangle(1, 1, w-1, h-1, fill=bg, outline=self._acento, width=1)
        t = 6
        for px, py, dx, dy in [(2,2,1,1),(w-2,2,-1,1),(2,h-2,1,-1),(w-2,h-2,-1,-1)]:
            self.create_line(px, py, px+dx*t, py,       fill=self._acento, width=1)
            self.create_line(px, py, px,       py+dy*t, fill=self._acento, width=1)
        self.create_text(w//2, h//2, text=self._texto,
                         fill=TEXT_MAIN, font=FONT_BTN, anchor="center")

    def _set_hover(self, v: bool) -> None:
        self._hover = v
        self._render()


class _SmallBtn(tk.Label):
    """Enlace-botón inline para acciones contextuales en tarjetas."""

    def __init__(self, parent, texto: str, color: str, comando, **kw):
        super().__init__(parent, text=texto, bg=BG_CARD, fg=color,
                         font=FONT_FAINT, cursor="hand2", **kw)
        self.bind("<Button-1>", lambda _: comando())
        self.bind("<Enter>",    lambda _: self.config(fg=TEXT_MAIN))
        self.bind("<Leave>",    lambda _: self.config(fg=color))


class NVEntry(tk.Frame):
    """Campo de texto estilizado con etiqueta y efecto focus."""

    def __init__(self, parent, label: str, show: str = "",
                 acento: str = ACCENT_CYAN, ancho_px: int = 280, **kw):
        super().__init__(parent, bg=BG_PANEL, **kw)
        tk.Label(self, text=label, bg=BG_PANEL, fg=TEXT_MUTED,
                 font=FONT_LABEL).pack(anchor="w", pady=(0, 2))
        self._marco = tk.Frame(self, bg=BORDER_DARK, padx=1, pady=1)
        self._marco.pack(fill="x")
        self._var = tk.StringVar()
        self._entry = tk.Entry(
            self._marco, textvariable=self._var, show=show,
            bg=BG_CARD, fg=TEXT_MAIN, insertbackground=acento,
            relief="flat", font=FONT_INPUT,
            width=max(1, ancho_px // 8), bd=3,
        )
        self._entry.pack(fill="x")
        self._barra = tk.Frame(self, bg=BORDER_DARK, height=1)
        self._barra.pack(fill="x")
        self._entry.bind("<FocusIn>",  lambda _: (self._marco.config(bg=acento),
                                                   self._barra.config(bg=acento)))
        self._entry.bind("<FocusOut>", lambda _: (self._marco.config(bg=BORDER_DARK),
                                                   self._barra.config(bg=BORDER_DARK)))

    def get(self)         -> str:  return self._var.get()
    def set(self, v: str) -> None: self._var.set(v)
    def limpiar(self)     -> None: self._var.set("")


# ═══════════════════════════════════════════════════════════════════════════
#  PREGUNTAS DE SEGURIDAD PREDEFINIDAS
# ═══════════════════════════════════════════════════════════════════════════

PREGUNTAS_SEGURIDAD = [
    "¿Cuál es tu materia favorita de la universidad?",
    "¿Cuál es el nombre de tu primera mascota?",
    "¿En qué ciudad naciste?",
    "¿Cuál es el nombre de tu escuela primaria?",
    "¿Cuál es tu película favorita de la infancia?",
]


# ═══════════════════════════════════════════════════════════════════════════
#  PANTALLA DE BÓVEDAS
# ═══════════════════════════════════════════════════════════════════════════

class BovedaScreen:

    W      = 1100
    H      = 660
    LEFT_W = 290

    def __init__(self, datos_usuario: dict) -> None:
        self._datos  = datos_usuario
        self._uid    = datos_usuario.get("localId", "")
        # La clave Fernet es por bóveda; se inicializa al desbloquear una.
        self._fernet: Fernet | None = None

        self._bovedas:          list[dict]       = []
        self._boveda_sel:       dict | None      = None
        self._entradas:         list[dict]       = []
        self._conteos:          dict[str, int]   = {}   # boveda_id → nº entradas
        self._form_modo:        str | None       = None  # "nueva_entrada" | "editar_entrada"
        self._entrada_editando: dict | None      = None

        self._root = tk.Tk()
        self._configurar()
        self._construir_esqueleto()
        self._cargar_bovedas()
        self._root.mainloop()

    # ── Configuración de la ventana ────────────────────────────────────────

    def _configurar(self) -> None:
        nombre = (self._datos.get("displayName") or
                  self._datos.get("email", "usuario").split("@")[0])
        self._root.title(f"NébulaVault — Bóvedas · {nombre}")
        self._root.configure(bg=BG_VOID)
        self._root.resizable(False, False)
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(
            f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}"
        )

    # ══════════════════════════════════════════════════════════════════════
    #  ESQUELETO DE LA PANTALLA (construido una sola vez)
    # ══════════════════════════════════════════════════════════════════════

    def _construir_esqueleto(self) -> None:
        W, H, LW = self.W, self.H, self.LEFT_W

        # Fondo decorativo
        self._bg = tk.Canvas(self._root, width=W, height=H,
                             bg=BG_VOID, highlightthickness=0)
        self._bg.place(x=0, y=0)
        self._dibujar_fondo()

        # ── Panel izquierdo ──────────────────────────────────────────────
        self._left = tk.Frame(self._root, bg=BG_PANEL,
                              highlightthickness=1,
                              highlightbackground=BORDER_DARK)
        self._left.place(x=14, y=14, width=LW, height=H - 28)
        self._left.pack_propagate(False)

        hdr = tk.Frame(self._left, bg=BG_PANEL)
        hdr.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(hdr, text="◈  MIS BÓVEDAS", bg=BG_PANEL,
                 fg=ACCENT_CYAN, font=FONT_TITLE).pack(side="left")

        lbl_perfil = tk.Label(
            hdr, text="👤 Mi perfil",
            bg=BG_PANEL, fg=TEXT_MUTED, font=FONT_FAINT, cursor="hand2",
        )
        lbl_perfil.pack(side="right")
        lbl_perfil.bind("<Button-1>", lambda _: self._abrir_perfil())
        lbl_perfil.bind("<Enter>", lambda _: lbl_perfil.config(fg=ACCENT_CYAN))
        lbl_perfil.bind("<Leave>", lambda _: lbl_perfil.config(fg=TEXT_MUTED))

        tk.Frame(self._left, bg=BORDER_DARK, height=1).pack(fill="x", padx=10)

        # Área scrollable para la lista de bóvedas
        wrap = tk.Frame(self._left, bg=BG_PANEL)
        wrap.pack(fill="both", expand=True, padx=4, pady=6)

        self._cv_bovedas = tk.Canvas(wrap, bg=BG_PANEL, highlightthickness=0)
        sb = tk.Scrollbar(wrap, orient="vertical",
                          command=self._cv_bovedas.yview,
                          bg=BG_PANEL, troughcolor=BG_PANEL)
        self._cv_bovedas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._cv_bovedas.pack(side="left", fill="both", expand=True)

        self._inner_bovedas = tk.Frame(self._cv_bovedas, bg=BG_PANEL)
        self._cv_bovedas.create_window((0, 0), window=self._inner_bovedas,
                                       anchor="nw")
        self._inner_bovedas.bind(
            "<Configure>",
            lambda e: self._cv_bovedas.configure(
                scrollregion=self._cv_bovedas.bbox("all"))
        )
        self._cv_bovedas.bind(
            "<MouseWheel>",
            lambda e: self._cv_bovedas.yview_scroll(
                -1 * (e.delta // 120), "units")
        )

        tk.Frame(self._left, bg=BORDER_DARK, height=1).pack(fill="x", padx=10)

        btn_w = tk.Frame(self._left, bg=BG_PANEL)
        btn_w.pack(fill="x", padx=10, pady=8)
        NVButton(btn_w, texto="⊕  NUEVA BÓVEDA",
                 acento=ACCENT_CYAN,
                 comando=self._dialogo_nueva_boveda,
                 ancho=LW - 20, alto=34).pack()

        # ── Panel derecho ────────────────────────────────────────────────
        RW = W - LW - 36
        self._right = tk.Frame(self._root, bg=BG_PANEL,
                               highlightthickness=1,
                               highlightbackground=BORDER_DARK)
        self._right.place(x=LW + 22, y=14, width=RW, height=H - 28)
        self._right.pack_propagate(False)

        # Cabecera del panel derecho
        self._hdr_r = tk.Frame(self._right, bg=BG_PANEL)
        self._hdr_r.pack(fill="x", padx=12, pady=(10, 6))

        self._lbl_boveda = tk.Label(
            self._hdr_r,
            text="Selecciona o crea una bóveda",
            bg=BG_PANEL, fg=TEXT_MUTED, font=FONT_TITLE,
        )
        self._lbl_boveda.pack(side="left")

        self._btn_del_boveda = NVButton(
            self._hdr_r,
            texto="⊘  ELIMINAR BÓVEDA",
            acento=LOCK_RED,
            comando=self._on_eliminar_boveda,
            ancho=180, alto=28,
        )
        # Visible solo cuando hay bóveda seleccionada

        tk.Frame(self._right, bg=BORDER_DARK, height=1).pack(fill="x", padx=12)

        # Contenedor dinámico de entradas (se vacía y reconstruye)
        self._content = tk.Frame(self._right, bg=BG_PANEL)
        self._content.pack(fill="both", expand=True)

        self._mostrar_placeholder()

        # Footer
        nombre = (self._datos.get("displayName") or
                  self._datos.get("email", "").split("@")[0])
        tk.Label(
            self._root,
            text=f"v1.0.0  //  {nombre.upper()}  //  NÉBULAVAULT  //  CONFIDENTIAL",
            bg=BG_VOID, fg=TEXT_FAINT, font=FONT_FAINT,
        ).place(x=W // 2, y=H - 10, anchor="center")

    def _dibujar_fondo(self) -> None:
        W, H = self.W, self.H
        r  = 24
        dx = r * 3 * 0.75
        dy = r * math.sqrt(3)
        col, x = 0, -r
        while x < W + r:
            y = (dy / 2 if col % 2 else 0) - r
            while y < H + r:
                pts = []
                for i in range(6):
                    a = math.radians(60 * i - 30)
                    pts += [x + r * 0.65 * math.cos(a),
                            y + r * 0.65 * math.sin(a)]
                self._bg.create_polygon(pts, outline="#0d1520", fill="", width=1)
                y += dy
            x += dx
            col += 1
        self._bg.create_line(0, 0, 0, H,     fill=ACCENT_CYAN, width=3)
        self._bg.create_line(3, 0, 3, H,     fill=CYAN_20,     width=1)
        self._bg.create_line(0, H-2, W, H-2, fill=ACCENT_CYAN, width=2)

    # ══════════════════════════════════════════════════════════════════════
    #  PLACEHOLDER
    # ══════════════════════════════════════════════════════════════════════

    def _mostrar_placeholder(self) -> None:
        for w in self._content.winfo_children():
            w.destroy()
        self._btn_del_boveda.pack_forget()
        f = tk.Frame(self._content, bg=BG_PANEL)
        f.place(relx=0.5, rely=0.45, anchor="center")
        tk.Label(f, text="⬡", bg=BG_PANEL, fg=BORDER_DARK,
                 font=("Courier New", 48)).pack()
        tk.Label(f, text="Sin bóveda seleccionada",
                 bg=BG_PANEL, fg=TEXT_MUTED, font=FONT_TITLE).pack()
        tk.Label(f,
                 text="Selecciona una bóveda de la lista\n"
                      "o crea una nueva con el botón inferior.",
                 bg=BG_PANEL, fg=TEXT_FAINT, font=FONT_FAINT,
                 justify="center").pack(pady=(4, 0))

    # ══════════════════════════════════════════════════════════════════════
    #  HANDLERS — BÓVEDAS
    # ══════════════════════════════════════════════════════════════════════

    def _cargar_bovedas(self) -> None:
        try:
            self._bovedas = cargar_bovedas(self._uid)
        except Exception as exc:
            messagebox.showerror("NébulaVault",
                                 f"Error al cargar bóvedas:\n{exc}",
                                 parent=self._root)
            self._bovedas = []
        # Cargar conteo de entradas por bóveda (no requiere descifrar)
        for b in self._bovedas:
            try:
                self._conteos[b["id"]] = contar_entradas(self._uid, b["id"])
            except Exception:
                self._conteos[b["id"]] = 0
        self._renderizar_lista_bovedas()

    def _dialogo_nueva_boveda(self) -> None:
        """
        Toplevel con campos de nombre, contraseña y pregunta de seguridad
        para crear una nueva bóveda.

        La contraseña es la clave de cifrado (PBKDF2 → Fernet).
        La respuesta cifra una copia de esa contraseña para recuperación
        ante bloqueo por intentos fallidos.
        """
        top = tk.Toplevel(self._root)
        top.title("Nueva bóveda")
        top.configure(bg=BG_PANEL)
        top.resizable(False, False)
        w, h = 460, 610
        sw, sh = self._root.winfo_screenwidth(), self._root.winfo_screenheight()
        top.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        frm = tk.Frame(top, bg=BG_PANEL, padx=24, pady=18)
        frm.pack(fill="both", expand=True)

        # ── Título ────────────────────────────────────────────────────────
        tk.Label(frm, text="⬡  NUEVA BÓVEDA", bg=BG_PANEL,
                 fg=ACCENT_CYAN, font=FONT_TITLE).pack(anchor="w", pady=(0, 10))

        # ── Advertencia ───────────────────────────────────────────────────
        warn = tk.Frame(frm, bg="#140d00",
                        highlightthickness=1, highlightbackground=ACCENT_GOLD)
        warn.pack(fill="x", pady=(0, 12))
        tk.Label(warn, text="⚠  ADVERTENCIA",
                 bg="#140d00", fg=ACCENT_GOLD, font=FONT_SUBTITLE,
                 anchor="w").pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(warn,
                 text="Si olvidas la contraseña de esta bóveda Y la respuesta a la\n"
                      "pregunta de seguridad, el contenido será PERMANENTEMENTE\n"
                      "INACCESIBLE. NébulaVault no puede recuperarlo.",
                 bg="#140d00", fg=TEXT_MUTED, font=FONT_FAINT,
                 justify="left").pack(anchor="w", padx=10, pady=(0, 8))

        # ── Separador ─────────────────────────────────────────────────────
        tk.Frame(frm, bg=BORDER_DARK, height=1).pack(fill="x", pady=(0, 10))

        # ── Campos de contraseña ──────────────────────────────────────────
        f_nombre = NVEntry(frm, label="NOMBRE DE LA BÓVEDA",
                           acento=ACCENT_CYAN, ancho_px=400)
        f_nombre.pack(fill="x", pady=(0, 8))

        f_pass = NVEntry(frm, label="CONTRASEÑA DE LA BÓVEDA", show="•",
                         acento=ACCENT_CYAN, ancho_px=400)
        f_pass.pack(fill="x", pady=(0, 8))

        f_confirm = NVEntry(frm, label="CONFIRMAR CONTRASEÑA", show="•",
                            acento=ACCENT_CYAN, ancho_px=400)
        f_confirm.pack(fill="x")

        # ── Separador ─────────────────────────────────────────────────────
        tk.Frame(frm, bg=BORDER_DARK, height=1).pack(fill="x", pady=(12, 8))

        # ── Pregunta de seguridad ─────────────────────────────────────────
        tk.Label(frm, text="PREGUNTA DE SEGURIDAD", bg=BG_PANEL,
                 fg=ACCENT_GOLD, font=FONT_SUBTITLE,
                 anchor="w").pack(anchor="w", pady=(0, 6))

        pregunta_var = tk.StringVar(value=PREGUNTAS_SEGURIDAD[0])
        opt = tk.OptionMenu(frm, pregunta_var, *PREGUNTAS_SEGURIDAD)
        opt.config(
            bg=BG_CARD, fg=TEXT_MAIN, activebackground=CYAN_20,
            activeforeground=TEXT_MAIN, font=FONT_FAINT,
            relief="flat", highlightthickness=1,
            highlightbackground=BORDER_DARK, bd=0, width=50,
        )
        opt["menu"].config(
            bg=BG_CARD, fg=TEXT_MAIN,
            activebackground=ACCENT_GOLD, activeforeground=BG_VOID,
            font=FONT_FAINT,
        )
        opt.pack(anchor="w", pady=(0, 8))

        f_respuesta = NVEntry(frm, label="TU RESPUESTA", show="•",
                              acento=ACCENT_GOLD, ancho_px=400)
        f_respuesta.pack(fill="x")

        # ── Error / estado ────────────────────────────────────────────────
        lbl_err = tk.Label(frm, text="", bg=BG_PANEL, fg=LOCK_RED,
                           font=FONT_FAINT, wraplength=400, justify="left")
        lbl_err.pack(pady=(6, 0), anchor="w")

        # ── Botón ─────────────────────────────────────────────────────────
        def confirmar():
            nombre    = f_nombre.get().strip()
            pw        = f_pass.get()
            pw_conf   = f_confirm.get()
            pregunta  = pregunta_var.get()
            respuesta = f_respuesta.get().strip()

            if not nombre:
                lbl_err.config(text="El nombre no puede estar vacío.")
                return
            if len(pw) < 6:
                lbl_err.config(text="La contraseña debe tener al menos 6 caracteres.")
                return
            if pw != pw_conf:
                lbl_err.config(text="Las contraseñas no coinciden.")
                return
            if len(respuesta) < 2:
                lbl_err.config(text="La respuesta de seguridad es muy corta.")
                return

            top.destroy()
            self._on_crear_boveda(nombre, pw, pregunta, respuesta)

        NVButton(frm, texto="✔  CREAR BÓVEDA",
                 acento=ACCENT_CYAN, comando=confirmar,
                 ancho=200, alto=34).pack(pady=(8, 0))

        f_respuesta._entry.bind("<Return>", lambda _: confirmar())
        f_nombre._entry.focus_set()

        top.wait_visibility()
        top.grab_set()

    def _on_crear_boveda(
        self, nombre: str, password: str,
        pregunta: str, respuesta: str,
    ) -> None:
        try:
            pw_hash          = hashear_password_boveda(password)
            pw_cifrada_resp  = cifrar_password_con_respuesta(
                password, respuesta, self._uid
            )
            nueva = crear_boveda(
                self._uid, nombre, pw_hash,
                pregunta, pw_cifrada_resp,
            )
        except Exception as exc:
            messagebox.showerror("NébulaVault",
                                 f"Error al crear bóveda:\n{exc}",
                                 parent=self._root)
            return
        self._bovedas.append(nueva)
        self._renderizar_lista_bovedas()
        # La bóveda recién creada se desbloquea directamente con la contraseña
        # que acaba de ingresar el usuario — no hace falta pedirla de nuevo.
        self._desbloquear_boveda(nueva, password)

    def _on_eliminar_boveda(self) -> None:
        if not self._boveda_sel:
            return
        nombre = self._boveda_sel.get("nombre", "")
        if not messagebox.askyesno(
            "Eliminar bóveda",
            f"¿Eliminar «{nombre}» y todas sus entradas?\n"
            "Esta acción no se puede deshacer.",
            parent=self._root,
        ):
            return
        try:
            eliminar_boveda(self._uid, self._boveda_sel["id"])
        except Exception as exc:
            messagebox.showerror("NébulaVault",
                                 f"Error al eliminar bóveda:\n{exc}",
                                 parent=self._root)
            return
        self._bovedas   = [b for b in self._bovedas
                           if b["id"] != self._boveda_sel["id"]]
        self._boveda_sel = None
        self._entradas   = []
        self._renderizar_lista_bovedas()
        self._lbl_boveda.config(text="Selecciona o crea una bóveda",
                                fg=TEXT_MUTED)
        self._mostrar_placeholder()

    def _seleccionar_boveda(self, boveda: dict) -> None:
        """Al hacer clic en una bóveda evalúa su estado y actúa en consecuencia."""
        if boveda.get("boveda_inaccesible", False):
            messagebox.showerror(
                "Bóveda inaccesible",
                f"«{boveda.get('nombre', '')}» fue bloqueada permanentemente.\n\n"
                "Esta bóveda no puede abrirse ni recuperarse.",
                parent=self._root,
            )
            return
        if boveda.get("boveda_bloqueada", False):
            self._dialogo_pregunta_seguridad(boveda)
            return
        self._dialogo_desbloquear(boveda)

    def _dialogo_desbloquear(self, boveda: dict) -> None:
        """
        Toplevel que solicita la contraseña de la bóveda.

        Política de bloqueo (acumulada en Firestore):
          · 1er intento fallido  → mensaje de error
          · 2° intento fallido   → advertencia de último intento
          · 3er intento fallido  → bóveda bloqueada → diálogo de pregunta
        """
        top = tk.Toplevel(self._root)
        top.title(f"Desbloquear — {boveda.get('nombre', '')}")
        top.configure(bg=BG_PANEL)
        top.resizable(False, False)
        w, h = 400, 280
        sw, sh = self._root.winfo_screenwidth(), self._root.winfo_screenheight()
        top.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        frm = tk.Frame(top, bg=BG_PANEL, padx=24, pady=20)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="⬡  DESBLOQUEAR BÓVEDA", bg=BG_PANEL,
                 fg=ACCENT_CYAN, font=FONT_TITLE).pack(anchor="w", pady=(0, 4))
        tk.Label(frm, text=f"«{boveda.get('nombre', '')}»",
                 bg=BG_PANEL, fg=TEXT_MUTED, font=FONT_SUBTITLE).pack(
                     anchor="w", pady=(0, 10))

        tk.Frame(frm, bg=BORDER_DARK, height=1).pack(fill="x", pady=(0, 12))

        f_pass = NVEntry(frm, label="CONTRASEÑA DE LA BÓVEDA", show="•",
                         acento=ACCENT_CYAN, ancho_px=340)
        f_pass.pack(fill="x")

        lbl_status = tk.Label(frm, text="", bg=BG_PANEL, fg=LOCK_RED,
                              font=FONT_FAINT, wraplength=340, justify="left")
        lbl_status.pack(pady=(6, 0), anchor="w")

        # Advertencia previa si ya hay 2 intentos fallidos acumulados
        intentos_act = boveda.get("intentos_password", 0)
        if intentos_act == 2:
            lbl_status.config(
                text="⚠  Último intento disponible. Un fallo más bloqueará esta bóveda.",
                fg=ACCENT_GOLD,
            )

        def intentar():
            nonlocal intentos_act
            pw = f_pass.get()
            if not pw:
                lbl_status.config(text="Ingresa la contraseña.", fg=LOCK_RED)
                return

            if not verificar_password_boveda(pw, boveda.get("password_hash", "")):
                intentos_act += 1
                bloquear = intentos_act >= 3

                # Persistir en Firestore (best-effort)
                try:
                    actualizar_intentos_boveda(
                        self._uid, boveda["id"], intentos_act, bloquear
                    )
                except Exception:
                    pass

                # Actualizar objeto local y lista
                boveda["intentos_password"] = intentos_act
                if bloquear:
                    boveda["boveda_bloqueada"] = True
                for b in self._bovedas:
                    if b["id"] == boveda["id"]:
                        b["intentos_password"] = intentos_act
                        if bloquear:
                            b["boveda_bloqueada"] = True

                if bloquear:
                    top.destroy()
                    self._renderizar_lista_bovedas()
                    self._dialogo_pregunta_seguridad(boveda)
                    return

                f_pass.limpiar()
                f_pass._entry.focus_set()

                if intentos_act == 1:
                    lbl_status.config(text="Contraseña incorrecta.", fg=LOCK_RED)
                else:   # intentos_act == 2
                    lbl_status.config(
                        text="⚠  Contraseña incorrecta.\n"
                             "Último intento disponible. Un fallo más bloqueará esta bóveda.",
                        fg=ACCENT_GOLD,
                    )
                return

            # Contraseña correcta — resetear contador
            try:
                actualizar_intentos_boveda(self._uid, boveda["id"], 0, False)
            except Exception:
                pass
            boveda["intentos_password"] = 0
            for b in self._bovedas:
                if b["id"] == boveda["id"]:
                    b["intentos_password"] = 0

            top.destroy()
            self._desbloquear_boveda(boveda, pw)

        NVButton(frm, texto="🔓  ABRIR",
                 acento=ACCENT_CYAN, comando=intentar,
                 ancho=200, alto=34).pack(pady=(10, 0))

        f_pass._entry.bind("<Return>", lambda _: intentar())
        f_pass._entry.focus_set()

        top.wait_visibility()
        top.grab_set()

    def _dialogo_pregunta_seguridad(self, boveda: dict) -> None:
        """
        Toplevel que muestra la pregunta de seguridad para desbloquear la bóveda
        tras agotar los intentos de contraseña.

        · Respuesta correcta → resetea bloqueo y abre la bóveda directamente.
        · Respuesta incorrecta → bóveda bloqueada permanentemente.
        """
        top = tk.Toplevel(self._root)
        top.title(f"Pregunta de seguridad — {boveda.get('nombre', '')}")
        top.configure(bg=BG_PANEL)
        top.resizable(False, False)
        w, h = 460, 330
        sw, sh = self._root.winfo_screenwidth(), self._root.winfo_screenheight()
        top.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        frm = tk.Frame(top, bg=BG_PANEL, padx=24, pady=20)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="🔒  BÓVEDA BLOQUEADA", bg=BG_PANEL,
                 fg=LOCK_RED, font=FONT_TITLE).pack(anchor="w", pady=(0, 4))
        tk.Label(frm,
                 text="Se agotaron los intentos de contraseña.\n"
                      "Responde correctamente para acceder.\n"
                      "Una respuesta incorrecta bloqueará la bóveda permanentemente.",
                 bg=BG_PANEL, fg=TEXT_MUTED, font=FONT_FAINT,
                 justify="left").pack(anchor="w", pady=(0, 10))

        tk.Frame(frm, bg=BORDER_DARK, height=1).pack(fill="x", pady=(0, 12))

        # Mostrar la pregunta almacenada
        pregunta = boveda.get("pregunta_seguridad", "Pregunta no disponible.")
        tk.Label(frm, text=pregunta,
                 bg=BG_PANEL, fg=ACCENT_GOLD, font=FONT_LABEL,
                 wraplength=410, justify="left").pack(anchor="w", pady=(0, 8))

        f_resp = NVEntry(frm, label="TU RESPUESTA",
                         acento=ACCENT_GOLD, ancho_px=410)
        f_resp.pack(fill="x")

        lbl_err = tk.Label(frm, text="", bg=BG_PANEL, fg=LOCK_RED,
                           font=FONT_FAINT, wraplength=410)
        lbl_err.pack(pady=(6, 0))

        def verificar():
            respuesta = f_resp.get().strip()
            if not respuesta:
                lbl_err.config(text="Ingresa tu respuesta.")
                return

            token = boveda.get("password_cifrada_con_respuesta", "")
            try:
                pw_descifrado = descifrar_password_con_respuesta(
                    token, respuesta, self._uid
                )
            except ValueError:
                # Respuesta incorrecta → bloqueo permanente
                try:
                    bloquear_boveda_permanente(self._uid, boveda["id"])
                except Exception:
                    pass
                boveda["boveda_inaccesible"] = True
                for b in self._bovedas:
                    if b["id"] == boveda["id"]:
                        b["boveda_inaccesible"] = True
                self._renderizar_lista_bovedas()
                top.destroy()
                messagebox.showerror(
                    "Bóveda inaccesible",
                    f"Respuesta incorrecta.\n\n"
                    f"«{boveda.get('nombre', '')}» ha sido bloqueada permanentemente.\n"
                    "Su contenido no puede recuperarse.",
                    parent=self._root,
                )
                return

            # Respuesta correcta → resetear bloqueo y abrir
            try:
                resetear_bloqueo_boveda(self._uid, boveda["id"])
            except Exception:
                pass
            boveda["intentos_password"] = 0
            boveda["boveda_bloqueada"]   = False
            for b in self._bovedas:
                if b["id"] == boveda["id"]:
                    b["intentos_password"] = 0
                    b["boveda_bloqueada"]   = False
            self._renderizar_lista_bovedas()

            top.destroy()
            self._desbloquear_boveda(boveda, pw_descifrado)

        NVButton(frm, texto="✔  VERIFICAR",
                 acento=ACCENT_GOLD, comando=verificar,
                 ancho=200, alto=34).pack(pady=(10, 0))

        f_resp._entry.bind("<Return>", lambda _: verificar())
        f_resp._entry.focus_set()

        top.wait_visibility()
        top.grab_set()

    def _desbloquear_boveda(self, boveda: dict, password: str) -> None:
        """Deriva la clave Fernet y activa la bóveda en el panel derecho."""
        self._fernet           = get_fernet_boveda(password, self._uid)
        self._boveda_sel       = boveda
        self._form_modo        = None
        self._entrada_editando = None
        self._lbl_boveda.config(
            text=f"⬡  {boveda.get('nombre', '')}",
            fg=ACCENT_CYAN,
        )
        self._btn_del_boveda.pack(side="right")
        self._cargar_entradas()

    # ══════════════════════════════════════════════════════════════════════
    #  HANDLERS — ENTRADAS
    # ══════════════════════════════════════════════════════════════════════

    def _cargar_entradas(self) -> None:
        if not self._boveda_sel:
            return
        try:
            self._entradas = cargar_entradas(self._uid, self._boveda_sel["id"])
        except Exception as exc:
            messagebox.showerror("NébulaVault",
                                 f"Error al cargar entradas:\n{exc}",
                                 parent=self._root)
            self._entradas = []
        self._renderizar_panel_boveda()

    def _on_guardar_entrada(self, correo: str, password: str, nota: str) -> None:
        """Cifra la contraseña y llama al servicio correspondiente."""
        if not self._boveda_sel:
            return
        try:
            pw_cifrada = cifrar(password, self._fernet) if password else ""
        except ValueError as exc:
            messagebox.showerror("NébulaVault", str(exc), parent=self._root)
            return

        bid = self._boveda_sel["id"]
        try:
            if self._form_modo == "editar_entrada" and self._entrada_editando:
                actualizado = actualizar_entrada(
                    self._uid, bid,
                    self._entrada_editando["id"],
                    correo, pw_cifrada, nota,
                )
                for i, e in enumerate(self._entradas):
                    if e["id"] == actualizado["id"]:
                        self._entradas[i].update(actualizado)
                        break
            else:
                nueva = crear_entrada(self._uid, bid, correo, pw_cifrada, nota)
                self._entradas.append(nueva)
                self._conteos[bid] = self._conteos.get(bid, 0) + 1
                self._renderizar_lista_bovedas()
        except Exception as exc:
            messagebox.showerror("NébulaVault",
                                 f"Error al guardar entrada:\n{exc}",
                                 parent=self._root)
            return

        self._form_modo        = None
        self._entrada_editando = None
        self._renderizar_panel_boveda()

    def _on_eliminar_entrada(self, entrada: dict) -> None:
        if not messagebox.askyesno(
            "Eliminar entrada",
            f"¿Eliminar la entrada «{entrada.get('correo', '')}»?",
            parent=self._root,
        ):
            return
        bid = self._boveda_sel["id"]
        try:
            eliminar_entrada(self._uid, bid, entrada["id"])
        except Exception as exc:
            messagebox.showerror("NébulaVault",
                                 f"Error al eliminar entrada:\n{exc}",
                                 parent=self._root)
            return
        self._entradas = [e for e in self._entradas if e["id"] != entrada["id"]]
        self._conteos[bid] = max(0, self._conteos.get(bid, 1) - 1)
        self._renderizar_lista_bovedas()
        self._renderizar_panel_boveda()

    def _abrir_form_nueva_entrada(self) -> None:
        self._form_modo        = "nueva_entrada"
        self._entrada_editando = None
        self._renderizar_panel_boveda()

    def _abrir_form_editar(self, entrada: dict) -> None:
        self._form_modo        = "editar_entrada"
        self._entrada_editando = entrada
        self._renderizar_panel_boveda()

    def _cancelar_form(self) -> None:
        self._form_modo        = None
        self._entrada_editando = None
        self._renderizar_panel_boveda()

    # ══════════════════════════════════════════════════════════════════════
    #  RENDERIZADO — LISTA DE BÓVEDAS (izquierda)
    # ══════════════════════════════════════════════════════════════════════

    def _renderizar_lista_bovedas(self) -> None:
        for w in self._inner_bovedas.winfo_children():
            w.destroy()

        if not self._bovedas:
            tk.Label(self._inner_bovedas,
                     text="Sin bóvedas.\nCrea la primera.",
                     bg=BG_PANEL, fg=TEXT_FAINT, font=FONT_FAINT,
                     justify="center").pack(pady=14, padx=8)
            return

        for b in self._bovedas:
            self._tarjeta_boveda(b)

    def _tarjeta_boveda(self, boveda: dict) -> None:
        inaccesible = boveda.get("boveda_inaccesible", False)
        bloqueada   = boveda.get("boveda_bloqueada",   False)
        es_sel      = bool(self._boveda_sel and
                           self._boveda_sel["id"] == boveda["id"])

        if inaccesible:
            bg    = BG_PANEL
            borde = LOCK_RED
            fg    = LOCK_RED
            icono = "⛔"
        elif bloqueada:
            bg    = BG_PANEL
            borde = ACCENT_GOLD
            fg    = ACCENT_GOLD
            icono = "🔒"
        else:
            bg    = BG_CARD    if es_sel else BG_PANEL
            borde = ACCENT_CYAN if es_sel else BORDER_DARK
            fg    = TEXT_MAIN  if es_sel else TEXT_MUTED
            icono = "⬡"

        card = tk.Frame(self._inner_bovedas, bg=bg,
                        highlightthickness=1, highlightbackground=borde,
                        cursor="hand2")
        card.pack(fill="x", padx=6, pady=3)

        row = tk.Frame(card, bg=bg)
        row.pack(fill="x", padx=8, pady=7)

        n   = self._conteos.get(boveda["id"], 0)
        sub = f"  ({n} {'entrada' if n == 1 else 'entradas'})"
        if inaccesible:
            sub = "  [INACCESIBLE]"
        elif bloqueada:
            sub = "  [BLOQUEADA]"

        lbl = tk.Label(row, text=f"{icono}  {boveda.get('nombre', '')}",
                       bg=bg, fg=fg, font=FONT_SUBTITLE, anchor="w")
        lbl.pack(side="left", fill="x", expand=True)
        tk.Label(row, text=sub, bg=bg, fg=fg if (inaccesible or bloqueada) else TEXT_FAINT,
                 font=FONT_FAINT).pack(side="right")

        def click(b=boveda):
            self._seleccionar_boveda(b)
            self._renderizar_lista_bovedas()

        for widget in (card, row, lbl):
            widget.bind("<Button-1>", lambda _e, b=boveda: click(b))

    # ══════════════════════════════════════════════════════════════════════
    #  RENDERIZADO — PANEL DERECHO (entradas + formulario)
    # ══════════════════════════════════════════════════════════════════════

    def _renderizar_panel_boveda(self) -> None:
        for w in self._content.winfo_children():
            w.destroy()

        if not self._boveda_sel:
            self._mostrar_placeholder()
            return

        # Canvas scrollable que envuelve todo el contenido derecho
        cv = tk.Canvas(self._content, bg=BG_PANEL, highlightthickness=0)
        sb = tk.Scrollbar(self._content, orient="vertical", command=cv.yview,
                          bg=BG_PANEL, troughcolor=BG_PANEL)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(cv, bg=BG_PANEL)
        cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<MouseWheel>",
                lambda e: cv.yview_scroll(-1 * (e.delta // 120), "units"))

        # Barra de acciones
        bar = tk.Frame(inner, bg=BG_PANEL)
        bar.pack(fill="x", padx=12, pady=(10, 6))
        NVButton(bar, texto="⊕  NUEVA ENTRADA",
                 acento=SUCCESS,
                 comando=self._abrir_form_nueva_entrada,
                 ancho=180, alto=30).pack(side="left")

        tk.Frame(inner, bg=BORDER_DARK, height=1).pack(fill="x", padx=12)

        # Formulario inline (al tope, si está activo)
        if self._form_modo in ("nueva_entrada", "editar_entrada"):
            self._construir_form_entrada(inner)
            tk.Frame(inner, bg=BORDER_DARK, height=1).pack(
                fill="x", padx=12, pady=(0, 4))

        # Lista de entradas
        if not self._entradas:
            tk.Label(inner,
                     text="Esta bóveda está vacía. Agrega tu primera entrada.",
                     bg=BG_PANEL, fg=TEXT_FAINT, font=FONT_FAINT
                     ).pack(pady=16, padx=12)
        else:
            for entrada in self._entradas:
                self._tarjeta_entrada(inner, entrada)

    def _tarjeta_entrada(self, parent: tk.Frame, entrada: dict) -> None:
        card = tk.Frame(parent, bg=BG_CARD,
                        highlightthickness=1, highlightbackground=BORDER_DARK)
        card.pack(fill="x", padx=12, pady=4)

        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill="x", padx=10, pady=8)

        # Columna izquierda: datos
        info = tk.Frame(row, bg=BG_CARD)
        info.pack(side="left", fill="x", expand=True)

        tk.Label(info, text=entrada.get("correo", "—"),
                 bg=BG_CARD, fg=ACCENT_CYAN, font=FONT_SUBTITLE,
                 anchor="w").pack(anchor="w")

        # Contraseña con toggle ver / ocultar
        pw_var     = tk.StringVar(value="••••••••")
        pw_visible = [False]
        pw_row     = tk.Frame(info, bg=BG_CARD)
        pw_row.pack(anchor="w", pady=(2, 0))

        tk.Label(pw_row, textvariable=pw_var,
                 bg=BG_CARD, fg=TEXT_MUTED, font=FONT_LABEL).pack(side="left")

        btn_ver = tk.Label(pw_row, text="[ ver ]", bg=BG_CARD,
                           fg=ACCENT_PURPLE, font=FONT_FAINT, cursor="hand2")
        btn_ver.pack(side="left", padx=(8, 0))

        def toggle(e=entrada, bv=btn_ver, pv=pw_var, vis=pw_visible):
            vis[0] = not vis[0]
            if vis[0]:
                try:
                    texto = descifrar(e.get("password", ""), self._fernet)
                    pv.set(texto or "(vacía)")
                except ValueError:
                    pv.set("[error al descifrar]")
                bv.config(text="[ ocultar ]")
            else:
                pv.set("••••••••")
                bv.config(text="[ ver ]")

        btn_ver.bind("<Button-1>", lambda _: toggle())

        nota = entrada.get("nota", "").strip()
        if nota:
            tk.Label(info, text=nota, bg=BG_CARD, fg=TEXT_FAINT,
                     font=FONT_FAINT, anchor="w",
                     wraplength=480, justify="left"
                     ).pack(anchor="w", pady=(3, 0))

        # Columna derecha: acciones contextuales
        acc = tk.Frame(row, bg=BG_CARD)
        acc.pack(side="right", padx=(10, 0))
        _SmallBtn(acc, "[ editar ]",   ACCENT_CYAN,
                  lambda e=entrada: self._abrir_form_editar(e)).pack(side="left", padx=2)
        _SmallBtn(acc, "[ eliminar ]", LOCK_RED,
                  lambda e=entrada: self._on_eliminar_entrada(e)).pack(side="left", padx=2)

    # ══════════════════════════════════════════════════════════════════════
    #  FORMULARIO INLINE — crear / editar entrada
    # ══════════════════════════════════════════════════════════════════════

    def _construir_form_entrada(self, parent: tk.Frame) -> None:
        es_edicion = self._form_modo == "editar_entrada"
        titulo     = "EDITAR ENTRADA"  if es_edicion else "NUEVA ENTRADA"
        acento     = ACCENT_GOLD       if es_edicion else SUCCESS

        card = tk.Frame(parent, bg=BG_CARD,
                        highlightthickness=1, highlightbackground=acento)
        card.pack(fill="x", padx=12, pady=(10, 4))

        inner = tk.Frame(card, bg=BG_CARD, padx=14, pady=12)
        inner.pack(fill="both")

        tk.Label(inner, text=titulo, bg=BG_CARD,
                 fg=acento, font=FONT_TITLE).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        f_correo = NVEntry(inner, label="CORREO / USUARIO",
                           acento=acento, ancho_px=260)
        f_correo.grid(row=1, column=0, padx=(0, 10), sticky="ew")

        f_pass = NVEntry(inner, label="CONTRASEÑA", show="•",
                         acento=acento, ancho_px=260)
        f_pass.grid(row=1, column=1, sticky="ew")

        f_nota = NVEntry(inner, label="NOTA  (opcional)",
                         acento=acento, ancho_px=540)
        f_nota.grid(row=2, column=0, columnspan=2, pady=(8, 0), sticky="ew")

        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=1)

        # Pre-cargar valores al editar
        if es_edicion and self._entrada_editando:
            e = self._entrada_editando
            f_correo.set(e.get("correo", ""))
            try:
                f_pass.set(descifrar(e.get("password", ""), self._fernet))
            except ValueError:
                f_pass.set("")
            f_nota.set(e.get("nota", ""))

        lbl_err = tk.Label(inner, text="", bg=BG_CARD,
                           fg=LOCK_RED, font=FONT_FAINT)
        lbl_err.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        btn_row = tk.Frame(inner, bg=BG_CARD)
        btn_row.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        def guardar():
            correo = f_correo.get().strip()
            if not correo:
                lbl_err.config(text="El campo correo/usuario es obligatorio.")
                return
            self._on_guardar_entrada(correo, f_pass.get(), f_nota.get().strip())

        NVButton(btn_row, texto="✔  GUARDAR",
                 acento=acento, comando=guardar,
                 ancho=140, alto=30).pack(side="left", padx=(0, 8))
        NVButton(btn_row, texto="✕  CANCELAR",
                 acento=TEXT_MUTED, comando=self._cancelar_form,
                 ancho=140, alto=30).pack(side="left")

        f_correo._entry.focus_set()

    # ══════════════════════════════════════════════════════════════════════
    #  PERFIL Y CIERRE DE SESIÓN
    # ══════════════════════════════════════════════════════════════════════

    def _abrir_perfil(self) -> None:
        """Oculta la bóveda, abre el perfil; al volver se restaura la bóveda."""
        self._root.withdraw()
        ProfileScreen(
            parent       = self._root,
            datos_usuario= self._datos,
            on_logout    = self._cerrar_sesion,
            on_volver    = self._root.deiconify,
        )

    def _cerrar_sesion(self) -> None:
        """
        Destruye la ventana de bóvedas y abre la pantalla de login.
        Sigue el mismo patrón que PantallaCloud._abrir_app_principal.
        """
        self._root.destroy()
        import tkinter as _tk
        from views.cloud import PantallaCloud
        nuevo_root = _tk.Tk()
        PantallaCloud(nuevo_root)
        nuevo_root.mainloop()
