import tkinter as tk

def log_viewer(parent):
    text = tk.Text(parent, height=8, width=50, state="disabled")
    text.pack(pady=10)
    return text 