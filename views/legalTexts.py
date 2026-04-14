"""
NebulaVault — Pantalla de Bienvenida y Consentimiento
Diseño: oscuro-cósmico, identidad visual de seguridad premium.
"""

from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import math
import time
from .firebaseLogic import AuthFire


# ─────────────────────────── PALETA ────────────────────────────
BG_VOID       = "#07090f"   # fondo profundo
BG_PANEL      = "#0d1117"   # paneles
BG_CARD       = "#111827"   # tarjetas
BORDER_DARK   = "#1e2939"   # bordes sutiles
BORDER_ACCENT = "#0ea5e9"   # borde activo
ACCENT_CYAN   = "#38bdf8"   # cian principal
ACCENT_GLOW   = "#7dd3fc"   # cyan claro
ACCENT_PURPLE = "#818cf8"   # índigo
ACCENT_GOLD   = "#fbbf24"   # dorado
TEXT_MAIN     = "#e2e8f0"   # texto principal
TEXT_MUTED    = "#64748b"   # texto atenuado
TEXT_FAINT    = "#334155"   # muy tenue
BTN_ACTIVE    = "#0369a1"   # botón activo
BTN_HOVER     = "#0284c7"   # botón hover
BTN_DISABLED  = "#1e2939"   # botón desactivado
SUCCESS       = "#34d399"   # verde confirmación
LOCK_RED      = "#f87171"   # rojo bloqueo


def blend(hex_color: str, alpha: float, bg: str = BG_VOID) -> str:
    """Mezcla hex_color con bg según alpha (0.0‥1.0) → color RGB sólido."""
    def _p(h):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    fr, fg, fb = _p(hex_color)
    br, bg_, bb = _p(bg)
    r = int(fr * alpha + br * (1 - alpha))
    g = int(fg * alpha + bg_ * (1 - alpha))
    b = int(fb * alpha + bb * (1 - alpha))
    return f"#{r:02x}{g:02x}{b:02x}"


# Pre-calculados para reutilizar
CYAN_05  = blend(ACCENT_CYAN, 0.05)
CYAN_13  = blend(ACCENT_CYAN, 0.13)
CYAN_20  = blend(ACCENT_CYAN, 0.20)
CYAN_27  = blend(ACCENT_CYAN, 0.27)
CYAN_33  = blend(ACCENT_CYAN, 0.33)
CYAN_53  = blend(ACCENT_CYAN, 0.53)
CYAN_80  = blend(ACCENT_CYAN, 0.80)


LEGAL_TEXTS = {
    "Términos de uso": (
        "TÉRMINOS DE USO\n"
        "Al instalar, abrir o utilizar NébulaVault (la \"Aplicación\"), el usuario acepta estos Términos de uso. "
        "Si no está de acuerdo, debe abstenerse de utilizar la Aplicación.\n\n"
        "1) Uso permitido\n"
        "La Aplicación está destinada a la administración local de credenciales y datos asociados. El usuario "
        "se compromete a usarla de forma lícita y conforme a estos Términos.\n\n"
        "2) Seguridad y responsabilidad del usuario\n"
        "La protección de la bóveda depende de la contraseña maestra y del control del dispositivo. El usuario "
        "acepta:\n"
        "• Definir una contraseña maestra robusta y no compartirla.\n"
        "• Proteger su equipo (bloqueo de sesión, actualizaciones, antivirus/antimalware cuando corresponda).\n"
        "• Comprender que el acceso al equipo por terceros, malware o copias no controladas puede comprometer datos.\n\n"
        "3) Propiedad intelectual\n"
        "La Aplicación, sus componentes, marca, diseño, textos y materiales asociados son propiedad de Nébula Security "
        "o se usan bajo licencias aplicables. Se prohíbe copiar, modificar, redistribuir o explotar comercialmente "
        "la Aplicación sin autorización.\n\n"
        "4) Restricciones\n"
        "Queda prohibido:\n"
        "• Usar la Aplicación para actividades ilícitas o para vulnerar derechos de terceros.\n"
        "• Intentar eludir medidas de seguridad, manipular la bóveda o acceder a datos sin autorización.\n"
        "• Descompilar, realizar ingeniería inversa o alterar la Aplicación cuando lo prohíba la legislación aplicable.\n\n"
        "5) Respaldo y disponibilidad\n"
        "El usuario es responsable de administrar sus respaldos si decide realizarlos. La Aplicación puede depender "
        "del entorno del sistema (permisos, rutas, almacenamiento). Nébula Security no garantiza recuperación de datos "
        "por fallos del equipo, eliminación accidental o configuraciones del usuario.\n\n"
        "6) Exclusión de garantías\n"
        "La Aplicación se proporciona \"tal cual\" (as-is), sin garantías expresas de comerciabilidad, idoneidad para "
        "un propósito particular o ausencia total de errores, en la medida permitida por la legislación aplicable.\n\n"
        "7) Limitación de responsabilidad\n"
        "En la medida permitida por la legislación aplicable, Nébula Security no será responsable por daños directos o "
        "indirectos derivados del uso o imposibilidad de uso de la Aplicación, incluyendo pérdida de datos por causas "
        "externas (fallos del sistema, accesos no autorizados al equipo, malware, respaldos inseguros o errores del usuario).\n\n"
        "8) Cambios a los Términos\n"
        "Estos Términos pueden actualizarse. La versión vigente estará disponible dentro de la Aplicación.\n\n"
        "Última actualización: 6 de febrero de 2026."
    ),
    "Aviso de privacidad": (
        "AVISO DE PRIVACIDAD\n"
        "Nébula Security (\"Nébula Security\") pone a disposición la aplicación de escritorio "
        "NébulaVault (la \"Aplicación\"). Este Aviso de privacidad describe cómo se tratan los datos "
        "cuando el usuario utiliza la Aplicación.\n\n"
        "1) Responsable y alcance\n"
        "Nébula Security es responsable del tratamiento de la información que el usuario capture "
        "dentro de la Aplicación. El tratamiento se realiza de forma local en el equipo del usuario.\n\n"
        "2) Información tratada\n"
        "La Aplicación permite al usuario almacenar información asociada a entradas de bóveda, "
        "como: nombre del servicio/sitio, usuario, contraseña, notas, etiquetas y otros campos "
        "definidos por el usuario (en conjunto, \"Datos de la bóveda\").\n\n"
        "3) Finalidades\n"
        "Los Datos de la bóveda se tratan exclusivamente para:\n"
        "• Permitir la creación, apertura y administración de una bóveda local.\n"
        "• Mostrar, organizar, buscar, editar y eliminar entradas de credenciales.\n"
        "• Mantener la integridad de la información mediante controles locales de la Aplicación.\n\n"
        "4) Operación local y ausencia de transmisión\n"
        "La Aplicación opera localmente y, por diseño:\n"
        "• No recopila datos de forma automática para enviarlos a terceros.\n"
        "• No transmite los Datos de la bóveda por internet.\n"
        "• No se integra con servicios en la nube ni con servidores externos para almacenar la bóveda.\n\n"
        "5) Almacenamiento y medidas de protección\n"
        "La bóveda se almacena en el dispositivo del usuario. Para protegerla, la Aplicación utiliza "
        "mecanismos de seguridad locales, incluyendo el uso de una contraseña maestra definida por el "
        "usuario y el cifrado del contenido de la bóveda, de modo que el acceso a los datos requiera "
        "la autenticación correspondiente.\n\n"
        "6) Conservación y eliminación\n"
        "Los datos se conservan mientras la bóveda exista en el equipo del usuario. El usuario puede "
        "eliminar información borrando entradas desde la Aplicación o eliminando la bóveda. La "
        "desinstalación de la Aplicación no garantiza, por sí sola, la eliminación de archivos de datos "
        "si estos se encuentran en ubicaciones externas o respaldos del sistema.\n\n"
        "7) Control del usuario\n"
        "El usuario mantiene control sobre sus datos mediante las funciones de administración de la "
        "bóveda (crear, abrir, editar, exportar si aplica, y eliminar). La seguridad final también "
        "depende de las prácticas del usuario (contraseña maestra robusta, bloqueo del equipo, "
        "actualizaciones del sistema, y protección contra malware).\n\n"
        "8) Cambios a este Aviso\n"
        "Nébula Security podrá actualizar este Aviso para reflejar cambios operativos o normativos. "
        "La versión vigente estará disponible dentro de la Aplicación.\n\n"
        "Última actualización: 6 de febrero de 2026."
    ),
    "Acuerdo de confidencialidad": (
        "ACUERDO DE CONFIDENCIALIDAD\n"
        "Este Acuerdo de Confidencialidad (\"Acuerdo\") aplica a personas que acceden a NébulaVault "
        "en contextos de evaluación, revisión, demostración o pruebas controladas, cuando Nébula Security "
        "lo requiera como condición de acceso.\n\n"
        "1) Información Confidencial\n"
        "Se considera \"Información Confidencial\" toda información no pública relacionada con:\n"
        "• La Aplicación, su diseño, interfaz, flujos, textos, identidad visual y documentación.\n"
        "• Especificaciones, arquitectura, modelos, decisiones técnicas, material interno y know-how.\n"
        "• Material compartido por Nébula Security para evaluación (builds, enlaces privados, manuales, "
        "capturas, diagramas, archivos, credenciales de prueba o procedimientos).\n\n"
        "2) Obligaciones\n"
        "La persona evaluadora se obliga a:\n"
        "• Usar la Información Confidencial únicamente para el propósito autorizado.\n"
        "• No divulgar, publicar, distribuir o poner a disposición de terceros la Información Confidencial.\n"
        "• Proteger la Información Confidencial con medidas razonables para evitar accesos no autorizados.\n\n"
        "3) Restricciones\n"
        "Salvo autorización expresa por escrito de Nébula Security, queda prohibido:\n"
        "• Compartir públicamente capturas, grabaciones, binarios, materiales o documentación no pública.\n"
        "• Realizar ingeniería inversa o descompilación con fines de publicación o explotación no autorizada.\n"
        "• Usar marca, nombres, logotipos o materiales de la Aplicación para fines ajenos al propósito autorizado.\n\n"
        "4) Divulgación responsable\n"
        "Si se detectan fallos, errores o vulnerabilidades, la persona evaluadora se compromete a "
        "reportarlos de forma responsable a Nébula Security y a no divulgarlos públicamente hasta recibir "
        "instrucciones o autorización.\n\n"
        "5) Exclusiones\n"
        "No será Información Confidencial aquella que:\n"
        "• Sea pública sin incumplimiento de este Acuerdo.\n"
        "• Haya sido obtenida legítimamente de un tercero sin obligación de confidencialidad.\n\n"
        "6) Vigencia\n"
        "Las obligaciones de confidencialidad se mantienen durante el acceso y continúan respecto de la "
        "Información Confidencial a la que se haya tenido acceso.\n\n"
        "Última actualización: 6 de febrero de 2026."
    ),
}

SECTION_ICONS  = ["📋", "🔒", "🤝"]
SECTION_COLORS = [ACCENT_CYAN, ACCENT_PURPLE, ACCENT_GOLD]


# ══════════════════════════════════════════════════════════════════════
#  UTILIDADES CANVAS
# ══════════════════════════════════════════════════════════════════════

def draw_hex_grid(canvas, w, h, spacing=52, color="#0f1820", line_w=1):
    """Dibuja una cuadrícula hexagonal decorativa de fondo."""
    r = spacing / 2
    dx = spacing * 1.5
    dy = spacing * math.sqrt(3) / 2
    col = 0
    x = -spacing
    while x < w + spacing:
        row = 0
        y_off = (dy if col % 2 else 0) - spacing
        y = y_off
        while y < h + spacing:
            pts = []
            for i in range(6):
                angle = math.radians(60 * i - 30)
                pts += [x + r * math.cos(angle), y + r * math.sin(angle)]
            canvas.create_polygon(pts, outline=color, fill="", width=line_w)
            y += dy * 2
            row += 1
        x += dx
        col += 1


def draw_glow_circle(canvas, cx, cy, r, color, steps=8):
    """Círculo con aura difuminada (aros concéntricos decrecientes)."""
    for i in range(steps, 0, -1):
        alpha_hex = format(int(255 * (i / steps) * 0.18), "02x")
        shade = color + alpha_hex if len(color) == 7 else color
        # tkinter no soporta rgba; simulamos con colores del mismo tono
        ratio = i / steps
        canvas.create_oval(
            cx - r * ratio, cy - r * ratio,
            cx + r * ratio, cy + r * ratio,
            outline=color, fill="", width=max(1, int(2 * ratio))
        )


# ══════════════════════════════════════════════════════════════════════
#  WIDGET: SECCIÓN LEGAL CON SCROLL
# ══════════════════════════════════════════════════════════════════════

class LegalSection(tk.Frame):
    """
    Una tarjeta con título, icono, área de texto con scroll vertical
    y un indicador de progreso de lectura.  Se desbloquea la siguiente
    sección cuando el usuario llega al final del scroll.
    """

    
    def __init__(self, master, title, text, icon, accent,
                on_read_callback=None, locked=True, **kw):
        super().__init__(master, bg=BG_CARD,
                        highlightthickness=1,
                        highlightbackground=BORDER_DARK, **kw)
        self.title = title
        self.text  = text
        self.accent = accent
        self.on_read_callback = on_read_callback
        self._read = False
        self._locked = locked

        self._build(icon, accent)
        self._set_locked(locked)

 

    # ── construcción ────────────────────────────────────────────────
    def _build(self, icon, accent):
        # ── cabecera ─────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_CARD)
        header.pack(fill="x", padx=14, pady=(12, 4))

        self.icon_lbl = tk.Label(header, text=icon, font=("Segoe UI Emoji", 16),
                                 bg=BG_CARD, fg=accent)
        self.icon_lbl.pack(side="left", padx=(0, 8))

        self.title_lbl = tk.Label(header, text=self.title,
                                  font=("Courier New", 11, "bold"),
                                  bg=BG_CARD, fg=accent, anchor="w")
        self.title_lbl.pack(side="left", fill="x", expand=True)

        self.status_lbl = tk.Label(header, text="● PENDIENTE",
                                   font=("Courier New", 8, "bold"),
                                   bg=BG_CARD, fg=TEXT_MUTED)
        self.status_lbl.pack(side="right")

        # ── separador decorativo ──────────────────────────────────
        sep = tk.Canvas(self, height=1, bg=BG_CARD,
                        highlightthickness=0)
        sep.pack(fill="x", padx=14)
        sep.create_line(0, 0, 2000, 0, fill=accent, width=1)

        # ── área de texto + scrollbar ─────────────────────────────
        txt_frame = tk.Frame(self, bg=BG_CARD)
        txt_frame.pack(fill="both", expand=True, padx=14, pady=(8, 6))

        scrollbar = tk.Scrollbar(txt_frame, orient="vertical",
                                 troughcolor=BG_PANEL,
                                 bg=TEXT_FAINT, activebackground=accent,
                                 highlightthickness=0, bd=0, width=8)
        scrollbar.pack(side="right", fill="y")

        self.txt = tk.Text(txt_frame,
                           wrap="word",
                           font=("Courier New", 9),
                           bg=BG_PANEL, fg=TEXT_MUTED,
                           insertbackground=accent,
                           relief="flat", bd=0,
                           padx=10, pady=10,
                           spacing1=2, spacing3=2,
                           yscrollcommand=scrollbar.set,
                           state="disabled",
                           cursor="arrow")
        self.txt.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.txt.yview)

        self.txt.config(state="normal")
        self.txt.insert("1.0", self.text)
        self.txt.config(state="disabled")
        self.txt.bind("<MouseWheel>",    self._on_scroll)
        self.txt.bind("<Button-4>",      self._on_scroll)
        self.txt.bind("<Button-5>",      self._on_scroll)

        # ── barra de progreso de lectura ──────────────────────────
        prog_frame = tk.Frame(self, bg=BG_CARD)
        prog_frame.pack(fill="x", padx=14, pady=(0, 10))

        prog_bg = tk.Canvas(prog_frame, height=4, bg=TEXT_FAINT,
                            highlightthickness=0)
        prog_bg.pack(fill="x")
        self._prog_bg = prog_bg
        self._prog_fill = prog_bg.create_rectangle(0, 0, 0, 4,
                                                    fill=accent, outline="")
        prog_bg.bind("<Configure>", self._redraw_progress)

        self._progress = 0.0

    # ── bloqueo / desbloqueo ─────────────────────────────────────
    def _set_locked(self, locked):
        self._locked = locked
        if locked:
            self.config(highlightbackground=BORDER_DARK)
            self.txt.config(fg=TEXT_FAINT, state="disabled", cursor="arrow")
            self.title_lbl.config(fg=TEXT_FAINT)
            self.icon_lbl.config(fg=TEXT_FAINT)
            self.status_lbl.config(text="🔒 BLOQUEADO", fg=TEXT_FAINT)
        else:
            self.config(highlightbackground=self.accent)
            self.txt.config(fg=TEXT_MUTED, state="disabled", cursor="xterm")
            self.title_lbl.config(fg=self.accent)
            self.icon_lbl.config(fg=self.accent)
            if not self._read:
                self.status_lbl.config(text="↕  DESPLÁZATE", fg=self.accent)

    def unlock(self):
        self._set_locked(False)

    # ── scroll ───────────────────────────────────────────────────
    def _on_scroll(self, event=None):
        if self._locked or self._read:
            return
        self.after(50, self._check_bottom)

    def _check_bottom(self):
        try:
            top, bot = self.txt.yview()
        except Exception:
            return
        progress = bot  # bot==1.0 cuando el final está visible
        self._update_progress(progress)
        if bot >= 0.999 and not self._read:
            self._mark_read()

    def _update_progress(self, value):
        self._progress = value
        self._redraw_progress()

    def _redraw_progress(self, event=None):
        w = self._prog_bg.winfo_width()
        if w < 2:
            return
        filled = int(w * self._progress)
        self._prog_bg.coords(self._prog_fill, 0, 0, filled, 4)

    def _mark_read(self):
        self._read = True
        self._update_progress(1.0)
        self.config(highlightbackground=SUCCESS)
        self.status_lbl.config(text="✔  LEÍDO", fg=SUCCESS)
        self.title_lbl.config(fg=SUCCESS)
        self.icon_lbl.config(fg=SUCCESS)
        if self.on_read_callback:        # ← debe estar así, no callable(self.on_read_callback)
            self.on_read_callback()

    @property
    def is_read(self):
        return self._read


# ══════════════════════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

class WelcomeScreen(tk.Tk):

    def __init__(self, uid: str = "", on_accepted=None, on_declined=None):
        super().__init__()
        self._uid         = uid
        self._on_accepted = on_accepted
        self._on_declined = on_declined
        self.protocol("WM_DELETE_WINDOW", self._on_decline)
        self.title("NébulaVault — Bienvenida")
        self.configure(bg=BG_VOID)
        self.resizable(False, False)

        W, H = 1850, 1000
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

        self._sections: list[LegalSection] = []
        self._accept_var = tk.BooleanVar(value=False)
        self._chk_state = False   # ← estado manual, reemplaza BooleanVar
        self._pulse_state = 0

        self._build_ui(W, H)
        self._start_pulse()


    # ── UI PRINCIPAL ─────────────────────────────────────────────
    def _build_ui(self, W, H):
        # ── fondo decorativo (Canvas) ─────────────────────────────
        bg_canvas = tk.Canvas(self, width=W, height=H,
                              bg=BG_VOID, highlightthickness=0)
        bg_canvas.place(x=0, y=0)
        draw_hex_grid(bg_canvas, W, H, spacing=48, color="#0d1520")

        # línea lateral izquierda
        bg_canvas.create_line(0, 0, 0, H, fill=ACCENT_CYAN, width=3)
        bg_canvas.create_line(3, 0, 3, H, fill=CYAN_20, width=1)

        # línea inferior
        bg_canvas.create_line(0, H-3, W, H-3, fill=ACCENT_CYAN, width=2)

        # esquinas decorativas (top-left, top-right)
        _corner(bg_canvas, 24, 24, 36, ACCENT_CYAN, "tl")
        _corner(bg_canvas, W-24, 24, 36, ACCENT_CYAN, "tr")

        # ── scrollable outer container ────────────────────────────
        outer = tk.Frame(self, bg=BG_VOID)
        outer.place(x=0, y=0, width=W, height=H)

        canvas_scroll = tk.Canvas(outer, bg=BG_VOID,
                                  highlightthickness=0)
        v_scroll = tk.Scrollbar(outer, orient="vertical",
                                command=canvas_scroll.yview,
                                bg=TEXT_FAINT, troughcolor=BG_PANEL,
                                width=8, bd=0, highlightthickness=0)
        canvas_scroll.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side="right", fill="y")
        canvas_scroll.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(canvas_scroll, bg=BG_VOID)
        win_id = canvas_scroll.create_window((0, 0), window=self._inner,
                                              anchor="nw")

        def _on_inner_configure(e):
            canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
            canvas_scroll.itemconfig(win_id, width=canvas_scroll.winfo_width())

        self._inner.bind("<Configure>", _on_inner_configure)
        canvas_scroll.bind("<Configure>",
                           lambda e: canvas_scroll.itemconfig(
                               win_id, width=e.width))
        canvas_scroll.bind_all("<MouseWheel>",
                               lambda e: canvas_scroll.yview_scroll(
                                   -1 * int(e.delta / 120), "units"))

        self._build_header()
        self._build_sections()
        self._build_footer()

    # ── CABECERA ─────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self._inner, bg=BG_VOID)
        hdr.pack(fill="x", padx=40, pady=(36, 0))

        # ── Logo desde archivo ────────────────────────────────────
        logo_outer = tk.Frame(hdr, bg=BG_VOID)
        logo_outer.pack(anchor="center")

        try:
            from PIL import Image, ImageTk
            img = Image.open("assets/nebulavaultLogo.png").resize((96, 96), Image.LANCZOS)
            self._logo_img = ImageTk.PhotoImage(img)
            tk.Label(logo_outer, image=self._logo_img, bg=BG_VOID).pack()
        except Exception:
            # Fallback: logo canvas original si no encuentra el archivo o Pillow
            logo_canvas = tk.Canvas(logo_outer, width=96, height=96,
                                    bg=BG_VOID, highlightthickness=0)
            logo_canvas.pack()
            for r, col, w in [(46, CYAN_27, 1), (40, CYAN_53, 1), (34, ACCENT_CYAN, 2)]:
                logo_canvas.create_oval(48-r, 48-r, 48+r, 48+r,
                                        outline=col, fill="", width=w)
            logo_canvas.create_polygon(
                48,16, 72,28, 72,52, 48,76, 24,52, 24,28,
                fill=BG_CARD, outline=ACCENT_CYAN, width=2)
            logo_canvas.create_polygon(
                48,26, 64,36, 64,52, 48,66, 32,52, 32,36,
                fill=CYAN_13, outline=CYAN_53, width=1)
            logo_canvas.create_oval(43,42, 53,52, fill=BG_CARD, outline=ACCENT_CYAN, width=2)
            logo_canvas.create_rectangle(41,48, 55,58, fill=CYAN_80, outline="")
            self._logo_canvas = logo_canvas

        # ── Nombre de la app ──────────────────────────────────────
        title_frame = tk.Frame(hdr, bg=BG_VOID)
        title_frame.pack(anchor="center", pady=(10, 0))

        tk.Label(title_frame, text="NÉBULA",
                 font=("Courier New", 32, "bold"),
                 bg=BG_VOID, fg=ACCENT_CYAN).pack(side="left")
        tk.Label(title_frame, text="VAULT",
                 font=("Courier New", 32, "bold"),
                 bg=BG_VOID, fg=TEXT_MAIN).pack(side="left")

        tk.Label(hdr, text="— gestor de contraseñas local —",
                 font=("Courier New", 9),
                 bg=BG_VOID, fg=TEXT_MUTED).pack(anchor="center")

        # ── Tagline / descripción ─────────────────────────────────
        sep_canvas = tk.Canvas(hdr, height=24, bg=BG_VOID,
                               highlightthickness=0, width=500)
        sep_canvas.pack(anchor="center", pady=(18, 4))
        sep_canvas.create_line(0, 12, 180, 12, fill=CYAN_33, width=1)
        sep_canvas.create_oval(185, 8, 193, 16, outline=ACCENT_CYAN, fill="")
        sep_canvas.create_oval(198, 8, 206, 16, outline=ACCENT_CYAN,
                               fill=ACCENT_CYAN)
        sep_canvas.create_oval(211, 8, 219, 16, outline=ACCENT_CYAN, fill="")
        sep_canvas.create_line(224, 12, 500, 12, fill=CYAN_33, width=1)

        desc = (
            "NébulaVault protege tus credenciales con cifrado de grado militar, "
            "sin nube ni servidores externos.\n"
            "Antes de continuar, revisa y acepta nuestros documentos legales. "
            "Tu privacidad importa — y tú mereces saberlo."
        )
        tk.Label(hdr, text=desc,
                 font=("Courier New", 9),
                 bg=BG_VOID, fg=TEXT_MUTED,
                 wraplength=640, justify="center",
                 pady=4).pack(anchor="center")

        # ── Indicador de pasos ────────────────────────────────────
        steps_frame = tk.Frame(hdr, bg=BG_VOID)
        steps_frame.pack(anchor="center", pady=(14, 4))

        steps = ["① Leer documentos", "② Desplazar al final",
                 "③ Aceptar", "④ Ingresar"]
        for i, s in enumerate(steps):
            col = ACCENT_CYAN if i == 0 else TEXT_FAINT
            tk.Label(steps_frame, text=s,
                     font=("Courier New", 8),
                     bg=BG_VOID, fg=col,
                     padx=8).pack(side="left")
            if i < len(steps) - 1:
                tk.Label(steps_frame, text="›",
                         font=("Courier New", 10),
                         bg=BG_VOID, fg=TEXT_FAINT).pack(side="left")

    # ── SECCIONES LEGALES ─────────────────────────────────────────
    def _build_sections(self):
        sections_frame = tk.Frame(self._inner, bg=BG_VOID)
        sections_frame.pack(fill="x", padx=40, pady=(24, 0))

        titles = list(LEGAL_TEXTS.keys())
        texts  = list(LEGAL_TEXTS.values())

        for i, (title, text, icon, accent) in enumerate(
                zip(titles, texts, SECTION_ICONS, SECTION_COLORS)):
            locked = (i > 0)
            sec = LegalSection(
                sections_frame, title, text, icon, accent,
                on_read_callback=lambda idx=i: self._on_section_read(idx),
                locked=locked,
                height=220
            )
            sec.pack(fill="x", pady=6)
            self._sections.append(sec)

        # tip de scroll
        tk.Label(sections_frame,
                 text="↕  Desplázate dentro de cada sección para desbloquear la siguiente.",
                 font=("Courier New", 8),
                 bg=BG_VOID, fg=TEXT_FAINT
                 ).pack(anchor="center", pady=(6, 0))

    # ── FOOTER: checkbox + botón Continuar + botón Rechazar ───────────
    def _build_footer(self):
        footer = tk.Frame(self._inner, bg=BG_VOID)
        footer.pack(fill="x", padx=40, pady=(20, 32))
 
        # divider
        div = tk.Canvas(footer, height=1, bg=BG_VOID,
                        highlightthickness=0)
        div.pack(fill="x")
        div.create_line(0, 0, 2000, 0, fill=BORDER_DARK, width=1)
 
        inner = tk.Frame(footer, bg=BG_VOID)
        inner.pack(fill="x", pady=(16, 0))
 
        # checkbox
        self._chk = tk.Checkbutton(
            inner,
            text="  Acepto los Términos de Uso, el Aviso de Privacidad "
                 "y el Acuerdo de Confidencialidad.",
            variable=self._accept_var,
            command=self._on_accept_toggle,
            font=("Courier New", 9, "bold"),
            bg=BG_VOID, fg=TEXT_MUTED,
            selectcolor=BG_CARD,
            activebackground=BG_VOID,
            activeforeground=ACCENT_CYAN,
            disabledforeground=TEXT_FAINT,
            state="disabled",
            anchor="w",
            pady=6,
        )
        self._chk.pack(fill="x")
        self._chk.bind("<ButtonRelease-1>", self._on_chk_manual)  # ← añadir esta línea
 
        # ── Botón Continuar ──────────────────────────────────────────
        self._btn = tk.Button(
            inner,
            text="  Continuar  →",
            font=("Courier New", 11, "bold"),
            bg=BTN_DISABLED, fg=TEXT_FAINT,
            activebackground=BTN_HOVER, activeforeground="white",
            relief="flat", bd=0, pady=10,
            cursor="arrow",
            state="disabled",
            command=self._on_continue,
        )
        self._btn.pack(fill="x", pady=(10, 0))
 
        # ── Botón Rechazar ───────────────────────────────────────────
        self._btn_decline = tk.Button(
            inner,
            text="  Rechazar y salir",
            font=("Courier New", 9),
            bg=BG_VOID, fg=TEXT_MUTED,
            activebackground=BG_CARD, activeforeground=LOCK_RED,
            relief="flat", bd=0, pady=6,
            cursor="hand2",
            command=self._on_decline,
        )
        self._btn_decline.pack(fill="x", pady=(4, 0))
 
        # ── Nota legal ───────────────────────────────────────────────
        tk.Label(
            inner,
            text="Nébula Security · Última actualización: 6 de febrero de 2026",
            font=("Courier New", 7),
            bg=BG_VOID, fg=TEXT_FAINT
        ).pack(anchor="center", pady=(10, 0))
 
    # ── LÓGICA ────────────────────────────────────────────────────────
    def _on_section_read(self, idx):
        """Se llama cuando la sección idx fue leída completamente."""
        next_idx = idx + 1
        if next_idx < len(self._sections):
            self._sections[next_idx].unlock()
        self._check_all_read()

    def _check_all_read(self):
        if all(s.is_read for s in self._sections):
            self._chk.config(state="normal", fg=TEXT_MAIN)

    def _on_chk_manual(self, event=None):
        """Toggle manual del checkbox — BooleanVar es poco fiable en Linux/Tk."""
        if str(self._chk.cget("state")) == "disabled":
            return
        self._chk_state = not self._chk_state
        print("chk_state:", self._chk_state)   # debug, quitar después
        if self._chk_state:
            self._btn.config(
                state="normal", bg=BTN_ACTIVE, fg="white",
                cursor="hand2"
            )
            self._pulse_btn()
        else:
            self._btn.config(
                state="disabled", bg=BTN_DISABLED, fg=TEXT_FAINT,
                cursor="arrow"
            )

    def _on_accept_toggle(self):
        pass   # ya no se usa, el control lo lleva _on_chk_manual
    
    def _on_continue(self):
        self._btn.config(state="disabled", text="  Guardando…")
        self.update_idletasks()
        try:
            AuthFire.guardar_aceptacion_terminos(self._uid)
        except Exception as exc:
            messagebox.showerror(
                "NébulaVault",
                f"No se pudo guardar tu consentimiento:\n{exc}\n\n"
                "Verifica tu conexión e intenta de nuevo.",
                parent=self,
            )
            self._btn.config(state="normal", text="  Continuar  →")
            return

        messagebox.showinfo(
            "NébulaVault",
            "✔ Consentimiento registrado.\n\nBienvenido a NébulaVault.",
            parent=self,
        )
        self.destroy()
        if callable(self._on_accepted):
            self._on_accepted()

    def _on_decline(self):
        respuesta = messagebox.askyesno(
            "NébulaVault — Confirmación",
            "Para usar NébulaVault debes aceptar los documentos legales.\n\n"
            "Si rechazas, no podrás acceder a la aplicación.\n\n"
            "¿Deseas salir?",
            icon="warning",
            parent=self,
        )
        if respuesta:
            self.destroy()
            if callable(self._on_declined):
                self._on_declined()
 

    # ── ANIMACIÓN: pulso en el logo ───────────────────────────────
    def _start_pulse(self):
        self._animate_logo()

    def _animate_logo(self):
        # Solo anima si existe el canvas (fallback); con imagen real no aplica
        if not hasattr(self, "_logo_canvas"):
            return
        t = time.time()
        alpha = 0.5 + 0.5 * math.sin(t * 2)
        r = int(34 + 6 * alpha)
        c = self._logo_canvas
        c.delete("pulse")
        c.create_oval(48-r, 48-r, 48+r, 48+r,
                      outline=ACCENT_CYAN, fill="", width=1,
                      tags="pulse")
        self.after(50, self._animate_logo)

    def _pulse_btn(self):
        """Parpadeo suave del botón al activarse."""
        colors = [BTN_ACTIVE, BTN_HOVER, BTN_ACTIVE]
        def _step(i=0):
            if i >= len(colors):
                return
            self._btn.config(bg=colors[i])
            self.after(120, lambda: _step(i+1))
        _step()


# ── HELPERS ───────────────────────────────────────────────────────────

def _corner(canvas, cx, cy, size, color, pos):
    """Dibuja un adorno de esquina (L)."""
    s = size // 2
    if pos == "tl":
        canvas.create_line(cx, cy+s, cx, cy, cx+s, cy,
                           fill=color, width=2)
    elif pos == "tr":
        canvas.create_line(cx, cy+s, cx, cy, cx-s, cy,
                           fill=color, width=2)
    elif pos == "bl":
        canvas.create_line(cx, cy-s, cx, cy, cx+s, cy,
                           fill=color, width=2)
    elif pos == "br":
        canvas.create_line(cx, cy-s, cx, cy, cx-s, cy,
                           fill=color, width=2)




