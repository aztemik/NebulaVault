"""
pantalla_nube.py
════════════════════════════════════════════════════════════════════════════════
NébulaVault — Pantalla de Autenticación (Modo Cloud)
Estética: dark cybersecurity / cósmico-industrial  ·  Paleta NébulaVault

Librerías añadidas respecto al proyecto base:
  • requests  → llamadas a Firebase Auth REST API (login, verificación email)
  • os        → leer variables de entorno (FIREBASE_API_KEY, FIREBASE_CREDENTIALS)
════════════════════════════════════════════════════════════════════════════════
"""

from pathlib import Path
import math
import os
import time
import tkinter as tk
from tkinter import ttk, messagebox

import requests
import firebase_admin
from firebase_admin import credentials, firestore, auth
from .firebaseLogic import AuthFire

from .legalTexts import WelcomeScreen

from .bovedaScreen import BovedaScreen
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

FONT_DISPLAY   = ("Courier New", 22, "bold")
FONT_SUBTITLE  = ("Courier New", 10, "bold")
FONT_LABEL     = ("Courier New",  9, "normal")
FONT_FAINT     = ("Courier New",  8, "normal")
FONT_BTN       = ("Courier New", 10, "bold")
FONT_INPUT     = ("Courier New", 10, "normal")
FONT_LINK      = ("Courier New",  9, "underline")


# ═════════════════════════════════════════════════════════════════════════════
#  HELPERS DE DIBUJO (paleta NébulaVault)
# ═════════════════════════════════════════════════════════════════════════════

def _hex_grid(canvas: tk.Canvas, w: int, h: int) -> None:
    r = HEX_SPACING / 2
    hh = r * math.sqrt(3)
    col, x = 0, r
    while x < w + r:
        offset_y = hh if col % 2 else 0
        y = offset_y
        while y < h + hh:
            pts = []
            for i in range(6):
                a = math.radians(60 * i - 30)
                pts += [x + r * 0.72 * math.cos(a), y + r * 0.72 * math.sin(a)]
            canvas.create_polygon(pts, outline=HEX_GRID_COLOR, fill="", width=1)
            y += hh * 2
        x += hh * 1.5
        col += 1


def _esquinas_L(canvas: tk.Canvas, w: int, h: int,
                tam: int = 30, color: str = ACCENT_CYAN, g: int = 2) -> None:
    m = 14
    defs = [(m, m, 1, 1), (w - m, m, -1, 1),
            (m, h - m, 1, -1), (w - m, h - m, -1, -1)]
    for px, py, dx, dy in defs:
        canvas.create_line(px, py, px + dx * tam, py,          fill=color, width=g)
        canvas.create_line(px, py, px,             py + dy * tam, fill=color, width=g)


def _sep(canvas: tk.Canvas, cx: int, y: int,
         mitad: int = 200, color: str = BORDER_DARK) -> None:
    canvas.create_line(cx - mitad, y, cx + mitad, y, fill=color, width=1)


# ═════════════════════════════════════════════════════════════════════════════
#  WIDGET NVEntry — campo de texto estilizado
# ═════════════════════════════════════════════════════════════════════════════

class NVEntry(tk.Frame):
    """
    Campo de entrada estilizado con etiqueta, borde de acento y efecto
    focus. Soporta modo contraseña (show="•").
    """

    def __init__(self, parent, label: str, placeholder: str = "",
                 show: str = "", acento: str = ACCENT_CYAN,
                 ancho_px: int = 340, **kw):
        super().__init__(parent, bg=BG_VOID, **kw)
        self._acento = acento

        # Etiqueta
        tk.Label(self, text=label, bg=BG_VOID, fg=TEXT_MUTED,
                 font=FONT_LABEL).pack(anchor="w", padx=2, pady=(0, 2))

        # Marco del campo
        self._marco = tk.Frame(self, bg=BORDER_DARK,
                               highlightthickness=0, padx=1, pady=1)
        self._marco.pack(fill="x")

        # Entry
        char_w = max(1, ancho_px // 8)   # aproximación para `width` en chars
        self._var = tk.StringVar()
        self._entry = tk.Entry(
            self._marco,
            textvariable=self._var,
            show=show,
            bg=BG_PANEL,
            fg=TEXT_MAIN,
            insertbackground=acento,
            relief="flat",
            font=FONT_INPUT,
            width=char_w,
            bd=4,
        )
        self._entry.pack(fill="x")

        # Barra de acento inferior (1 px)
        self._barra = tk.Frame(self, bg=BORDER_DARK, height=1)
        self._barra.pack(fill="x")

        # Placeholder
        if placeholder:
            self._entry.insert(0, placeholder)
            self._entry.config(fg=TEXT_FAINT)
            self._entry.bind("<FocusIn>",  lambda _: self._clear_ph(placeholder))
            self._entry.bind("<FocusOut>", lambda _: self._restore_ph(placeholder))

        self._entry.bind("<FocusIn>",  lambda _: self._on_focus(), add="+")
        self._entry.bind("<FocusOut>", lambda _: self._on_blur(),  add="+")

    # ── Placeholder ──────────────────────────────────────────────────────────

    def _clear_ph(self, ph: str) -> None:
        if self._entry.get() == ph:
            self._entry.delete(0, "end")
            self._entry.config(fg=TEXT_MAIN)

    def _restore_ph(self, ph: str) -> None:
        if not self._entry.get():
            self._entry.insert(0, ph)
            self._entry.config(fg=TEXT_FAINT)

    # ── Focus ────────────────────────────────────────────────────────────────

    def _on_focus(self) -> None:
        self._marco.config(bg=self._acento)
        self._barra.config(bg=self._acento)

    def _on_blur(self) -> None:
        self._marco.config(bg=BORDER_DARK)
        self._barra.config(bg=BORDER_DARK)

    # ── API pública ──────────────────────────────────────────────────────────

    def get(self) -> str:
        return self._var.get()

    def limpiar(self) -> None:
        self._var.set("")

    def bind_enter(self, callback) -> None:
        self._entry.bind("<Return>", lambda _: callback())


# ═════════════════════════════════════════════════════════════════════════════
#  WIDGET NVButton — botón canvas estilizado
# ═════════════════════════════════════════════════════════════════════════════

class NVButton(tk.Canvas):
    """Botón canvas con hover, borde de acento y esquinas en L."""

    def __init__(self, parent, texto: str, acento: str = ACCENT_CYAN,
                 comando=None, ancho: int = 200, alto: int = 42, **kw):
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
        self.create_rectangle(1, 1, w - 1, h - 1, fill=bg, outline=self._acento, width=1)
        t = 7
        for px, py, dx, dy in [(2, 2, 1, 1), (w-2, 2, -1, 1),
                                (2, h-2, 1, -1), (w-2, h-2, -1, -1)]:
            self.create_line(px, py, px + dx*t, py,          fill=self._acento, width=1)
            self.create_line(px, py, px,         py + dy*t,  fill=self._acento, width=1)
        self.create_text(w//2, h//2, text=self._texto,
                         fill=TEXT_MAIN, font=FONT_BTN, anchor="center")

    def _set_hover(self, v: bool) -> None:
        self._hover = v
        self._render()

    def set_loading(self, estado: bool) -> None:
        """Cambia el texto a '…' durante operaciones async."""
        self._texto = "PROCESANDO…" if estado else self._texto
        self._render()


# ═════════════════════════════════════════════════════════════════════════════
#  PANTALLA CLOUD — Login + Registro
# ═════════════════════════════════════════════════════════════════════════════

class PantallaCloud:
    """
    Pantalla de autenticación para el modo En la Nube.

    ┌──────────────────────────────────────┐
    │  ◈ NÉBULAVAULT  ·  CLOUD AUTH        │
    │  ─────────────────────────────────── │
    │  [ Email              ]              │
    │  [ Contraseña         ]              │
    │           [ INICIAR SESIÓN ]         │
    │  ─────────────────────────────────── │
    │  ¿No tienes cuenta?  [ REGISTRARSE ] │
    └──────────────────────────────────────┘

    Al pulsar REGISTRARSE el panel inferior se expande con los campos
    de nombre + email + contraseña del nuevo usuario.
    """

    ANCHO = 560
    ALTO_LOGIN  = 500
    ALTO_TOTAL  = 850   # con el panel de registro visible

    def __init__(self, root: tk.Tk) -> None:
        self.root          = root
        self._modo         = "login"   # "login" | "registro"
        self._id_token_sesion: str | None = None   # token tras login exitoso

        self._configurar_ventana()
        self._construir()

    # ── Configuración ────────────────────────────────────────────────────────

    def _configurar_ventana(self) -> None:
        self.root.title("NébulaVault — Autenticación Cloud")
        self.root.configure(bg=BG_VOID)
        self.root.resizable(False, False)
        self._centrar(self.ANCHO, self.ALTO_LOGIN)

    def _centrar(self, w: int, h: int) -> None:
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── Construcción UI ──────────────────────────────────────────────────────

    def _construir(self) -> None:
        # Limpia widgets anteriores (al redimensionar)
        for w in self.root.winfo_children():
            w.destroy()

        alto = self.ALTO_TOTAL if self._modo == "registro" else self.ALTO_LOGIN
        self._centrar(self.ANCHO, alto)

        cw = self.ANCHO

        # ── Canvas decorativo de fondo ────────────────────────────────────
        self._bg = tk.Canvas(self.root, width=cw, height=alto,
                             bg=BG_VOID, highlightthickness=0)
        self._bg.place(x=0, y=0)
        _hex_grid(self._bg, cw, alto)
        _esquinas_L(self._bg, cw, alto)

        # Barra lateral izquierda
        self._bg.create_line(10, 50, 10, alto - 50,
                             fill=ACCENT_PURPLE, width=3)
        self._bg.create_line(14, 50, 14, alto - 50,
                             fill=CYAN_20, width=1)

        # Barra inferior
        self._bg.create_line(14, alto - 14, cw - 14, alto - 14,
                             fill=ACCENT_PURPLE, width=2)

        # ── Encabezado ────────────────────────────────────────────────────
        self._bg.create_text(cw//2, 44,
                             text="◈  NÉBULAVAULT  ·  CLOUD AUTH",
                             fill=ACCENT_PURPLE, font=FONT_DISPLAY, anchor="center")
        self._bg.create_text(cw//2, 68,
                             text="AUTENTICACIÓN SEGURA EN LA NUBE",
                             fill=TEXT_MUTED, font=FONT_FAINT, anchor="center")

        # Separador bajo header
        _sep(self._bg, cw//2, 84, mitad=230, color=ACCENT_PURPLE)

        # ── Etiqueta LOGIN ────────────────────────────────────────────────
        self._bg.create_text(cw//2, 104,
                             text="INICIAR SESIÓN",
                             fill=ACCENT_CYAN, font=FONT_SUBTITLE, anchor="center")

        # ── Formulario LOGIN ──────────────────────────────────────────────
        px = cw//2 - 170   # x de padding del formulario

        self._f_email = NVEntry(self.root, label="CORREO ELECTRÓNICO",
                                placeholder="usuario@dominio.com",
                                acento=ACCENT_CYAN, ancho_px=340)
        self._f_email.place(x=px, y=120)

        self._f_pass = NVEntry(self.root, label="CONTRASEÑA",
                               placeholder="••••••••",
                               show="•", acento=ACCENT_CYAN, ancho_px=340)
        self._f_pass.place(x=px, y=188)
        self._f_pass.bind_enter(self._hacer_login)

        # Mensaje de estado (error / éxito)
        self._lbl_status = tk.Label(
            self.root, text="", bg=BG_VOID,
            font=FONT_LABEL, fg=LOCK_RED, wraplength=340, justify="center"
        )
        self._lbl_status.place(x=px, y=260, width=340)

        # Botón LOGIN
        self._btn_login = NVButton(
            self.root, texto="→  INICIAR SESIÓN",
            acento=ACCENT_CYAN, comando=self._hacer_login,
            ancho=340, alto=42
        )
        self._btn_login.place(x=px, y=288)

        # ── Separador + sección Registro ─────────────────────────────────
        _sep(self._bg, cw//2, 356, mitad=230, color=BORDER_DARK)

        self._bg.create_text(cw//2, 374,
                             text="¿No tienes cuenta?",
                             fill=TEXT_MUTED, font=FONT_LABEL, anchor="center")

        lbl_toggle_txt = (
            "▾  OCULTAR REGISTRO" if self._modo == "registro"
            else "▸  CREAR NUEVA CUENTA"
        )
        lbl_toggle_color = ACCENT_GLOW

        self._btn_toggle = tk.Label(
            self.root,
            text=lbl_toggle_txt,
            bg=BG_VOID,
            fg=lbl_toggle_color,
            font=FONT_LINK,
            cursor="hand2",
        )
        self._btn_toggle.place(x=cw//2 - 75, y=392)
        self._btn_toggle.bind("<Button-1>", lambda _: self._toggle_registro())
        self._btn_toggle.bind("<Enter>",
                              lambda _: self._btn_toggle.config(fg=ACCENT_CYAN))
        self._btn_toggle.bind("<Leave>",
                              lambda _: self._btn_toggle.config(fg=lbl_toggle_color))

        # ── Panel de REGISTRO (sólo si modo == "registro") ────────────────
        if self._modo == "registro":
            self._construir_panel_registro(px, y_inicio=430)

        # ── Footer ────────────────────────────────────────────────────────
        self._bg.create_text(cw//2, alto - 26,
                             text="v1.0.0  //  CLOUD SECURE AUTH  //  CONFIDENTIAL",
                             fill=TEXT_FAINT, font=FONT_FAINT, anchor="center")

        # Dot estado
        dot_color = SUCCESS if self._modo == "login" else ACCENT_PURPLE
        self._bg.create_oval(cw - 42, alto - 34, cw - 30, alto - 22,
                             fill=dot_color, outline="")

    def _construir_panel_registro(self, px: int, y_inicio: int) -> None:
        """Agrega los campos y botón de registro al panel expandido."""
        cw = self.ANCHO

        # Cabecera sección
        self._bg.create_text(cw//2, y_inicio,
                             text="NUEVA CUENTA",
                             fill=ACCENT_PURPLE, font=FONT_SUBTITLE, anchor="center")
        _sep(self._bg, cw//2, y_inicio + 14, mitad=230, color=ACCENT_PURPLE)

        self._r_nombre = NVEntry(self.root, label="NOMBRE COMPLETO",
                                 placeholder="Tu nombre",
                                 acento=ACCENT_PURPLE, ancho_px=340)
        self._r_nombre.place(x=px, y=y_inicio + 26)

        self._r_email = NVEntry(self.root, label="CORREO ELECTRÓNICO",
                                placeholder="nuevo@dominio.com",
                                acento=ACCENT_PURPLE, ancho_px=340)
        self._r_email.place(x=px, y=y_inicio + 94)

        self._r_pass = NVEntry(self.root, label="CONTRASEÑA  (mín. 6 caracteres)",
                               placeholder="••••••••",
                               show="•", acento=ACCENT_PURPLE, ancho_px=340)
        self._r_pass.place(x=px, y=y_inicio + 158)
        self._r_pass.bind_enter(self._hacer_registro)

        # Mensaje estado registro
        self._lbl_r_status = tk.Label(
            self.root, text="", bg=BG_VOID,
            font=FONT_LABEL, fg=LOCK_RED, wraplength=340, justify="center"
        )
        self._lbl_r_status.place(x=px, y=y_inicio + 255, width=340)  # era 230

        # Botón REGISTRO
        self._btn_registro = NVButton(
            self.root, texto="◈  CREAR CUENTA",
            acento=ACCENT_PURPLE, comando=self._hacer_registro,
            ancho=340, alto=42
        )
        self._btn_registro.place(x=px, y=y_inicio + 300)  # era 252

        # Nota verificación
        self._bg.create_text(cw//2, y_inicio + 310,
                             text="Se enviará un correo de verificación al registrarte.",
                             fill=TEXT_FAINT, font=FONT_FAINT, anchor="center")

    # ── Interacción ──────────────────────────────────────────────────────────

    def _toggle_registro(self) -> None:
        """Alterna la visibilidad del panel de registro."""
        self._modo = "registro" if self._modo == "login" else "login"
        self._construir()

    def _set_status(self, msg: str, color: str = LOCK_RED,
                    registro: bool = False) -> None:
        """Actualiza el label de estado del formulario correspondiente."""
        if registro and hasattr(self, "_lbl_r_status"):
            self._lbl_r_status.config(text=msg, fg=color)
        else:
            self._lbl_status.config(text=msg, fg=color)

    # ── Acciones Firebase ────────────────────────────────────────────────────

    def _hacer_login(self) -> None:
        """
        Valida los campos y llama a login_con_email().
        En caso de éxito llama a on_login_exitoso().
        """
        email    = self._f_email.get().strip()
        password = self._f_pass.get()

        # Validación básica en cliente
        if not email or "@" not in email:
            self._set_status("Ingresa un correo válido.")
            return
        if len(password) < 6:
            self._set_status("La contraseña debe tener al menos 6 caracteres.")
            return

        self._set_status("")
        self._btn_login.set_loading(True)
        self.root.update_idletasks()

        try:
            datos = AuthFire.login_con_email(email, password)
            self._id_token_sesion = datos.get("idToken")
            self._set_status("✔  Acceso concedido.", color=SUCCESS)
            # Pequeña pausa visual antes de navegar
            self.root.after(700, lambda: self.on_login_exitoso(datos))

        except RuntimeError as exc:
            self._set_status(str(exc))
        except requests.exceptions.ConnectionError:
            self._set_status("Sin conexión a internet. Verifica tu red.")
        except Exception as exc:
            self._set_status(f"Error inesperado: {exc}")
        finally:
            self._btn_login.set_loading(False)

    def _hacer_registro(self) -> None:
        nombre   = self._r_nombre.get().strip()
        email    = self._r_email.get().strip()
        password = self._r_pass.get()

        if not nombre:
            self._set_status("Ingresa tu nombre completo.", registro=True)
            return
        if not email or "@" not in email:
            self._set_status("Ingresa un correo válido.", registro=True)
            return
        if len(password) < 6:                          # ← validación local, nunca llega al SDK
            self._set_status("La contraseña debe tener al menos 6 caracteres.", registro=True)
            return
        
        self._set_status("", registro=True)
        self._btn_registro.set_loading(True)
        self.root.update_idletasks()

        try:
            datos = AuthFire.registrar_usuario(nombre, email, password)

            # Obtener idToken para enviar verificación (login inmediato post-registro)
            datos_login = AuthFire.login_con_email(email, password)
            id_token    = datos_login.get("idToken")

            # Enviar correo de verificación (función stub lista para implementar)
            AuthFire.enviar_correo_verificacion(id_token)

            self._set_status(
                "✔  Cuenta creada. Revisa tu correo para verificarla.",
                color=SUCCESS, registro=True
            )
            # Volver al modo login tras breve pausa
            self.root.after(4000, lambda: self._volver_a_login(email))

        except RuntimeError as exc:
            self._set_status(str(exc), registro=True)
        except requests.exceptions.ConnectionError:
            self._set_status("Sin conexión a internet.", registro=True)
        except Exception as exc:
            self._set_status(f"Error inesperado: {exc}", registro=True)
        finally:
            self._btn_registro.set_loading(False)

    def _volver_a_login(self, email_prellenado: str = "") -> None:
        """Regresa al modo login y prelena el email si se recibe."""
        self._modo = "login"
        self._construir()
        if email_prellenado:
            self._f_email.limpiar()
            self._f_email._entry.insert(0, email_prellenado)
            self._f_email._entry.config(fg=TEXT_MAIN)

    # ── Callback de navegación ────────────────────────────────────────────────
 
    def on_login_exitoso(self, datos_usuario: dict) -> None:
        """
        Llamado cuando Firebase confirma el login.
 
        Flujo:
          1. Extrae el uid del dict de Firebase.
          2. Consulta Firestore: ¿ya aceptó los términos vigentes?
             · Sí → navega directo a la pantalla principal.
             · No → muestra WelcomeScreen para que los acepte.
          3. Si la consulta falla por red, permite continuar con aviso
             (decisión de UX; cambia a `return` si prefieres bloquear).
        """
        uid = datos_usuario.get("localId", "")
 
        try:
            ya_acepto = AuthFire.verificar_aceptacion_terminos(uid)
        except Exception as exc:
            # Error de red o Firestore: mostrar aviso pero dejar pasar
            messagebox.showwarning(
                "NébulaVault",
                f"No se pudo verificar el estado de los términos:\n{exc}\n\n"
                "Continuando de todas formas.",
                parent=self.root,
            )
            ya_acepto = False   # fuerza mostrar términos en caso de duda
 
        if ya_acepto:
            self._abrir_app_principal(datos_usuario)
        else:
            self._mostrar_terminos(datos_usuario)
 
    # ── Términos de uso ───────────────────────────────────────────────────────
 
    def _mostrar_terminos(self, datos_usuario: dict) -> None:
        """
        Oculta la ventana de login y lanza WelcomeScreen.
        WelcomeScreen es una tk.Tk independiente; cuando termina
        (aceptación o rechazo) llama a los callbacks definidos abajo.
        """
        uid = datos_usuario.get("localId", "")
 
        # Ocultar (no destruir) la ventana de login mientras se muestran
        # los términos.  Se destruirá una vez el usuario acepte/rechace.
        self.root.withdraw()
 
        pantalla_terms = WelcomeScreen(
            uid        = uid,
            on_accepted= lambda: self._tras_aceptar_terminos(datos_usuario),
            on_declined= lambda: self._on_rechazo_terminos(),
        )
        pantalla_terms.mainloop()
 
    def _tras_aceptar_terminos(self, datos_usuario: dict) -> None:
        """
        Ejecutado después de que WelcomeScreen llama a on_accepted
        (la aceptación ya quedó guardada en Firestore por WelcomeScreen).
        La ventana de login se destruye dentro de _abrir_app_principal.
        """
        self._abrir_app_principal(datos_usuario)

    def _on_rechazo_terminos(self) -> None:
        """
        Ejecutado si el usuario rechaza los términos en WelcomeScreen.
        Vuelve a mostrar la ventana de login con un aviso informativo.
        """
        self.root.deiconify()   # recuperar ventana de login
        self._set_status(
            "⚠  Debes aceptar los documentos legales para usar NébulaVault.",
            color=LOCK_RED,
        )
        # Limpiar la contraseña por seguridad
        self._f_pass.limpiar()

    # ── Navegación a la pantalla principal ───────────────────────────────────

    def _abrir_app_principal(self, datos_usuario: dict) -> None:
        """Destruye la ventana de login y abre la pantalla de bóvedas."""
        self.root.destroy()
        BovedaScreen(datos_usuario)
 


