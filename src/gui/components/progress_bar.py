import tkinter as tk
from tkinter import ttk

def progress_bar(parent):
    bar = ttk.Progressbar(parent, orient="horizontal", length=300, mode="determinate")
    bar.pack(pady=10)
    return bar 