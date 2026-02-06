import tkinter as tk
from tkinter import ttk, messagebox
from config import COMPANY, LEGAL_TEXTS

class AboutFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill="x", padx=14, pady=12)

        ttk.Label(top, text="Empresa / App", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(top, text="Volver", command=lambda: app.show("WelcomeFrame")).pack(side="right")

        meta = ttk.LabelFrame(self, text="Identidad")
        meta.pack(fill="x", padx=14, pady=(0, 10))

        ttk.Label(meta, text=f"Empresa: {COMPANY['name']}").pack(anchor="w", padx=10, pady=(8, 2))
        ttk.Label(meta, text=f"Producto: {COMPANY['product']}").pack(anchor="w", padx=10, pady=2)
        ttk.Label(meta, text=f"Lema: {COMPANY['tagline']}").pack(anchor="w", padx=10, pady=2)
        ttk.Label(meta, text="Objetivo:", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(8, 0))
        ttk.Label(meta, text=COMPANY["objective"], wraplength=820, justify="left").pack(anchor="w", padx=10, pady=(2, 10))

        docs = ttk.LabelFrame(self, text="Documentos legales")
        docs.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        nb = ttk.Notebook(docs)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        for title, body in LEGAL_TEXTS.items():
            page = ttk.Frame(nb)
            nb.add(page, text=title)

            txt = tk.Text(page, wrap="word")
            txt.insert("1.0", body)
            txt.configure(state="disabled")
            txt.pack(fill="both", expand=True, padx=8, pady=8)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=14, pady=(0, 14))

        ttk.Button(bottom, text="Simular 'Iniciar' (solo demo)", command=self._demo_start).pack(side="left")

    def _demo_start(self):
        messagebox.showinfo(
            "Demo",
            "Aquí iría el flujo real: Crear/Abrir bóveda, Gestión de entradas, etc."
        )
