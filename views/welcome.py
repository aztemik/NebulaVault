import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from config import COMPANY

class WelcomeFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._logo_img = None

        header = ttk.Frame(self)
        header.pack(fill="x", padx=14, pady=14)

        self._build_logo(header)

        info = ttk.Frame(header)
        info.pack(side="left", fill="both", expand=True, padx=14)

        ttk.Label(info, text=COMPANY["product"], font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(info, text=COMPANY["tagline"], font=("Segoe UI", 11)).pack(anchor="w", pady=(2, 10))
        ttk.Label(info, text=COMPANY["objective"], wraplength=640, justify="left").pack(anchor="w")

        card = ttk.LabelFrame(self, text="¿Qué hace la app? (demo)")
        card.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        bullets = (
            "• Crea y abre una bóveda local.\n"
            "• Administra credenciales: agregar, listar, buscar.\n"
            "• Exportación segura.\n"
            "• Seguridad planeada: cifrado fuerte + bitácora + bloqueo por intentos.\n"
        )
        ttk.Label(card, text=bullets, justify="left").pack(anchor="w", padx=12, pady=12)

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=14, pady=(0, 14))

        ttk.Button(actions, text="Ver empresa y documentos legales", command=lambda: app.show("AboutFrame")).pack(side="left")
        ttk.Button(actions, text="Salir", command=app.destroy).pack(side="right")

    def _build_logo(self, parent):
        box = ttk.LabelFrame(parent, text="Logo")
        box.pack(side="left")

        path = COMPANY["logo_path"]
        if path.exists():
            img = Image.open(path).convert("RGBA")
            img.thumbnail((110, 110))
            self._logo_img = ImageTk.PhotoImage(img)
            ttk.Label(box, image=self._logo_img).pack(padx=10, pady=10)
        else:
            canvas = tk.Canvas(box, width=110, height=110, highlightthickness=0)
            canvas.pack(padx=10, pady=10)
            canvas.create_rectangle(8, 8, 102, 102)
            canvas.create_text(55, 55, text="NV", font=("Segoe UI", 24, "bold"))
