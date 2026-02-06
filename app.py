import tkinter as tk
from tkinter import ttk
from config import COMPANY
from views.welcome import WelcomeFrame
from views.about import AboutFrame

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(f"{COMPANY['product']} • {COMPANY['name']}")
        self.geometry("900x9870")
        self.resizable(False, False)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        self.frames = {}
        for FrameClass in (WelcomeFrame, AboutFrame):
            frame = FrameClass(container, self)
            self.frames[FrameClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show("WelcomeFrame")

    def show(self, frame_name: str):
        self.frames[frame_name].tkraise()
