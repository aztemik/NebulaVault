import tkinter as tk
from views.WelcomeScreen import WelcomeScreen


def run_app():
    root = tk.Tk()
    app = WelcomeScreen(root)
    root.mainloop()