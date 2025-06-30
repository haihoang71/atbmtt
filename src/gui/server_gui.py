import tkinter as tk
from tkinter import scrolledtext
import logging

class ServerGUI:
    def __init__(self, server_name="Server"):
        self.root = tk.Tk()
        self.root.title(f"{server_name} GUI")
        self.root.geometry("600x400")
        self.log_text = scrolledtext.ScrolledText(self.root, height=20, width=80, state="disabled")
        self.log_text.pack(padx=10, pady=10)

    def log(self, level, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{level.upper()}] {msg}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def run(self):
        self.root.mainloop()

class TkinterLogHandler(logging.Handler):
    def __init__(self, gui_log_func):
        super().__init__()
        self.gui_log_func = gui_log_func

    def emit(self, record):
        msg = self.format(record)
        level = record.levelname.lower()
        self.gui_log_func(level, msg) 